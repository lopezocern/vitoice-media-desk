"""UI 构建冒烟：无头实例化主窗口及各页，验证新布局/图标不带崩。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import init_env
init_env()
from app.task import TaskPool
from app.ui.icons import nav_icon
from app.ui.main_window import MainWindow

app = __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication([])

win = MainWindow(TaskPool())
win.resize(1080, 760)
win.show()
print("MainWindow OK, pages:", list(win._pages.keys()))

for k in ["overview", "compress", "cut", "concat", "convert", "rename", "settings"]:
    a, b = nav_icon(k), nav_icon(k, True)
    assert not a.isNull() and not b.isNull(), k

# 遍历压测每个页面的进入
for i in range(len(win._pages)):
    win.sidebar.select(i)
print("All pages selectable OK")

# 截图保存供人工查看
import tempfile
from pathlib import Path

out = Path(os.environ.get("UI_SHOT_DIR", tempfile.gettempdir())) / "mdesk_ui"
out.mkdir(parents=True, exist_ok=True)
idx_by_name = {n: i for i, n in enumerate(win._pages.keys())}
win.sidebar.select(idx_by_name["总览"])
app.processEvents()
win.grab().save(str(out / "overview.png"))
win.sidebar.select(idx_by_name["视频压缩"])
app.processEvents()
win.grab().save(str(out / "compress.png"))
win.sidebar.select(idx_by_name["全局设置"])
app.processEvents()
win.grab().save(str(out / "settings.png"))
print("shots →", out)
print("UI-BUILD-OK")