"""桌面壳层：顶部标题栏 + 侧边导航 + 页面栈 + 底部全局任务栏。

阶段一启用：总览、视频压缩、全局设置；格式转换/文件整理为占位。
"""
from __future__ import annotations

from pathlib import Path
import os
import sys

from PySide6.QtCore import (
    QEasingCurve, QEvent, QPropertyAnimation, QRect, QSize, Qt, Signal,
)
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSizeGrip, QSpinBox, QStackedWidget,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .. import state
from ..config import AppConfig
from ..task import TaskPool
from .compression import CompressionPage
from .concat import ConcatPage
from .convert import ConvertPage
from .cut import CutPage
from .icons import nav_icon, window_icon
from .overview import OverviewPage
from .rename_page import RenamePage


def _logo_path() -> str:
    """定位品牌 logo 资源：常规运行取 app/assets，PyInstaller 冻结态取 exe 同级资源。"""
    asset_dir = Path(sys._MEIPASS) / "assets" if getattr(sys, "_MEIPASS", None) else Path(__file__).resolve().parent / "../assets"
    for name in ("logo_256.png", "logo.png"):
        p = asset_dir / name
        if p.exists():
            return str(p)
    return ""


from .widgets import HelpLabel, OutputDirRow  # noqa: E402

NAV = [
    ("总览", "overview"),
    ("视频压缩", "compress"),
    ("视频切割", "cut"),
    ("视频拼接", "concat"),
    ("格式转换", "convert"),
    ("文件整理", "rename"),
    ("全局设置", "settings"),
]


class Sidebar(QWidget):
    currentChanged = Signal(int)

    _FULL_W = 216

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setMinimumWidth(self._FULL_W)
        self.setMaximumWidth(self._FULL_W)
        self._collapsed = False
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 8)
        lay.setSpacing(1)
        self._buttons: list[QPushButton] = []
        self._icons: dict[int, str] = {}
        self._current = 0

        # 品牌标（logo 已在标题栏最左；侧边栏仅保留文字，避免重复标识）
        brand = QWidget()
        brand.setObjectName("SidebarBrand")
        blay = QHBoxLayout(brand)
        blay.setContentsMargins(14, 10, 10, 8)
        blay.setSpacing(9)
        btx = QVBoxLayout()
        btx.setSpacing(0)
        bt1 = QLabel("MediaDesk")
        bt1.setObjectName("BrandName")
        bt2 = QLabel("媒体工作台")
        bt2.setObjectName("BrandSub")
        btx.addWidget(bt1)
        btx.addWidget(bt2)
        blay.addLayout(btx)
        blay.addStretch(1)
        lay.addWidget(brand)

        self.add_group("工作台")
        for i, (name, _cls) in enumerate(NAV[:6]):
            b = self._make_item(i, name, _cls)
            lay.addWidget(b)
        lay.addSpacing(6)
        self.add_group("系统")
        for i in range(6, len(NAV)):
            name, _cls = NAV[i]
            b = self._make_item(i, name, _cls)
            lay.addWidget(b)
        lay.addStretch(1)

        footer = QWidget()
        footer.setObjectName("SidebarEnv")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(16, 4, 14, 14)
        flay.setSpacing(7)
        self.env_dot = QLabel("●")
        self.env_dot.setStyleSheet("color:#9aa3bd;font-size:8px;")
        self.env_lbl = QLabel("环境检测中…")
        self.env_lbl.setObjectName("TaskMeta")
        flay.addWidget(self.env_dot)
        flay.addWidget(self.env_lbl, 1)
        lay.addWidget(footer)

        self._buttons[0].setChecked(True)

    def set_env(self, text: str, ok: bool | None = None) -> None:
        color = {True: "#2f9e54", False: "#d1495b", None: "#c98a1b"}[ok]
        self.env_dot.setStyleSheet(f"color:{color};font-size:8px;")
        self.env_lbl.setText(text)

    def _make_item(self, idx: int, name: str, cls: str) -> QPushButton:
        b = QPushButton(name)
        b.setObjectName("NavItem")
        b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setIcon(nav_icon(cls))
        b.setIconSize(QSize(16, 16))
        self._icons[idx] = cls
        b.clicked.connect(lambda _=False, i=idx: self.select(i))
        self._buttons.append(b)
        return b

    def add_group(self, text: str) -> None:
        grp = QLabel(text)
        grp.setObjectName("NavGroup")
        self.layout().addWidget(grp)

    def select(self, index: int) -> None:
        self._current = index
        for i, b in enumerate(self._buttons):
            b.setChecked(i == index)
            b.setIcon(nav_icon(self._icons[i], brand=(i == index)))
        self.currentChanged.emit(index)

    def current_index(self) -> int:
        return self._current

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool, animate: bool = True) -> None:
        """折叠/展开侧栏；animate=False 用于启动恢复（避免闪一下动画）。"""
        self._collapsed = collapsed
        self._anim.stop()
        if collapsed:
            self.setMinimumWidth(0)
            if animate:
                self._anim.setStartValue(self.width())
                self._anim.setEndValue(0)
        else:
            self.setMinimumWidth(self._FULL_W)
            if animate:
                self._anim.setStartValue(max(self.width(), 0))
                self._anim.setEndValue(self._FULL_W)
        if animate:
            self._anim.start()
        else:
            self.setMaximumWidth(0 if collapsed else self._FULL_W)


class _TitleBar(QWidget):
    """无边框窗口标题栏：空白/文字区按住拖动窗口，双击最大化/还原。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            self._drag_offset = event.globalPosition().toPoint() - win.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            toggle = getattr(self.window(), "_toggle_max", None)
            if toggle:
                toggle()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class PlaceholderPage(QWidget):
    def __init__(self, name: str, note: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 12)
        t = QLabel(name)
        t.setObjectName("PageTitle")
        lay.addWidget(t)
        info = QLabel(note)
        info.setObjectName("TaskMeta")
        lay.addWidget(info)
        lay.addStretch(1)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _make_card(self, title: str, tip: str = "") -> tuple[QVBoxLayout, QFrame]:
        frame = QFrame()
        frame.setObjectName("SettingCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        h = QHBoxLayout()
        t = QLabel(title)
        t.setObjectName("ValueAccent")
        t.setStyleSheet("font-size:13.5px;font-weight:700;")
        h.addWidget(t)
        if tip:
            h.addWidget(HelpLabel(tip))
        h.addStretch(1)
        lay.addLayout(h)
        return lay, frame

    def _build_ui(self) -> None:
        cfg = AppConfig.instance()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 12)
        title = QLabel("全局设置")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        sub = QLabel("集中管理 FFmpeg 路径、硬件加速、输出默认目录与并发上限。")
        sub.setObjectName("PageSub")
        outer.addWidget(sub)
        outer.addSpacing(8)

        # FFmpeg
        lay, card = self._make_card("FFmpeg 路径", "留空用系统 PATH；指定后优先使用该路径 ffmpeg。")
        row = QHBoxLayout()
        self.ff_input = QLineEdit(cfg.get("ffmpeg_path"))
        self.ff_input.setPlaceholderText("留空 = 使用系统 PATH 中的 ffmpeg")
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._pick_ffmpeg)
        row.addWidget(self.ff_input, 1)
        row.addWidget(browse)
        lay.addLayout(row)
        self.ff_resolved = QLabel("当前使用：检测中…")
        self.ff_resolved.setObjectName("ValueAccent")
        lay.addWidget(self.ff_resolved)
        detect = QPushButton("重新检测环境")
        detect.setObjectName("Ghost")
        detect.clicked.connect(self._redetect)
        lay.addWidget(detect)
        outer.addWidget(card)

        # GPU
        lay, card = self._make_card("硬件加速", "开关只决定“是否用硬编”；前提是当前 FFmpeg 含 NVENC 且机器有 NVIDIA 显卡。")
        self.gpu = QCheckBox("允许 GPU 硬件编码（NVENC，需 NVIDIA 显卡）")
        self.gpu.setChecked(bool(cfg.get("gpu_enabled")))
        self.gpu.toggled.connect(self._on_gpu_toggled)
        lay.addWidget(self.gpu)
        self.gpu_status = QLabel("检测中…")
        self.gpu_status.setWordWrap(True)
        lay.addWidget(self.gpu_status)
        outer.addWidget(card)
        state.state.env_changed.connect(self._refresh_env_info)
        self._refresh_env_info()

        # 输出目录
        lay, card = self._make_card("输出目录默认", "压缩默认输出位置；模块内可临时覆盖。")
        self.od = OutputDirRow()
        self.od.set_mode(cfg.get("output_dir_mode") or "same")
        self.od.mode_changed.connect(
            lambda mode: AppConfig.instance().set("output_dir_mode", mode))
        self.od.custom_changed.connect(
            lambda d: AppConfig.instance().set("output_dir_custom", d))
        lay.addWidget(self.od)
        outer.addWidget(card)

        # 并发
        lay, card = self._make_card("默认同时压缩（路）", "0 表示自动（min 4, CPU核）。")
        row = QHBoxLayout()
        self.conc = QSpinBox()
        self.conc.setRange(0, 16)
        self.conc.setValue(cfg.get_compress("concurrency") or 0)
        self.conc.valueChanged.connect(self._on_conc)
        row.addWidget(self.conc)
        row.addStretch(1)
        lay.addLayout(row)
        outer.addWidget(card)

        # 任务通知
        lay, card = self._make_card(
            "任务通知", "整批任务结束时若窗口不在前台，弹托盘气泡并闪烁任务栏。")
        self.notify = QCheckBox("任务全部结束时通知我")
        self.notify.setChecked(bool(cfg.get_ui("notify_on_finish")))
        self.notify.toggled.connect(
            lambda v: AppConfig.instance().set_ui("notify_on_finish", bool(v)))
        lay.addWidget(self.notify)
        outer.addWidget(card)
        outer.addStretch(1)

    def _refresh_env_info(self) -> None:
        # 开关勾选态与全局配置同步（压缩页/设置页互切均走 env_changed）
        self.gpu.blockSignals(True)
        self.gpu.setChecked(bool(AppConfig.instance().get("gpu_enabled")))
        self.gpu.blockSignals(False)
        e = state.state.env
        if e is None or not e.ffmpeg_ok:
            self.ff_resolved.setText("当前使用：未检测到 FFmpeg，请指定路径")
            self.gpu_status.setText("未检测到 FFmpeg，无法判断硬件编码支持。")
            self.gpu_status.setStyleSheet("color:#d1495b;font-size:12.5px;")
            return
        self.ff_resolved.setText(f"当前使用：{e.ffmpeg_path}")
        if e.gpu_encoders:
            self.gpu_status.setText(f"已检测到 NVENC 硬件编码器（{'、'.join(e.gpu_encoders)}），开启开关即可使用。")
            self.gpu_status.setStyleSheet("color:#2f9e54;font-size:12.5px;")
        else:
            self.gpu_status.setText(
                "当前 FFmpeg 不含 NVENC 硬编（或显卡不支持），开启开关也将使用软件编码。"
                "可安装完整版 FFmpeg（如 gyan.dev full/essentials）并在上方指定路径。")
            self.gpu_status.setStyleSheet("color:#c98a1b;font-size:12.5px;")

    def _on_gpu_toggled(self, v: bool) -> None:
        # 单源 helper：落库 + env_changed 广播。EnvProbe.encoder/label 动态读
        # gpu_enabled，顶栏状态/总览/压缩页编码器胶囊同步刷新，无需重跑探测。
        state.set_gpu_enabled(v)

    def _pick_ffmpeg(self) -> None:
        import os
        f, _ = QFileDialog.getOpenFileName(self, "选择 ffmpeg", str(Path(os.getcwd())))
        if f:
            self.ff_input.setText(f)
            AppConfig.instance().set("ffmpeg_path", f)
            state.start_env_probe()

    def _redetect(self) -> None:
        AppConfig.instance().set("ffmpeg_path", self.ff_input.text().strip())
        state.start_env_probe()
        QMessageBox.information(self, "已提交", "已重新检测环境，稍后顶部状态会更新。")

    def _on_conc(self, v: int) -> None:
        AppConfig.instance().set_compress("concurrency", v)


class MainWindow(QMainWindow):
    _RESIZE_M = 6  # 无边框窗口边缘拖拽缩放阈值（px）

    def __init__(self, pool: TaskPool):
        super().__init__()
        self.setWindowTitle("媒体工作台 MediaDesk")
        icon_path = _logo_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))  # 任务栏 / Alt-Tab 窗口图标
        self.resize(1200, 820)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self._maximized = False
        self._restore_geo = None
        self._pool = pool
        self._resizing = Qt.Edge(0)          # 当前拖拽的缩放边
        self._resize_geo = None              # 拖拽起始窗口几何
        self._resize_pos = None              # 拖拽起始全局鼠标位置
        self._prev_running = 0               # 上一轮「运行中」任务数（用于批次完成判定）
        self._batch_base = (0, 0)            # 本批次开始时的（完成, 失败）累计值
        self._tray = None                    # 托盘图标（首次通知时才创建）
        self._build()
        self._restore_ui_state()
        self._init_shortcuts()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root.setMouseTracking(True)
        root.installEventFilter(self)
        self._root = root
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶部标题栏
        tb = _TitleBar()
        tb.setObjectName("TitleBar")
        tlay = QHBoxLayout(tb)
        tlay.setContentsMargins(14, 8, 10, 8)
        tlay.setSpacing(10)
        # logo + 品牌置顶最左（品牌识别在顶部）
        logo = QLabel()
        logo.setFixedSize(24, 24)
        logo.setScaledContents(True)
        lp = _logo_path()
        if lp:
            logo.setPixmap(QPixmap(lp))
        tlay.addWidget(logo)
        # 折叠按钮：紧邻 logo，醒目的左侧位（始终可见、收起后可再展开）
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("NavCollapse")
        self.collapse_btn.setIcon(window_icon("menu"))
        self.collapse_btn.setIconSize(QSize(16, 16))
        self.collapse_btn.setFixedSize(30, 26)
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.collapse_btn.setToolTip("显示/隐藏侧边栏")
        self.collapse_btn.clicked.connect(self._toggle_sidebar)
        tlay.addWidget(self.collapse_btn)
        self.app_title = QLabel("媒体工作台")
        self.app_title.setObjectName("AppTitle")
        tlay.addWidget(self.app_title)
        tagline = QLabel("MediaDesk")
        tagline.setStyleSheet("color:#9aa3bd;font-size:11px;font-weight:600;")
        tlay.addWidget(tagline)
        tlay.addStretch(1)
        self.env_caps = QLabel("检测中…")
        self.env_caps.setObjectName("EnvCaps")
        tlay.addWidget(self.env_caps)
        tlay.addSpacing(6)
        self._win_min = QPushButton()
        self._win_max = QPushButton()
        self._win_close = QPushButton()
        for b in (self._win_min, self._win_max, self._win_close):
            b.setText("")
            b.setFixedSize(38, 28)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setIconSize(QSize(16, 16))  # 与图标预渲染档位对齐，避免 18→15 缩放发虚
        self._win_min.setIcon(window_icon("min"))
        self._win_max.setIcon(window_icon("max"))
        self._win_close.setIcon(window_icon("close"))
        self._win_min.setObjectName("WinBtn")
        self._win_min.setToolTip("最小化")
        self._win_max.setObjectName("WinBtn")
        self._win_max.setToolTip("最大化/还原")
        self._win_close.setObjectName("WinBtnClose")
        self._win_close.setToolTip("关闭")
        self._win_min.clicked.connect(self.showMinimized)
        self._win_max.clicked.connect(self._toggle_max)
        self._win_close.clicked.connect(self.close)
        tlay.addWidget(self._win_min)
        tlay.addWidget(self._win_max)
        tlay.addWidget(self._win_close)
        outer.addWidget(tb)

        # 身体：侧边栏 + 页面栈
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar()
        body.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)

        # 底部全局任务栏
        bar = QFrame()
        bar.setObjectName("StatusBar")
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(16, 7, 16, 7)
        blay.setSpacing(18)
        self.bar_running = self._status_lbl("运行中")
        self.bar_done = self._status_lbl("完成")
        self.bar_failed = self._status_lbl("失败")
        blay.addWidget(self.bar_running)
        blay.addWidget(self.bar_done)
        blay.addWidget(self.bar_failed)
        blay.addStretch(1)
        env_hint = QLabel("硬件加速 · hevc_nvenc")
        env_hint.setStyleSheet("color:#9aa3bd;font-size:11.5px;")
        env_hint.setObjectName("EnvHint")
        blay.addWidget(env_hint)
        self.stop_all = QPushButton("停止全部")
        self.stop_all.setObjectName("Ghost")
        self.stop_all.clicked.connect(self._stop_all)
        blay.addWidget(self.stop_all)
        blay.addSpacing(2)
        self.size_grip = QSizeGrip(bar)
        self.size_grip.setFixedSize(16, 16)
        blay.addWidget(self.size_grip)
        outer.addWidget(bar)

        # 页面
        self._pages: dict[str, QWidget] = {}
        for name, kind in NAV:
            if kind == "overview":
                page = OverviewPage()
                page.module_activated.connect(self._activate_module)
            elif kind == "compress":
                page = CompressionPage(self._pool)
            elif kind == "cut":
                page = CutPage(self._pool)
            elif kind == "concat":
                page = ConcatPage(self._pool)
            elif kind == "convert":
                page = ConvertPage(self._pool)
            elif kind == "rename":
                page = RenamePage()
            elif kind == "settings":
                page = SettingsPage()
            else:
                page = PlaceholderPage(name, "该模块处于阶段二，尚未开发。")
            self._pages[name] = page
            self.stack.addWidget(page)
        self.sidebar.currentChanged.connect(self.stack.setCurrentIndex)
        for _name in ("视频压缩", "视频切割", "格式转换"):
            self._pages[_name].task_count_changed.connect(self._recount)
        state.state.env_changed.connect(self._refresh_env)
        if state.state.env is not None:
            self._refresh_env()

    # ---- 侧边栏 ----
    def _toggle_sidebar(self) -> None:
        self.sidebar.set_collapsed(not self.sidebar.is_collapsed())

    def _activate_module(self, kind: str) -> None:
        for i, (_name, k) in enumerate(NAV):
            if k == kind:
                self.sidebar.select(i)
                return

    # ---- 无边框窗口控制 ----
    def _toggle_max(self) -> None:
        if self._maximized:
            self.showNormal()
            if self._restore_geo:
                self.setGeometry(self._restore_geo)
            self._maximized = False
            self._win_max.setIcon(window_icon("max"))
        else:
            self._restore_geo = self.geometry()
            self._maximized = True
            self._win_max.setIcon(window_icon("restore"))
            if self.screen():
                self.setGeometry(self.screen().availableGeometry())

    # ---- 界面状态持久化 ----
    @staticmethod
    def _rect_visible(rect: QRect) -> bool:
        """几何是否仍落在某块屏幕内。

        防「换分辨率 / 拔掉外接屏」后窗口恢复到屏幕外，造成打不开的假死。
        """
        for screen in QGuiApplication.screens():
            inter = screen.availableGeometry().intersected(rect)
            if inter.width() >= 160 and inter.height() >= 60:
                return True
        return False

    def _restore_ui_state(self) -> None:
        """恢复上次退出时的窗口几何 / 最大化 / 侧栏折叠 / 停留页面。"""
        cfg = AppConfig.instance()
        raw = cfg.get_ui("window_geometry")
        rect = None
        if isinstance(raw, (list, tuple)) and len(raw) == 4:
            try:
                rect = QRect(*(int(v) for v in raw))
            except (TypeError, ValueError):
                rect = None
        if (rect is not None
                and rect.width() >= self.minimumWidth()
                and rect.height() >= self.minimumHeight()
                and self._rect_visible(rect)):
            self.setGeometry(rect)
            self._restore_geo = rect
        if cfg.get_ui("sidebar_collapsed"):
            self.sidebar.set_collapsed(True, animate=False)
        idx = cfg.get_ui("last_page")
        if isinstance(idx, int) and 0 <= idx < len(NAV):
            self.sidebar.select(idx)          # 同时经 currentChanged 切到对应页面
        if cfg.get_ui("window_maximized"):
            self._maximized = False
            self._toggle_max()

    def _save_ui_state(self) -> None:
        geo = self._restore_geo if (self._maximized and self._restore_geo) else self.geometry()
        try:
            AppConfig.instance().update_ui({
                "window_geometry": [geo.x(), geo.y(), geo.width(), geo.height()],
                "window_maximized": bool(self._maximized),
                "sidebar_collapsed": self.sidebar.is_collapsed(),
                "last_page": self.sidebar.current_index(),
            })
        except OSError:
            pass

    def closeEvent(self, event) -> None:
        self._save_ui_state()
        super().closeEvent(event)

    # ---- 全局快捷键 ----
    def _init_shortcuts(self) -> None:
        """Ctrl+1~7 切页｜Ctrl+, 设置｜Ctrl+O 添加｜Ctrl+Enter 开始｜Esc 停止。"""
        # 必须持有引用：QShortcut 的 Python 包装被回收后，其 activated 连接会失效
        self._shortcuts: list[QShortcut] = []

        def _bind(seq, slot) -> None:
            sc = QShortcut(seq, self)
            sc.activated.connect(slot)
            self._shortcuts.append(sc)

        for i in range(len(NAV)):
            _bind(QKeySequence(f"Ctrl+{i + 1}"), lambda i=i: self.sidebar.select(i))
        _bind(QKeySequence("Ctrl+,"), lambda: self.sidebar.select(len(NAV) - 1))
        _bind(QKeySequence.StandardKey.Open, self._shortcut_add)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            _bind(QKeySequence(seq), self._shortcut_start)
        _bind(QKeySequence("Esc"), self._shortcut_stop)

    def _shortcut_add(self) -> None:
        page = self.stack.currentWidget()
        for name in ("_pick_files", "_pick_dir"):
            fn = getattr(page, name, None)
            if callable(fn):
                fn()
                return

    def _shortcut_start(self) -> None:
        fn = getattr(self.stack.currentWidget(), "_start", None)
        if callable(fn):
            fn()

    def _shortcut_stop(self) -> None:
        page = self.stack.currentWidget()
        for name in ("_stop_all", "_stop"):
            fn = getattr(page, name, None)
            if callable(fn):
                fn()
                return

    # ---- 任务完成通知 ----
    def _ensure_tray(self) -> QSystemTrayIcon | None:
        if self._tray is not None:
            return self._tray
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        lp = _logo_path()
        icon = QIcon(lp) if lp else nav_icon("overview", brand=True)
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip("媒体工作台 MediaDesk")
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray
        return tray

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show()
            self.raise_()
            self.activateWindow()

    def _maybe_notify_batch(self, running: int, done: int, failed: int) -> None:
        """整批任务从「有运行」转为「全结束」时提醒，窗口在前台则不打扰。"""
        if self._prev_running == 0 and running > 0:
            self._batch_base = (done, failed)      # 记录批次起点
        prev, self._prev_running = self._prev_running, running
        if prev <= 0 or running > 0:
            return
        if not AppConfig.instance().get_ui("notify_on_finish"):
            return
        d = max(0, done - self._batch_base[0])
        f = max(0, failed - self._batch_base[1])
        if d + f <= 0 or self.isActiveWindow():
            return
        msg = f"完成 {d} 个" + (f"，失败 {f} 个" if f else "")
        tray = self._ensure_tray()
        if tray is not None:
            tray.showMessage("MediaDesk 任务结束", msg,
                             QSystemTrayIcon.MessageIcon.Information, 4000)
        QApplication.alert(self, 0)                # 任务栏闪烁，切回窗口即停

    # ---- 无边框窗口：边缘/角落拖拽缩放 ----
    def _resize_cursor(self, edges) -> Qt.CursorShape:
        e = int(edges)
        if e in (0b1010, 0b0101):      # 左|右 / 上|下（整边）
            return Qt.CursorShape.SizeHorCursor if e & 0b0011 else Qt.CursorShape.SizeVerCursor
        if e & 0b0011 and e & 0b1100:  # 四角
            return (Qt.CursorShape.SizeBDiagCursor
                    if (e & 0b0001) == (e & 0b1000)
                    else Qt.CursorShape.SizeFDiagCursor)
        if e & 0b0011:
            return Qt.CursorShape.SizeHorCursor
        if e & 0b1100:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def _resize_edges(self, p) -> Qt.Edge:
        w, h = self._root.width(), self._root.height()
        m = self._RESIZE_M
        e = Qt.Edge(0)
        if p.x() <= m: e |= Qt.Edge.LeftEdge
        if p.x() >= w - m: e |= Qt.Edge.RightEdge
        if p.y() <= m: e |= Qt.Edge.TopEdge
        if p.y() >= h - m: e |= Qt.Edge.BottomEdge
        return e

    def eventFilter(self, obj, ev) -> bool:
        if obj is not self._root:
            return super().eventFilter(obj, ev)
        t = ev.type()
        if t == QEvent.Type.MouseMove:
            if self.isMaximized():
                self._root.setCursor(Qt.CursorShape.ArrowCursor)
                return super().eventFilter(obj, ev)
            edges = self._resize_edges(ev.position().toPoint())
            self._root.setCursor(self._resize_cursor(edges))
            if self._resizing:
                self._apply_resize(ev.globalPosition().toPoint())
                return True
            return super().eventFilter(obj, ev)
        if t == QEvent.Type.MouseButtonPress:
            if (ev.button() == Qt.MouseButton.LeftButton and not self.isMaximized()
                    and self._resize_edges(ev.position().toPoint()) != Qt.Edge(0)):
                self._resizing = self._resize_edges(ev.position().toPoint())
                self._resize_geo = self.geometry()
                self._resize_pos = ev.globalPosition().toPoint()
                return True
        elif t == QEvent.Type.MouseButtonRelease:
            if self._resizing:
                self._resizing = Qt.Edge(0)
                return True
        return super().eventFilter(obj, ev)

    def _apply_resize(self, gpos) -> None:
        geo, pos = self._resize_geo, self._resize_pos
        if geo is None or pos is None:
            return
        dx = gpos.x() - pos.x()
        dy = gpos.y() - pos.y()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        e = int(self._resizing)
        if e & 0b0010: w = geo.width() + dx       # right
        if e & 0b1000: h = geo.height() + dy      # bottom
        if e & 0b0001:                            # left
            x = geo.x() + dx
            w = geo.width() - dx
        if e & 0b0100:                            # top
            y = geo.y() + dy
            h = geo.height() - dy
        mw, mh = self.minimumWidth(), self.minimumHeight()
        if w < mw:
            if e & 0b0001: x -= (mw - w)
            w = mw
        if h < mh:
            if e & 0b0100: y -= (mh - h)
            h = mh
        self.setGeometry(x, y, w, h)

    # ---- 底部任务栏 ----
    def _status_lbl(self, label: str) -> QLabel:
        lbl = QLabel(f"{label} 0")
        lbl.setStyleSheet("font-size:12px;color:#9aa3bd;font-weight:600;")
        return lbl

    def _recount(self, *_args) -> None:
        r = d = f = 0
        for name in ("视频压缩", "视频切割", "格式转换"):
            page = self._pages[name]
            if hasattr(page, "snapshot_counts"):
                cr, cd, cf = page.snapshot_counts()
                r += cr; d += cd; f += cf
        self.bar_running.setText(
            f'运行中 <span style="color:#4f5bd5;font-weight:700">{r}</span>'
        )
        self.bar_done.setText(
            f'完成 <span style="color:#2f9e54;font-weight:700">{d}</span>'
        )
        self.bar_failed.setText(
            f'失败 <span style="color:#d1495b;font-weight:700">{f}</span>'
        )
        self._maybe_notify_batch(r, d, f)

    def _stop_all(self) -> None:
        for name in ("视频压缩", "视频切割", "格式转换"):
            page = self._pages[name]
            if hasattr(page, "_stop_all"):
                page._stop_all()

    # ---- 环境 ----
    def _refresh_env(self) -> None:
        e = state.state.env
        self.env_caps.setText(e.label if e else "检测中…")
        hint = self.findChild(QLabel, "EnvHint")
        if e and e.ffmpeg_ok:
            gpu_on = bool(AppConfig.instance().get("gpu_enabled"))
            if e.gpu_encoders and gpu_on:
                self.sidebar.set_env(f"硬件加速 · {e.encoder}", True)
                if hint:
                    hint.setText(f"硬件加速 · {e.encoder}")
            elif e.gpu_encoders:
                self.sidebar.set_env(f"软件编码 · {e.encoder}", True)
                if hint:
                    hint.setText(f"硬件加速可开 · 当前软件编码 {e.encoder}")
            else:
                self.sidebar.set_env(f"软件编码 · {e.encoder}", True)
                if hint:
                    hint.setText(f"软件编码 · {e.encoder}")
        else:
            self.sidebar.set_env("环境未就绪", False)
            if hint:
                hint.setText("FFmpeg 未就绪")