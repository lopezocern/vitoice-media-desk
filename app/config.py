"""配置中心：读写本地 config.json，各模块共享默认参数。

使用方式：AppConfig 单例。读取时如键缺失或值非法，回退到 DEFAULT。
所有写操作立即落盘（save_json）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_base = os.environ.get("MEDIADESK_CONFIG_DIR")
CONFIG_DIR = (
    Path(_base) if _base
    else Path(os.environ.get("APPDATA", str(Path.home()))) / "MediaDesk"
)
CONFIG_FILE = CONFIG_DIR / "config.json"

# 默认值（阶段一）。"编码器"设计为 None，表示运行期自动检测后回填。
DEFAULTS: dict[str, Any] = {
    "ffmpeg_path": "",          # 空 => 走 PATH；设置里可手动指定
    "output_dir_mode": "same",  # same=同源/out, custom=指定目录
    "output_dir_custom": "",
    "gpu_enabled": True,        # 是否允许硬件编码
    "gpu_encoder": "auto",      # auto=按检测优先序 / 指定 hevc_nvenc|h264_nvenc
    "compress": {
        "speed_mode": "balanced",      # balanced / fast / ultrafast
        "crf": None,                   # None => 按速度档取默认
        "bitrate_mode": "auto",        # auto / fixed / targetsize
        "resolution": "keep",          # keep / 1080 / 720 / custom
        "resolution_w": 1920,
        "resolution_h": 1080,
        "fps": "keep",                 # keep / custom
        "fps_value": 30,
        "suffix": "_compressed",       # 输出命名后缀
        "concurrency": 0,              # 0 => 自动 min(4, cpu)
    },
    "cut": {
        "mode": "reencode",            # reencode=精确重编码 / copy=快速流复制
        "crf": 18,
        "preset": "fast",
        "suffix": "_cut",              # 每段时间输出命名后缀（实际 <stem>_<i><ext>）
    },
    "concat": {
        "mode": "copy",                # copy=快速流复制 / reencode=精确重编码
        "crf": 18,
        "preset": "fast",
        "suffix": "_concat",           # 拼接输出命名后缀（实际 <前置名><后缀>）
    },
    "convert": {
        "fmt": "mp4",                  # 目标容器：mp4 / webm / mkv
        "quality": "balance",          # high / balance / small
        "resolution": "keep",          # keep / 1920x1080 / 1280x720 / 854x480 / 640x360 / custom
        "custom_res": "",              # 自定义 WxH
        "gpu": False,                  # 是否用 hevc_nvenc（mp4/mkv）
        "audio": "keep",               # keep=保留重编码 / none=去掉音频
        "prefer_soft": True,           # 预留：软件编码优先
        "audio_only": False,           # 仅提取音频
    },
    "log_enabled": True,
}

CRF_BY_SPEED = {"balanced": 18, "fast": 26, "ultrafast": 28}
PRESET_BY_SPEED = {"balanced": "medium", "fast": "fast", "ultrafast": "ultrafast"}


class AppConfig:
    _inst: "AppConfig | None" = None

    def __init__(self) -> None:
        self._data: dict[str, Any] = json.loads(json.dumps(DEFAULTS))
        self._load()

    @classmethod
    def instance(cls) -> "AppConfig":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def _load(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        merged = DEFAULTS.copy()
        merged.update({k: raw[k] for k in raw if k in DEFAULTS})
        # 子字典做浅合并，保护默认子键
        merged["compress"] = {**DEFAULTS["compress"], **raw.get("compress", {})}
        merged["cut"] = {**DEFAULTS["cut"], **raw.get("cut", {})}
        merged["concat"] = {**DEFAULTS["concat"], **raw.get("concat", {})}
        merged["convert"] = {**DEFAULTS["convert"], **raw.get("convert", {})}
        self._data = merged

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            CONFIG_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    # ---- 通用读写 ----
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get_compress(self, key: str) -> Any:
        return self._data["compress"].get(key)

    def set_compress(self, key: str, value: Any) -> None:
        self._data["compress"][key] = value
        self.save()

    # ---- 切割子配置 ----
    def get_cut(self, key: str) -> Any:
        return self._data["cut"].get(key)

    def set_cut(self, key: str, value: Any) -> None:
        self._data["cut"][key] = value
        self.save()

    # ---- 拼接子配置 ----
    def get_concat(self, key: str) -> Any:
        return self._data["concat"].get(key)

    def set_concat(self, key: str, value: Any) -> None:
        self._data["concat"][key] = value
        self.save()

    # ---- 格式转换子配置 ----
    def get_convert(self, key: str) -> Any:
        return self._data["convert"].get(key)

    def set_convert(self, key: str, value: Any) -> None:
        self._data["convert"][key] = value
        self.save()

    # ---- 便捷派生态度 ----
    def crf(self) -> int:
        v = self._data["compress"].get("crf")
        return int(v) if v else CRF_BY_SPEED[self._data["compress"]["speed_mode"]]

    def preset(self) -> str:
        return PRESET_BY_SPEED[self._data["compress"]["speed_mode"]]

    def concurrency(self) -> int:
        c = int(self._data["compress"].get("concurrency") or 0)
        if c > 0:
            return c
        return max(1, min(4, os.cpu_count() or 2))

    def output_dir(self, source_dir: Path) -> Path:
        """结合 output 模式，从源文件目录推出本次输出的目录。"""
        if self._data["output_dir_mode"] == "custom" and self._data["output_dir_custom"]:
            p = Path(self._data["output_dir_custom"])
            if p.is_absolute():
                return p
        return source_dir / "out"


def init_env() -> None:
    """应用启动时确保配置目录存在并存在备份默认配置（保留用户已有数据）。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = AppConfig.instance()
    if not CONFIG_FILE.exists() or CONFIG_FILE.stat().st_size == 0:
        cfg.save()