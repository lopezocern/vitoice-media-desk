"""FFmpeg 运行时检测：定位 ffmpeg/ffprobe、探测可用硬件编码器、读取媒体时长。

路径优先级（项目约束）：手动配置 > 随包 ffmpeg/bin > 系统 PATH。
PATH 内存在多个 ffmpeg 时，探测阶段自动优先选择带 NVENC 硬编的完整版，
避免被某些软件自带的精简版 ffmpeg（如 IDE 内置）抢占 PATH 首位。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from .config import AppConfig

# 探测阶段从 PATH 候选中选定的 ffmpeg 目录（模块级缓存；随每次探测刷新）
_resolved_dir: Optional[Path] = None


def _bundle_bit(name: str, base: Optional[Path] = None) -> Optional[str]:
    """随包 FFmpeg 路径：绿色版把 ffmpeg/ffprobe 放在应用根 `ffmpeg/bin`。

    base 缺省时：冻结态（PyInstaller）取可执行文件所在目录，开发态取项目根。
    - base/ffmpeg/bin/{name} 存在 → 返回该绝对路径
    - 否则返回 None
    """
    if base is None:
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).resolve().parent
        else:
            base = Path(__file__).resolve().parent.parent
    p = base / "ffmpeg" / "bin" / name
    return str(p) if p.is_file() else None


def _path_ffmpeg_candidates() -> list[str]:
    """按 PATH 顺序枚举所有 ffmpeg.exe（去重、忽略 .cmd 包装）。"""
    seen: set[str] = set()
    out: list[str] = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        d = d.strip().strip('"')
        if not d:
            continue
        p = Path(d) / "ffmpeg.exe"
        key = str(p).lower()
        if p.is_file() and key not in seen:
            seen.add(key)
            out.append(str(p))
    return out


def ffmpeg_exe() -> str:
    cfg = AppConfig.instance()
    if cfg.get("ffmpeg_path"):
        return cfg.get("ffmpeg_path")
    b = _bundle_bit("ffmpeg.exe")
    if b:
        return b
    if _resolved_dir is not None:
        p = _resolved_dir / "ffmpeg.exe"
        if p.is_file():
            return str(p)
    found = shutil.which("ffmpeg")
    return found or "ffmpeg"


def ffprobe_exe() -> str:
    b = _bundle_bit("ffprobe.exe")
    if b:
        return b
    if _resolved_dir is not None:
        p = _resolved_dir / "ffprobe.exe"
        if p.is_file():
            return str(p)
    return shutil.which("ffprobe") or "ffprobe"


class EnvProbe:
    """一次性环境自检结果，供设置页与压缩页展示。"""

    def __init__(self, ffmpeg_ok: bool, ffprobe_ok: bool, gpu_encoders: list[str],
                 ffmpeg_path: str = ""):
        self.ffmpeg_ok = ffmpeg_ok
        self.ffprobe_ok = ffprobe_ok
        self.gpu_encoders = gpu_encoders  # 优先序：hevc_nvenc -> h264_nvenc
        self.ffmpeg_path = ffmpeg_path    # 实际生效的 ffmpeg 完整路径（展示用）

    @property
    def encoder(self) -> str:
        # 压缩逻辑优先硬件；返回最终应使用的视频编码器
        if AppConfig.instance().get("gpu_enabled"):
            if "hevc_nvenc" in self.gpu_encoders:
                return "hevc_nvenc"
            if "h264_nvenc" in self.gpu_encoders:
                return "h264_nvenc"
        return "libx264"

    @property
    def label(self) -> str:
        if not self.ffmpeg_ok:
            return "未检测到 FFmpeg，请到设置指定路径"
        gpu_on = bool(AppConfig.instance().get("gpu_enabled"))
        if self.gpu_encoders and gpu_on:
            return f"硬件加速可用 · {self.encoder}"
        if gpu_on:
            return f"硬件加速已开启 · 未检测到 NVENC · 软件编码 {self.encoder}"
        return f"硬件加速已关闭 · 软件编码 {self.encoder}"


def _nvenc_of(ff: str) -> list[str]:
    try:
        out = subprocess.run(
            [ff, "-encoders"], capture_output=True, text=True, timeout=15
        ).stdout or ""
    except Exception:
        return []
    gpus: list[str] = []
    for name in ("hevc_nvenc", "h264_nvenc"):
        if name in out:
            gpus.append(name)
    return gpus


def probe_env() -> EnvProbe:
    """检测 ffmpeg 可用性与 NVIDIA 硬件编码器。耗时点应放在后台线程。"""
    global _resolved_dir
    cfg = AppConfig.instance()

    cands: list[str] = []
    for c in (cfg.get("ffmpeg_path"), _bundle_bit("ffmpeg.exe"), *_path_ffmpeg_candidates()):
        if c:
            cands.append(c)
    # 去重（保持顺序，Windows 不区分大小写）
    seen: set[str] = set()
    cands = [c for c in cands
             if not (str(c).lower() in seen or seen.add(str(c).lower()))]

    if not cands:
        _resolved_dir = None
        return EnvProbe(False, False, [], "")

    chosen: Optional[str] = None
    chosen_gpus: list[str] = []
    first_ok: Optional[str] = None
    first_gpus: list[str] = []
    for c in cands:
        if not _run_ok([c, "-version"]):
            continue
        g = _nvenc_of(c)
        if first_ok is None:
            first_ok, first_gpus = c, g
        if g:  # 首个带硬编的完整版即中选
            chosen, chosen_gpus = c, g
            break
    if chosen is None:
        chosen, chosen_gpus = first_ok, first_gpus
    if chosen is None:
        _resolved_dir = None
        return EnvProbe(False, False, [], "")

    _resolved_dir = Path(chosen).parent
    ffprobe_cand = _resolved_dir / "ffprobe.exe"
    if ffprobe_cand.is_file():
        ffprobe_ok = _run_ok([str(ffprobe_cand), "-version"])
    else:
        ffprobe_ok = _run_ok([shutil.which("ffprobe") or "ffprobe", "-version"])
    return EnvProbe(True, ffprobe_ok, chosen_gpus, chosen)


def _run_ok(argv: Sequence[str]) -> bool:
    try:
        return subprocess.run(argv, capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def probe_duration_ms(path: Path) -> int:
    """读取媒体时长（毫秒）。失败返回 0。"""
    try:
        out = subprocess.run(
            [
                ffprobe_exe(),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        return int(float(out) * 1000)
    except Exception:
        return 0
