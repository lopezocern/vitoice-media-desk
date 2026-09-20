"""FFmpeg 命令封装 + 进度解析。

- build_compress_cmd: 把压缩参数（编码器/CRF/预设/分辨率/帧率）拼成 ffmpeg 参数。
- run_ffmpeg: 启动子进程，用 `-progress pipe:1` 增量解析进度回调。
进度回调 on_progress(current_ms)。取消通过 stop_event 触发（发 SIGKILL 方式终止）。
"""
from __future__ import annotations

import shlex
import signal
import subprocess
import threading
from typing import Callable, Optional, Sequence

from .env import ffmpeg_exe, ffprobe_exe, probe_duration_ms


def _enc_args(encoder: str, crf: int, preset: str) -> list[str]:
    """根据编码器类型生成视频编码参数（硬件/软件语义不同）。"""
    if "nvenc" in encoder:
        hw_preset = {"medium": "p4", "fast": "p5", "ultrafast": "p7"}.get(preset, "p4")
        return ["-c:v", encoder, "-preset", hw_preset, "-cq", str(crf)]
    return ["-c:v", encoder, "-preset", preset, "-crf", str(crf)]


def build_compress_cmd(
    input_path: str,
    output_path: str,
    encoder: str,
    crf: int,
    preset: str,
    resolution: str = "keep",       # keep / 1080 / 720 / custom
    res_w: Optional[int] = None,
    res_h: Optional[int] = None,
    fps: str = "keep",              # keep / custom
    fps_value: int = 30,
) -> list[str]:
    """组装压缩命令，返回 ffmpeg argv 列表。"""
    vf = []
    if resolution == "1080":
        vf.append(f"scale=-2:1080")
    elif resolution == "720":
        vf.append(f"scale=-2:720")
    elif resolution == "custom" and res_w and res_h:
        even_w = res_w if res_w % 2 == 0 else res_w - 1
        even_h = res_h if res_h % 2 == 0 else res_h - 1
        vf.append(f"scale={even_w}:{even_h}")

    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin"]
    cmd += ["-i", input_path]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if fps == "custom" and fps_value > 0:
        cmd += ["-r", str(fps_value)]

    is_nvenc = "nvenc" in encoder
    if is_nvenc:
        # NVIDIA 硬件编码：quality 与 preset 的参数语义与软件不同
        hw_preset = {"medium": "p4", "fast": "p5", "ultrafast": "p7"}.get(preset, "p4")
        cmd += ["-c:v", encoder, "-preset", hw_preset, "-cq", str(crf)]
    else:
        cmd += ["-c:v", encoder, "-preset", preset, "-crf", str(crf)]

    cmd += ["-c:a", "copy"]
    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    return cmd


_ProgressCb = Callable[[int], None]
_StopEvent = Optional[threading.Event]


def run_ffmpeg(cmd: Sequence[str], total_ms: int, on_progress: _ProgressCb,
               stop_event: _StopEvent = None) -> tuple[int, str]:
    """运行 ffmpeg 命令并推送实时进度（累计微秒 / total_ms）。

    返回 (returncode, stderr文本)。停止时 returncode = -9。
    """
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x00000008 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,  # CREATE_NO_WINDOW
        )
    except FileNotFoundError:
        return -1, "FFmpeg 未找到，请在【全局设置】中指定路径。"

    stderr_chunks: list[str] = []
    last_ms = 0
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key in ("out_time_us", "out_time_ms"):
                try:
                    us = int(val)
                    ms = us // 1000
                except ValueError:
                    ms = last_ms
                if ms > last_ms:
                    last_ms = ms
                if total_ms > 0:
                    on_progress(min(last_ms, total_ms))
            if stop_event is not None and stop_event.is_set():
                proc.kill()
                break
    except Exception:
        pass

    if proc.stderr is not None:
        rest = proc.stderr.read()
        if rest:
            stderr_chunks.append(rest)
    proc.wait()
    return proc.returncode, "".join(stderr_chunks)


def resolve_output(input_path: str, output_dir: str, suffix: str) -> str:
    """根据源文件与输出目录/后缀，生成实际输出路径（保留扩展名）。"""
    from pathlib import Path
    src = Path(input_path)
    stem, ext = src.stem, src.suffix or ".mp4"
    return str(Path(output_dir) / f"{stem}{suffix}{ext}")


# ---- 切割 ----

def parse_time_to_secs(t: str) -> int:
    """把 HH:MM:SS（也容忍 秒 或 MM:SS）解析为秒。失败抛 ValueError。"""
    parts = [p for p in t.strip().split(":") if p != ""]
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"时间格式无效：{t}")
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    raise ValueError(f"时间格式无效：{t}")


def build_cut_cmd(
    input_path: str,
    output_path: str,
    start: str,
    end: str,
    mode: str = "reencode",        # reencode / copy
    encoder: str = "libx264",
    crf: int = 18,
    preset: str = "fast",
) -> list[str]:
    """组装切割命令。时间段以 HH:MM:SS 表示。

    reencode：-ss 置于 -i 之后做帧精确重编码；copy：-ss 放在 -i 之前做快速流复制。
    """
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin"]
    if mode == "copy":
        cmd += ["-ss", start, "-to", end, "-i", input_path, "-c", "copy"]
    else:
        cmd += ["-i", input_path, "-ss", start, "-to", end]
        cmd += _enc_args(encoder, crf, preset)
        cmd += ["-c:a", "aac"]
    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    return cmd


# ---- 拼接 ----

def write_concat_list(list_path: str, input_paths: Sequence[str]) -> None:
    """写 ffmpeg concat 需要的 `file '路径'` 列表（-safe 0 允许绝对路径）。"""
    from pathlib import Path
    lines = []
    for p in input_paths:
        escaped = p.replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    Path(list_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_concat_cmd(
    list_path: str,
    output_path: str,
    mode: str = "copy",              # copy / reencode
    encoder: str = "libx264",
    crf: int = 18,
    preset: str = "fast",
) -> list[str]:
    """组装 concat 拼接命令（依赖 write_concat_list 先生成列表文件）。"""
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin",
           "-f", "concat", "-safe", "0", "-i", list_path]
    if mode == "reencode":
        cmd += _enc_args(encoder, crf, preset)
        cmd += ["-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    return cmd


# ---- 格式转换 ----

_CONVERT_QUALITY = {
    "high":    {"crf": 18, "vp": "2M"},
    "balance": {"crf": 23, "vp": "1M"},
    "small":   {"crf": 28, "vp": "500k"},
}


def build_convert_cmd(
    input_path: str,
    output_path: str,
    fmt: str = "mp4",                 # mp4 / webm / mkv
    resolution: str | None = None,    # "1920x1080" 等，None=保持原尺寸
    quality: str = "balance",         # high / balance / small
    vcodec: str = "libx264",
    audio: str = "keep",              # keep 保留(重编码) / none 去掉音频
    preset: str = "medium",
) -> list[str]:
    """组装格式转换命令。webm 强制 libvpx+libvorbis；mp4/mkv 走 libx264/GPU。

    缩放时用 lanczos 并归一为 yuv420p。
    """
    q = _CONVERT_QUALITY.get(quality, _CONVERT_QUALITY["balance"])
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin", "-i", input_path]
    if resolution:
        cmd += ["-vf", f"scale={resolution}:flags=lanczos,format=yuv420p"]
    if fmt == "webm":
        cmd += ["-c:v", "libvpx", "-b:v", q["vp"], "-g", "30"]
        if audio == "keep":
            cmd += ["-c:a", "libvorbis"]
    else:
        cmd += _enc_args(vcodec, q["crf"], preset)
        if audio == "keep":
            cmd += ["-c:a", "aac"]
    if audio == "none":
        cmd += ["-an"]
    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    return cmd


def build_audio_extract_cmd(input_path: str, output_path: str) -> list[str]:
    """提取音轨为 m4a（去掉视频流）。"""
    return [ffmpeg_exe(), "-y", "-hide_banner", "-nostdin", "-i", input_path,
            "-vn", "-c:a", "aac", "-progress", "pipe:1", "-nostats", output_path]