"""渲染各页面高清截图，输出到 docs/assets/screenshots/ 供文档使用。"""
import os
import sys
import time

# 注意：用真实平台渲染以加载系统中文字体；离屏平台会因缺字体导致全部中文显示为“□”
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path

from app.config import init_env
from app.state import start_env_probe

init_env()
start_env_probe()
from app.task import TaskPool
from app.ui.main_window import MainWindow

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

app = __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication([])
from main import _apply_light_palette  # 与真实客户端一致：强制浅色，避免抓成系统深色

_apply_light_palette(app)
win = MainWindow(TaskPool())
win.resize(1280, 860)
win.show()

# 等待后台环境探测（FFmpeg / GPU 编码器）完成，截图要展示“就绪”态而非“检测中…”
from app import state as _state  # noqa: E402


def _wait_env_ready() -> None:
    for _ in range(80):  # 最多约 8s
        app.processEvents()
        if _state.state.env is not None:
            for _ in range(12):  # 多跑几帧让 UI 响应 env_changed 刷新布局
                app.processEvents()
                time.sleep(0.04)
            return
        time.sleep(0.1)


_wait_env_ready()

idx_by_name = {n: i for i, n in enumerate(win._pages.keys())}
for name, fn in [
    ("总览", "overview"),
    ("视频压缩", "compress"),
    ("视频切割", "cut"),
    ("视频拼接", "concat"),
    ("格式转换", "convert"),
    ("文件整理", "rename"),
    ("全局设置", "settings"),
]:
    win.sidebar.select(idx_by_name[name])
    win.raise_()
    win.activateWindow()
    for _ in range(6):
        app.processEvents()
        time.sleep(0.06)
    path = OUT / f"{fn}.png"
    win.grab().save(str(path))
    print("saved", path)
print("DONE", OUT)