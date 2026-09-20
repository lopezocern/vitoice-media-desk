"""共享 UI 组件：帮助按钮、分段选择器、任务行（文件名 + 进度条 + 状态）。

TaskRow 用于压缩页的每个文件：原始大小 -> 进度 -> 最终压缩率/状态。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QToolButton, QToolTip, QVBoxLayout, QWidget,
)
# 状态配色
_COLOR_RUN = "#4f5bd5"
_COLOR_OK = "#2f9e54"
_COLOR_ERR = "#d1495b"
_COLOR_WAIT = "#9aa3bd"


class HelpLabel(QToolButton):
    """圆形 ? 帮助按钮：悬停立即弹出说明（不等系统悬停延迟）。"""

    def __init__(self, tip: str, parent=None):
        super().__init__(parent)
        self.setText("?")
        self.setToolTip(tip)
        self.setCursor(QCursor(Qt.CursorShape.WhatsThisCursor))
        self.setFixedSize(16, 16)
        self.setObjectName("HelpLabel")

    def enterEvent(self, ev) -> None:
        # 16px 小目标 + 系统悬停延迟常常让用户以为“没有说明”；
        # 进入即显示，彻底消除等待。
        QToolTip.showText(QCursor.pos(), self.toolTip(), self)
        super().enterEvent(ev)


def form_label(text: str) -> QLabel:
    """参数表单的左侧标签（统一字号与灰阶，供各页 QFormLayout 使用）。"""
    lbl = QLabel(text)
    lbl.setObjectName("FormLbl")
    return lbl


def section_title(text: str) -> QHBoxLayout:
    """段落标题：主色竖条 + 13px 粗体文字（设计稿 .section-title）。"""
    box = QHBoxLayout()
    box.setSpacing(8)
    dot = QFrame()
    dot.setObjectName("SectionDot")
    dot.setFixedSize(5, 15)
    box.addWidget(dot)
    lbl = QLabel(text)
    lbl.setObjectName("SectionTitle")
    box.addWidget(lbl)
    box.addStretch(1)
    return box


def page_head(title: str, sub: str) -> QVBoxLayout:
    """页面头（设计稿 .page-head）：标题 + 灰色副标题。"""
    col = QVBoxLayout()
    col.setSpacing(3)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    col.addWidget(t)
    s = QLabel(sub)
    s.setObjectName("PageSub")
    col.addWidget(s)
    return col


class DropBox(QFrame):
    """两行拖拽区（设计稿 .dropzone）：整块可点击（等同「添加文件」），
    且自身接受文件拖放——拖放目标即组件本体，不依赖父级冒泡，最稳定。"""

    clicked = Signal()
    files_dropped = Signal(list)  # list[str]：拖入的文件路径

    def __init__(self, big: str, small: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DropBox")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAcceptDrops(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(6)
        b = QLabel(big)
        b.setObjectName("DropBig")
        b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = QLabel(small)
        s.setObjectName("DropSmall")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(b)
        lay.addWidget(s)

    def _urls_to_local(self, mime) -> list:
        return [u.toLocalFile() for u in mime.urls()]

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            self._set_hover(True)
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragLeaveEvent(self, ev):
        self._set_hover(False)
        ev.accept()

    def dropEvent(self, ev):
        self._set_hover(False)
        paths = self._urls_to_local(ev.mimeData())
        if paths:
            ev.acceptProposedAction()
            self.files_dropped.emit(paths)
        else:
            ev.ignore()

    def _set_hover(self, on: bool) -> None:
        # 拖入时用边框高亮反馈；Qt 动态属性需 style 排斥条件才生效
        self.setProperty("drophover", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class Segmented(QWidget):
    """分段选择器（设计稿 .seg）：互斥按钮组，替代下拉。

    API 对齐 QComboBox 的常用子集：currentData() / setCurrentData() / 信号 currentChanged(str)。
    """

    currentChanged = Signal(str)

    def __init__(self, items: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self._data: list[str] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        box = QFrame()
        box.setObjectName("SegBox")
        bl = QHBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._btns: list[QPushButton] = []
        for i, (label, data) in enumerate(items):
            self._data.append(data)
            b = QPushButton(label)
            b.setObjectName("SegBtn")
            b.setCheckable(True)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(lambda _=False, idx=i: self._on_click(idx))
            self._group.addButton(b, i)
            bl.addWidget(b)
            self._btns.append(b)
        lay.addWidget(box)
        if self._btns:
            self._btns[0].setChecked(True)

    def _on_click(self, idx: int) -> None:
        self.currentChanged.emit(self._data[idx])

    def currentData(self) -> str:
        for i, b in enumerate(self._btns):
            if b.isChecked():
                return self._data[i]
        return self._data[0] if self._data else ""

    def setCurrentData(self, data: str) -> None:
        if data in self._data:
            idx = self._data.index(data)
            if not self._btns[idx].isChecked():
                self._btns[idx].setChecked(True)
                self.currentChanged.emit(data)


class TaskRow(QWidget):
    remove_requested = Signal(object)  # (self)

    def __init__(self, name: str, size_text: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._size_text = size_text
        self.setObjectName("TaskRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(14)

        self.name_lbl = QLabel(name)
        self.name_lbl.setObjectName("TaskName")
        self.name_lbl.setToolTip(name)
        self.name_lbl.setMinimumWidth(150)
        lay.addWidget(self.name_lbl, 1)

        self.size_lbl = QLabel(size_text)
        self.size_lbl.setObjectName("TaskMeta")
        lay.addWidget(self.size_lbl, 0)

        self.bar = QProgressBar()
        self.bar.setObjectName("TaskBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(7)
        self.bar.setTextVisible(False)
        lay.addWidget(self.bar, 2)

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setObjectName("TaskPct")
        self.pct_lbl.setFixedWidth(44)
        self.pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.pct_lbl, 0)

        close = QToolButton()
        close.setText("×")
        close.setObjectName("TaskRemove")
        close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close.setToolTip("移除本行")
        close.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(close, 0)

        self.set_progress(0)

    def set_progress(self, pct: int) -> None:
        self.bar.setValue(min(max(pct, 0), 100))
        self.pct_lbl.setText(f"{pct}%")
        self.name_lbl.setStyleSheet("")
        if pct > 0:
            self._bar_chunk(_COLOR_RUN, "#7a5ce0")

    def set_running(self) -> None:
        self._bar_chunk(_COLOR_RUN, "#7a5ce0")
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_RUN};font-weight:700;")

    def set_done(self, ok: bool, ratio_text: str, msg: str = "") -> None:
        self.bar.setValue(100 if ok else 0)
        color = _COLOR_OK if ok else _COLOR_ERR
        status = "完成" if ok else "失败"
        self.pct_lbl.setText(status)
        self.pct_lbl.setStyleSheet(f"color:{color};font-weight:700;")
        self._bar_chunk(color, "#36b061" if ok else "")
        tip = f"{self._size_text} → {ratio_text}"
        if msg:
            tip += f"｜{msg}"
        self.setToolTip(tip)

    def set_cancelled(self) -> None:
        self.bar.setValue(0)
        self.pct_lbl.setText("已取消")
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_WAIT};font-weight:700;")
        self._bar_chunk(_COLOR_WAIT)

    def set_waiting(self) -> None:
        self.set_progress(0)
        self.pct_lbl.setText("等待中")
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_WAIT};")
        self._bar_chunk("#c6cddf")

    def _bar_chunk(self, color: str, gradient_to: str = "") -> None:
        chunk = (
            f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {color},stop:1 {gradient_to})"
            if gradient_to else color
        )
        self.bar.setStyleSheet(
            f"QProgressBar{{background:#edf0f7;border:none;border-radius:999px;}}"
            f"QProgressBar::chunk{{background:{chunk};border-radius:999px;}}"
        )