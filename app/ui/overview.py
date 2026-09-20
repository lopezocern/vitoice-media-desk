"""总览页：环境状态条 + 3 列模块入口网格（带图标）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from .. import state
from .icons import nav_icon

MODULES = [
    ("compress", "视频压缩", "已可用", "多文件拖入，硬件加速，实时进度"),
    ("cut", "视频切割", "已可用", "按时间段切割，快速 / 精确重编码"),
    ("concat", "视频拼接", "已可用", "多视频按序拼接，快速 / 统一重编码"),
    ("convert", "格式转换", "已可用", "mp4/webm/mkv，分辨率/画质/GPU/音频"),
    ("rename", "文件整理", "已可用", "中文名加拼音前缀，垃圾清理，干跑预览"),
    ("settings", "全局设置", "可配置", "FFmpeg 路径 / GPU / 输出目录 / 并发"),
]

_BADGE_STYLE = {
    "已可用": "background:#e7f6ec;color:#2f9e54;",
    "可配置": "background:#eef1f8;color:#64748b;",
}


class ModuleCard(QFrame):
    clicked = Signal(str)  # kind

    def __init__(self, kind: str, name: str, badge: str, desc: str, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._pressed = False
        self.setObjectName("ModuleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 13, 15, 13)
        lay.setSpacing(7)

        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(nav_icon(kind).pixmap(18, 18))
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background:#eef0fe;border-radius:9px;")
        head.addWidget(icon)
        head.addStretch(1)
        b = QLabel(badge)
        b.setStyleSheet(
            f"font-size:10.5px;font-weight:600;border-radius:999px;"
            f"padding:2px 9px;{_BADGE_STYLE.get(badge, _BADGE_STYLE['可配置'])}"
        )
        head.addWidget(b)
        lay.addLayout(head)

        t = QLabel(name)
        t.setStyleSheet("font-size:13.5px;font-weight:700;color:#1c2333;")
        lay.addWidget(t)
        d = QLabel(desc)
        d.setStyleSheet("font-size:11.5px;color:#64748b;line-height:1.5;")
        d.setWordWrap(True)
        lay.addWidget(d)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if (self._pressed
                and event.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(event.position().toPoint())):
            self._pressed = False
            self.clicked.emit(self._kind)
            event.accept()
            return
        self._pressed = False
        super().mouseReleaseEvent(event)


class OverviewPage(QWidget):
    module_activated = Signal(str)  # kind

    @staticmethod
    def _section(text: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(7)
        dot = QFrame()
        dot.setObjectName("SectionDot")
        dot.setFixedSize(5, 14)
        t = QLabel(text)
        t.setObjectName("SectionTitle")
        h.addWidget(dot)
        h.addWidget(t)
        h.addStretch(1)
        return w

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 12)

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("总览")
        title.setObjectName("PageTitle")
        title_box.addWidget(title)
        sub = QLabel("把零散的 FFmpeg 能力收拢到一个统一的桌面客户端。")
        sub.setObjectName("PageSub")
        title_box.addWidget(sub)
        head.addLayout(title_box)
        head.addStretch(1)
        lay.addLayout(head)
        lay.addSpacing(6)

        # 环境状态条
        lay.addWidget(self._section("环境状态"))
        self.env_card = QFrame()
        self.env_card.setObjectName("EnvStrip")
        el = QHBoxLayout(self.env_card)
        el.setContentsMargins(16, 13, 16, 13)
        el.setSpacing(14)
        self.env_ff = QLabel("检测中…")
        self.env_ff.setStyleSheet("font-size:12.5px;color:#3a4256;")
        self.env_gpu = QLabel("")
        self.env_enc = QLabel("")
        self.env_ff_dot = QLabel()
        self.env_ff_dot.setFixedSize(8, 8)
        self.env_ff_dot.setStyleSheet("background:#2f9e54;border-radius:4px;")
        el.addWidget(self.env_ff_dot)
        el.addWidget(self.env_ff)
        el.addSpacing(6)
        el.addWidget(self.env_gpu)
        el.addWidget(self.env_enc)
        el.addStretch(1)
        lay.addWidget(self.env_card)
        lay.addSpacing(10)

        lay.addWidget(self._section("模块"))
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (kind, name, badge, desc) in enumerate(MODULES):
            card = ModuleCard(kind, name, badge, desc)
            card.clicked.connect(self.module_activated.emit)
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)
        lay.addStretch(1)

        # 环境提示样式由 env probe 更新
        self._badge_enc = None
        state.state.env_changed.connect(self._refresh)
        if state.state.env is not None:
            self._refresh()

    def _refresh(self) -> None:
        e = state.state.env
        if e is None:
            return
        from ..config import AppConfig
        gpu_enabled = AppConfig.instance().get("gpu_enabled")
        if e.ffmpeg_ok:
            self.env_ff.setText("FFmpeg 可用")
            self.env_ff_dot.setStyleSheet("background:#2f9e54;border-radius:4px;")
        else:
            self.env_ff.setText("未检测到 FFmpeg（请到设置指定路径）")
            self.env_ff_dot.setStyleSheet("background:#d1495b;border-radius:4px;")
        if e.gpu_encoders and gpu_enabled:
            self.env_gpu.setText(f"{e.gpu_encoders[0]} · 硬件加速")
            self._env_pill(self.env_gpu, "gpu")
        else:
            self.env_gpu.setText("软件编码" if gpu_enabled else "硬件加速已关闭")
            self._env_pill(self.env_gpu, "soft")
        self.env_enc.setText(f"编码器 {e.encoder}")

    def _env_pill(self, lbl: QLabel, kind: str) -> None:
        if kind == "gpu":
            lbl.setStyleSheet(
                "font-size:11.5px;font-weight:600;color:#4f5bd5;"
                "background:#eef0fe;border-radius:999px;padding:3px 10px;"
            )
        else:
            lbl.setStyleSheet(
                "font-size:11.5px;font-weight:600;color:#64748b;"
                "background:#eef1f8;border-radius:999px;padding:3px 10px;"
            )