"""后台任务模型与线程池。

CompressionTask 承载一个视频的完整压缩：读时长 -> 拼命令 -> 跑 ffmpeg -> 汇报结果。
run() 在工作线程执行；progress / finished 信号自动投递回主线程。
TaskPool 用 QThreadPool 限制并发数（阶段一由设置或 config 控制）。
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from . import env
from .config import AppConfig
from .ffmpeg_runner import (
    build_audio_extract_cmd, build_compress_cmd, build_concat_cmd,
    build_convert_cmd, build_cut_cmd, parse_time_to_secs, resolve_output,
    run_ffmpeg, write_concat_list,
)

# 任务状态
RUNNING, SUCCESS, FAILED, CANCELLED = "running", "success", "failed", "cancelled"


class CompressionTaskSignals(QObject):
    progress = Signal(int)
    finished = Signal(object)  # task 自己


class CompressionTask(QRunnable):
    def __init__(self, input_path: str, params: dict):
        super().__init__()
        self.input_path = input_path
        self.params = params
        self.status = RUNNING
        self.message = ""
        self.output_path = ""
        self.progress_pct = 0
        self.orig_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
        self.result_size = 0
        self._stop = __import__("threading").Event()
        self._signals = CompressionTaskSignals()

    # ---- 公共信号访问 ----
    @property
    def signals(self):
        return self._signals

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            cfg = AppConfig.instance()
            p = self.params
            enc = p["encoder"]

            src = Path(self.input_path)
            out_dir = cfg.output_dir(src.parent)
            out_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = resolve_output(self.input_path, str(out_dir), p.get("suffix", "_compressed"))

            cmd = build_compress_cmd(
                self.input_path, self.output_path,
                encoder=enc,
                crf=p["crf"],
                preset=p["preset"],
                resolution=p["resolution"],
                res_w=p.get("resolution_w"),
                res_h=p.get("resolution_h"),
                fps=p["fps"],
                fps_value=p.get("fps_value"),
            )

            total_ms = env.probe_duration_ms(src)
            # nvenc 的 -progress 以 out_time_us 输出；软件编码同理
            code, stderr = run_ffmpeg(
                cmd, total_ms,
                on_progress=lambda ms: self._on_progress(ms, total_ms),
                stop_event=self._stop,
            )

            if self._stop.is_set():
                self.status = CANCELLED
                self.message = "已取消"
            elif code == 0 and Path(self.output_path).exists():
                self.result_size = Path(self.output_path).stat().st_size
                self.status = SUCCESS
                self.progress_pct = 100
            else:
                self.status = FAILED
                self.message = _tail(stderr) or f"ffmpeg 退出码 {code}"
            self._signals.finished.emit(self)
        except Exception as exc:  # 兜底，避免工作线程静默崩溃
            self.status = FAILED
            self.message = str(exc)
            self._signals.finished.emit(self)

    def _on_progress(self, ms: int, total_ms: int) -> None:
        if total_ms > 0:
            self.progress_pct = min(int(ms * 100 / total_ms), 99)
        else:
            self.progress_pct = 0
        self._signals.progress.emit(self.progress_pct)

    def size_ratio(self) -> float:
        if self.orig_size <= 0:
            return 1.0
        return self.result_size / self.orig_size


def _tail(text: str, n: int = 300) -> str:
    t = text.strip().replace("\n", " · ")
    return t[-n:] if t else ""


class CutTaskSignals(QObject):
    progress = Signal(int)
    finished = Signal(object)  # task 自己


class CutTask(QRunnable):
    """按时间段切割单个视频。每个时间段输出 `<stem>_<i><ext>`。

    segments 形如 [(start, end, ...)]，start/end 为 HH:MM:SS 字符串。
    progress 按所有时间段累计时长加权。
    """

    def __init__(self, input_path: str, segments: list[list[str]], params: dict):
        super().__init__()
        self.input_path = input_path
        self.segments = segments
        self.params = params
        self.status = RUNNING
        self.message = ""
        self.outputs: list[str] = []
        self.progress_pct = 0
        self._stop = __import__("threading").Event()
        self._signals = CutTaskSignals()

    @property
    def signals(self):
        return self._signals

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            cfg = AppConfig.instance()
            p = self.params
            src = Path(self.input_path)
            out_dir = cfg.output_dir(src.parent)
            out_dir.mkdir(parents=True, exist_ok=True)
            stem, ext = src.stem, src.suffix or ".mp4"

            # 校验时间段并算累计时长
            durations = []
            for st, en in self.segments:
                s = parse_time_to_secs(st)
                e = parse_time_to_secs(en)
                if e <= s:
                    self.status = FAILED
                    self.message = f"时间段结束必须晚于开始：{st} - {en}"
                    self._signals.finished.emit(self)
                    return
                durations.append((s, e, e - s))
            total_ms = sum(d * 1000 for _, _, d in durations)
            if total_ms <= 0:
                self.status = FAILED
                self.message = "未设置有效时间段"
                self._signals.finished.emit(self)
                return

            encoder = p.get("encoder", "libx264")
            crf = p.get("crf", 18)
            preset = p.get("preset", "fast")
            mode = p.get("mode", "reencode")

            done_ms = 0
            for i, (s_sec, _, d_sec) in enumerate(durations, 1):
                output_path = str(out_dir / f"{stem}_{i}{ext}")
                cmd = build_cut_cmd(
                    self.input_path, output_path,
                    _fmt_sec(s_sec), _fmt_sec(s_sec + d_sec),
                    mode=mode, encoder=encoder, crf=crf, preset=preset,
                )
                seg_ms = d_sec * 1000
                base = done_ms

                def _prog(ms: int, _b=base, _s=seg_ms, _t=total_ms) -> None:
                    overall = min(int((_b + ms) / _t * 100), 99)
                    if overall > self.progress_pct:
                        self.progress_pct = overall
                    self._signals.progress.emit(self.progress_pct)

                code, stderr = run_ffmpeg(cmd, seg_ms, _prog, self._stop)
                done_ms += seg_ms
                if self._stop.is_set():
                    self.status = CANCELLED
                    self.message = "已取消"
                    self._signals.finished.emit(self)
                    return
                if code != 0:
                    self.status = FAILED
                    self.message = _tail(stderr) or f"第{i}段 ffmpeg 退出码 {code}"
                    self._signals.finished.emit(self)
                    return
                self.outputs.append(output_path)

            self.progress_pct = 100
            self.status = SUCCESS
            self._signals.finished.emit(self)
        except Exception as exc:  # 兜底，避免工作线程静默崩溃
            self.status = FAILED
            self.message = str(exc)
            self._signals.finished.emit(self)


def _fmt_sec(total_secs: int) -> str:
    """把秒数格式化为 HH:MM:SS（小时可为多位）。"""
    h, rem = divmod(total_secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class ConvertTaskSignals(QObject):
    progress = Signal(int)
    finished = Signal(object)  # task 自己


class ConvertTask(QRunnable):
    """格式转换 / 提取音频（单文件单任务）。

    params:
      audio_only=True → 输出 `<stem>.m4a`（仅音轨）
      否则 → 输出 `<stem>.<fmt>`（fmt∈mp4/webm/mkv）
    """

    def __init__(self, input_path: str, params: dict):
        super().__init__()
        self.input_path = input_path
        self.params = params
        self.status = RUNNING
        self.message = ""
        self.output_path = ""
        self.progress_pct = 0
        self._stop = __import__("threading").Event()
        self._signals = ConvertTaskSignals()

    @property
    def signals(self):
        return self._signals

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            cfg = AppConfig.instance()
            p = self.params
            src = Path(self.input_path)
            out_dir = cfg.output_dir(src.parent)
            out_dir.mkdir(parents=True, exist_ok=True)

            if p.get("audio_only"):
                self.output_path = str(out_dir / f"{src.stem}.m4a")
                cmd = build_audio_extract_cmd(self.input_path, self.output_path)
            else:
                self.output_path = str(out_dir / f"{src.stem}.{p.get('fmt', 'mp4')}")
                cmd = build_convert_cmd(
                    self.input_path, self.output_path,
                    fmt=p.get("fmt", "mp4"),
                    resolution=p.get("resolution") or None,
                    quality=p.get("quality", "balance"),
                    vcodec=p.get("vcodec", "libx264"),
                    audio=p.get("audio", "keep"),
                    preset=p.get("preset", "medium"),
                )

            total_ms = env.probe_duration_ms(src)
            code, stderr = run_ffmpeg(
                cmd, total_ms,
                on_progress=lambda ms: self._on_progress(ms, total_ms),
                stop_event=self._stop,
            )
            if self._stop.is_set():
                self.status = CANCELLED
                self.message = "已取消"
            elif code == 0 and Path(self.output_path).exists():
                self.progress_pct = 100
                self.status = SUCCESS
            else:
                self.status = FAILED
                self.message = _tail(stderr) or f"转换 ffmpeg 退出码 {code}"
            self._signals.finished.emit(self)
        except Exception as exc:
            self.status = FAILED
            self.message = str(exc)
            self._signals.finished.emit(self)

    def _on_progress(self, ms: int, total_ms: int) -> None:
        if total_ms > 0:
            self.progress_pct = min(int(ms * 100 / total_ms), 99)
        else:
            self.progress_pct = 0
        self._signals.progress.emit(self.progress_pct)


class ConcatTaskSignals(QObject):
    progress = Signal(int)
    finished = Signal(object)  # task 自己


class ConcatTask(QRunnable):
    """把多个视频按给定顺序拼成一个文件（concat demuxer）。

    inputs 顺序即拼接顺序。快速流复制（-c copy）要求各段编码参数一致；
    不一致时可选精确重编码统一编码。输出 `<首文件名>_<后缀>.<ext>`。
    """

    def __init__(self, inputs: list[str], params: dict):
        super().__init__()
        self.inputs = inputs
        self.params = params
        self.status = RUNNING
        self.message = ""
        self.output_path = ""
        self.progress_pct = 0
        self._stop = __import__("threading").Event()
        self._signals = ConcatTaskSignals()

    @property
    def signals(self):
        return self._signals

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        list_path = ""
        try:
            cfg = AppConfig.instance()
            p = self.params
            if len(self.inputs) < 2:
                self.status = FAILED
                self.message = "拼接至少需要 2 个视频"
                self._signals.finished.emit(self)
                return

            src = Path(self.inputs[0])
            out_dir = cfg.output_dir(src.parent)
            out_dir.mkdir(parents=True, exist_ok=True)
            stem = src.stem
            # 前置名取首文件最左边不含数字序号尾巴的部分（同原始脚本语义）
            import re as _re
            prefix = _re.sub(r"[-_ ]*(?:Part|CPart)?\d{3,}$", "", stem)
            ext = src.suffix or ".mp4"
            suffix = p.get("suffix", "_concat")
            self.output_path = str(out_dir / f"{prefix}{suffix}{ext}")

            list_path = str(out_dir / f".{stem}_concat.txt")
            write_concat_list(list_path, self.inputs)

            total_ms = sum(env.probe_duration_ms(Path(f)) for f in self.inputs)
            cmd = build_concat_cmd(
                list_path, self.output_path,
                mode=p.get("mode", "copy"),
                encoder=p.get("encoder", "libx264"),
                crf=int(p.get("crf", 18)),
                preset=p.get("preset", "fast"),
            )
            code, stderr = run_ffmpeg(
                cmd, total_ms,
                on_progress=lambda ms: self._on_progress(ms, total_ms),
                stop_event=self._stop,
            )

            if self._stop.is_set():
                self.status = CANCELLED
                self.message = "已取消"
            elif code == 0 and Path(self.output_path).exists():
                self.progress_pct = 100
                self.status = SUCCESS
            else:
                self.status = FAILED
                self.message = _tail(stderr) or f"拼接 ffmpeg 退出码 {code}"
            self._signals.finished.emit(self)
        except Exception as exc:
            self.status = FAILED
            self.message = str(exc)
            self._signals.finished.emit(self)
        finally:
            if list_path and Path(list_path).exists():
                try:
                    Path(list_path).unlink()
                except OSError:
                    pass

    def _on_progress(self, ms: int, total_ms: int) -> None:
        if total_ms > 0:
            self.progress_pct = min(int(ms * 100 / total_ms), 99)
        else:
            self.progress_pct = 0
        self._signals.progress.emit(self.progress_pct)


class TaskPool:
    """统一的后台执行池。承接压缩 / 切割等任务。"""

    def __init__(self) -> None:
        self._pool = QThreadPool.globalInstance()
        self._apply_concurrency()

    def _apply_concurrency(self) -> None:
        self._pool.setMaxThreadCount(AppConfig.instance().concurrency())

    def add(self, task: "CompressionTask | CutTask | ConvertTask | ConcatTask", concurrency: int | None = None) -> None:
        self._pool.start(task)
        self._pool.setMaxThreadCount(concurrency or AppConfig.instance().concurrency())

    def wait(self):
        self._pool.waitForDone()