"""渲染各页面高清截图，输出到 docs/assets/screenshots/ 供文档使用。"""
import os
import sys
import time

# 注意：用真实平台渲染以加载系统中文字体；离屏平台会因缺字体导致全部中文显示为“□”
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path

from app.config import init_env

init_env()
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