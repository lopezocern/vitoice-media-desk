"""时间输入组件：时分秒三栏微调 + 秒/MM:SS/HH:MM:SS 智能解析。

供视频切割「设置切割时间段」弹窗等处复用；纯 Qt Widgets，无业务依赖。
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QWidget

_COL = "#8b93ab"


def parse_ts(text: str, fmt: str = "auto") -> int | None:
    """把用户输入解析为秒数。支持 秒 / MM:SS / HH:MM:SS。

    fmt: "auto" 自动识别；"s" 仅秒；"ms" 仅 MM:SS；"hms" 仅 HH:MM:SS。
    """
    t = (text or "").strip()
    if not t:
        return None
    t = t.replace("：", ":")
    parts = t.split(":")
    parts = [p for p in parts]
    if fmt == "s":
        if not t.isdigit():
            return None
        return int(t)
    if len(parts) == 1:
        if fmt == "auto" and t.isdigit():
            return int(t)
        if fmt in ("ms", "hms") and len(parts) == 1:
            # 无冒号视为秒；若明确要求 MM:SS 也可退化为秒
            return int(t) if t.isdigit() else None
        if not t.isdigit():
            return None
        return int(t)
    vals: list[int] = []
    for p in parts:
        if not p.isdigit():
            return None
        vals.append(int(p))
    sec = 0
    for v in vals:
        sec = sec * 60 + v
    return sec


def fmt_secs(sec: int) -> str:
    sec = max(0, int(sec))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


class TimeField(QWidget):
    """一行「时:分:秒」三栏微调时间输入。"""

    valueChanged = Signal()  # 任一栏被改动

    def __init__(self, parent=None):
        super().__init__(parent)
        self._h = QSpinBox()
        self._m = QSpinBox()
        self._s = QSpinBox()
        for sb, suffix, hi in ((self._h, " h", 999), (self._m, " m", 59), (self._s, " s", 59)):
            sb.setRange(0, hi)
            sb.setSuffix(suffix)
            sb.setFixedWidth(68)
            sb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sb.setAccelerated(True)
            sb.valueChanged.connect(self._on_changed)
            sb.setToolTip("上下箭头或直接输入数字微调")
        col1 = QLabel(":"); col2 = QLabel(":")
        for c in (col1, col2):
            c.setStyleSheet(f"color:{_COL};")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self._h)
        lay.addWidget(col1)
        lay.addWidget(self._m)
        lay.addWidget(col2)
        lay.addWidget(self._s)

    def _on_changed(self, _v) -> None:
        self.valueChanged.emit()

    def secs(self) -> int:
        return self._h.value() * 3600 + self._m.value() * 60 + self._s.value()

    def set_secs(self, sec: int) -> None:
        sec = max(0, int(sec))
        self._h.setValue(sec // 3600)
        self._m.setValue((sec % 3600) // 60)
        self._s.setValue(sec % 60)

    def set_from_str(self, text: str, fmt: str = "auto") -> bool:
        sec = parse_ts(text, fmt)
        if sec is None:
            return False
        self.set_secs(sec)
        return True