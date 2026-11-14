"""UI 行为回归测试：窗口状态持久化 / 快捷键 / 任务完成通知 / 拖拽 / 图标高 DPI。

全程 offscreen + 独立临时配置目录，不触碰用户真实 config.json。
运行：python tests/ui_behavior_test.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP = tempfile.mkdtemp(prefix="md_ui_")
os.environ["MEDIADESK_CONFIG_DIR"] = _TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize, Qt                      # noqa: E402
from PySide6.QtGui import QShortcut                       # noqa: E402
from PySide6.QtWidgets import QApplication                 # noqa: E402

results: list[tuple[str, bool, str]] = []


def check(name: str, cond, detail: str = "") -> None:
    results.append((name, bool(cond), detail))
    print(("[OK]   " if cond else "[FAIL] ") + name + (f" | {detail}" if detail else ""))


app = QApplication.instance() or QApplication(sys.argv)

from app.config import AppConfig, init_env           # noqa: E402
from app.task import TaskPool                         # noqa: E402
from app.ui import main_window as mw                 # noqa: E402
from app.ui.styles import QSS                         # noqa: E402

init_env()
app.setStyleSheet(QSS)
cfg = AppConfig.instance()

# ---------------- A1: 配置层 ui 节 ----------------
check("ui 节默认值齐全",
      all(k in cfg._data["ui"] for k in
          ("window_geometry", "window_maximized", "sidebar_collapsed",
           "last_page", "notify_on_finish")))
cfg.set_ui("last_page", 3)
check("set_ui 落盘后可读", cfg.get_ui("last_page") == 3)
cfg.update_ui({"sidebar_collapsed": True, "last_page": 1})
check("update_ui 批量写", cfg.get_ui("sidebar_collapsed") is True and cfg.get_ui("last_page") == 1)

# ---------------- A1: 窗口状态保存/恢复 ----------------
w1 = mw.MainWindow(TaskPool())
w1.setGeometry(40, 60, 1010, 720)
w1.sidebar.set_collapsed(True, animate=False)
w1.sidebar.select(2)
w1.close()
saved = cfg.get_ui("window_geometry")
check("关闭时保存几何", isinstance(saved, list) and saved[2] == 1010 and saved[3] == 720, str(saved))
check("关闭时保存侧栏折叠", cfg.get_ui("sidebar_collapsed") is True)
check("关闭时保存停留页", cfg.get_ui("last_page") == 2)

w2 = mw.MainWindow(TaskPool())
g = w2.geometry()
check("新窗口恢复几何", (g.x(), g.y(), g.width(), g.height()) == (40, 60, 1010, 720),
      f"{g.x()},{g.y()},{g.width()}x{g.height()}")
check("新窗口恢复侧栏折叠", w2.sidebar.is_collapsed() is True)
check("新窗口恢复停留页", w2.sidebar.current_index() == 2)
check("恢复的页面与栈一致", w2.stack.currentIndex() == 2)

# 屏幕外几何不得恢复（防换屏后打不开）
cfg.update_ui({"window_geometry": [-9000, -9000, 900, 600], "window_maximized": False,
               "sidebar_collapsed": False, "last_page": 0})
w3 = mw.MainWindow(TaskPool())
g3 = w3.geometry()
check("屏幕外几何被拒绝", g3.x() > -5000, f"{g3.x()},{g3.y()} {g3.width()}x{g3.height()}")

# ---------------- A3: 快捷键 ----------------
shortcuts = [s for s in w2.findChildren(QShortcut)]
seqs = sorted(s.key().toString() for s in shortcuts)
check("快捷键数量（7 切页 + 设置 + 打开 + 2×开始 + 停止）", len(shortcuts) == 12, str(seqs))
check("含 Ctrl+1 / Ctrl+7", "Ctrl+1" in seqs and "Ctrl+7" in seqs, str(seqs))
check("含 Ctrl+O 打开", "Ctrl+O" in seqs, str(seqs))
check("含 Ctrl+Enter 开始", any("Return" in s or "Enter" in s for s in seqs), str(seqs))
check("含 Esc 停止", "Esc" in seqs, str(seqs))

w2.sidebar.select(0)
next(s for s in shortcuts if s.key().toString() == "Ctrl+1").activated.emit()
check("Ctrl+1 切到第 1 页（总览）", w2.stack.currentIndex() == 0)
next(s for s in shortcuts if s.key().toString() == "Ctrl+5").activated.emit()
check("Ctrl+5 切到第 5 页（格式转换）", w2.stack.currentIndex() == 4, str(w2.stack.currentIndex()))
next(s for s in shortcuts if s.key().toString() == "Ctrl+,").activated.emit()
check("Ctrl+, 切到设置页", w2.stack.currentIndex() == len(mw.NAV) - 1)

# ---------------- A2: 批次完成通知 ----------------
alerts: list = []
_orig_alert = mw.QApplication.alert
mw.QApplication.alert = staticmethod(lambda *a, **k: alerts.append(a))  # type: ignore[assignment]
_hooked: list = []
_orig_maybe = w2._maybe_notify_batch
try:
    # 接线：_recount 把页面统计透传给通知判定
    w2._maybe_notify_batch = lambda r, d, f: _hooked.append((r, d, f))
    w2._recount()
    w2._maybe_notify_batch = _orig_maybe
    check("_recount 把统计透传给通知判定", _hooked == [(0, 0, 0)], str(_hooked))

    cfg.set_ui("notify_on_finish", True)
    w2._prev_running = 0
    w2._maybe_notify_batch(0, 0, 0)      # 空闲
    w2._maybe_notify_batch(2, 0, 0)      # 开工（记录批次起点）
    mid = len(alerts)
    w2._maybe_notify_batch(0, 2, 0)      # 全部结束
    check("批次结束触发提醒", len(alerts) > mid, f"alerts {mid}→{len(alerts)}")
    check("批次起点记录正确", w2._batch_base == (0, 0), str(w2._batch_base))

    alerts.clear()
    w2._maybe_notify_batch(1, 2, 0)      # 第二批开工，起点=(2,0)
    w2._maybe_notify_batch(0, 2, 0)      # 结束但无新增完成
    check("同一批无新增完成不重复提醒", len(alerts) == 0, str(len(alerts)))

    alerts.clear()
    w2.isActiveWindow = lambda: True      # 模拟窗口在前台
    w2._prev_running = 0
    w2._maybe_notify_batch(1, 2, 0)
    w2._maybe_notify_batch(0, 3, 0)
    check("窗口在前台时不打扰", len(alerts) == 0, str(len(alerts)))
    w2.__dict__.pop("isActiveWindow", None)

    alerts.clear()
    cfg.set_ui("notify_on_finish", False)
    w2._prev_running = 0
    w2._maybe_notify_batch(1, 3, 0)
    w2._maybe_notify_batch(0, 4, 0)
    check("关闭开关后不提醒", len(alerts) == 0)
finally:
    mw.QApplication.alert = _orig_alert       # type: ignore[assignment]
    w2._maybe_notify_batch = _orig_maybe
    cfg.set_ui("notify_on_finish", True)

# 设置页开关存在且可写
sp = w2._pages["全局设置"]
check("设置页有通知开关", hasattr(sp, "notify") and sp.notify.isChecked() is True)

# ---------------- A4: 拖拽 ----------------
from app.ui.compression import CompressionPage   # noqa: E402
from app.ui.rename_page import RenamePage         # noqa: E402
from app.ui.cut import CutPage                     # noqa: E402
from app.ui.concat import ConcatPage               # noqa: E402
from app.ui.convert import ConvertPage             # noqa: E402

pool = TaskPool()
pages = {"压缩": CompressionPage(pool), "切割": CutPage(pool), "拼接": ConcatPage(pool),
         "转换": ConvertPage(pool), "整理": RenamePage()}
for name, pg in pages.items():
    check(f"{name}页接受拖放", pg.acceptDrops() is True)

# 拖入文件夹 → 整理页填入并扫描
rp = pages["整理"]
folder = Path(_TMP) / "media"
folder.mkdir()
(folder / "a.txt").write_text("x", encoding="utf-8")
(folder / "b.txt").write_text("x", encoding="utf-8")


class _Url:
    def __init__(self, p): self._p = str(p)
    def toLocalFile(self): return self._p


class _Mime:
    def __init__(self, paths): self._paths = paths
    def hasUrls(self): return True
    def urls(self): return [_Url(p) for p in self._paths]


class _Ev:
    def __init__(self, paths): self._m = _Mime(paths)
    def mimeData(self): return self._m
    def acceptProposedAction(self): pass
    def ignore(self): pass


rp.dropEvent(_Ev([folder]))
check("拖入文件夹填入目标目录", rp.src_input.text() == str(folder), rp.src_input.text())
check("拖入后自动扫描出行", len(rp._items) >= 2, f"items={len(rp._items)}")

# ---------------- A5: 图标 ----------------
from app.ui import icons                          # noqa: E402

check("图标多档物理像素", len(icons._PHYS) >= 6 and max(icons._PHYS) >= 48,
      str(icons._PHYS))
for dpr in (1.0, 1.5, 2.0, 3.0):
    pm = icons.nav_icon("compress").pixmap(QSize(16, 16), dpr)
    check(f"16@{dpr:g} → {round(16 * dpr)}px 原生位图",
          pm.width() == round(16 * dpr), f"{pm.width()}x{pm.height()}")
ref = icons._pixmap(icons._DRAWERS["compress"], icons._NORMAL.name(), 36)
got = icons.nav_icon("compress").pixmap(QSize(18, 18), 2.0)
check("18@2x 命中 36px 原生图（非放大）", got.toImage() == ref.toImage())
check("图标缓存生效", icons._render.cache_info().hits > 0, str(icons._render.cache_info()))

# ---------------- 收尾 ----------------
fails = [r for r in results if not r[1]]
print(f"\nUI 行为校验: PASS {len(results) - len(fails)} / FAIL {len(fails)}")
sys.exit(1 if fails else 0)
