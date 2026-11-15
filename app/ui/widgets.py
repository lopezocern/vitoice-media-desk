"""共享 UI 组件：帮助按钮、分段选择器、任务行（文件名 + 进度条 + 状态）、输出目录行。

TaskRow 用于压缩页的每个文件：原始大小 -> 进度 -> 最终压缩率/状态。
OutputDirRow 为压缩/切割/拼接/转换/设置五页共用的输出目录行。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QCursor, QFont, QFontMetrics, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QProgressBar, QPushButton, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem, QToolButton, QToolTip, QVBoxLayout, QWidget,
)

from ..config import AppConfig

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


class OutputDirRow(QWidget):
    """输出目录行（五页共用）：同源/custom 下拉 + 只读目录框 + 浏览按钮。

    功能页在 _start 里用 mode_data()/custom_text() 取值批量落库；
    设置页等需要即时落库的场景连接 mode_changed / custom_changed。
    """

    mode_changed = Signal(str)      # "same" / "custom"
    custom_changed = Signal(str)    # 浏览选定的新目录

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.mode = QComboBox()
        self.mode.addItem("同源目录 /out", "same")
        self.mode.addItem("指定目录", "custom")
        self.mode.currentIndexChanged.connect(self._on_mode)
        lay.addWidget(self.mode)
        self.dir_edit = QLineEdit(AppConfig.instance().get("output_dir_custom"))
        self.dir_edit.setPlaceholderText("选择输出目录…")
        self.dir_edit.setReadOnly(True)
        self.pick_btn = QPushButton("浏览…")
        self.pick_btn.setObjectName("Ghost")
        self.pick_btn.clicked.connect(self._pick)
        lay.addWidget(self.dir_edit, 1)
        lay.addWidget(self.pick_btn)
        self._on_mode()

    def _on_mode(self) -> None:
        custom = self.mode.currentData() == "custom"
        self.dir_edit.setEnabled(custom)
        self.pick_btn.setEnabled(custom)
        self.mode_changed.emit(self.mode.currentData())

    def _pick(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.dir_edit.text() or str(Path.home()))
        if d:
            self.dir_edit.setText(d)
            self.custom_changed.emit(d)

    # ---- 取值接口 ----
    def mode_data(self) -> str:
        return self.mode.currentData()

    def custom_text(self) -> str:
        return self.dir_edit.text()

    def set_mode(self, data: str) -> None:
        idx = self.mode.findData(data)
        if idx >= 0:
            self.mode.setCurrentIndex(idx)


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


# ---- 下拉项自绘：主文案 + 右侧灰色说明 + 已选对勾 ----
# QSS 无法表达「弹出项单独选中态」与「一行内两段不同字号」，故走 delegate 自绘。
HINT_ROLE = Qt.ItemDataRole.UserRole + 101   # 右侧辅助说明（如 1080p / -an）
CHECK_ROLE = Qt.ItemDataRole.UserRole + 102  # 是否为当前已选值

_BRAND = "#4f5bd5"
_TEXT_MAIN = "#1c2333"
_TEXT_SUB = "#9aa3bd"
_TEXT_DIS = "#b9bfd2"
_TEXT_DIS_SUB = "#cfd5e2"


class HintItemDelegate(QStyledItemDelegate):
    """QComboBox 弹出项绘制：左侧主文案、右侧灰色说明、末位对勾。

    高亮态（鼠标悬停 / 键盘移动）统一为品牌色底白字，当前已选值额外带对勾——
    Qt 的弹出层无法区分「当前值」与「悬停项」，用对勾表达已选最清晰。
    """

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = option.rect.adjusted(2, 1, -2, -1)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)

        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_BRAND))
            painter.drawRoundedRect(rect, 6, 6)
            c_main, c_sub = QColor("#ffffff"), QColor(255, 255, 255, 184)
        elif not enabled:
            c_main, c_sub = QColor(_TEXT_DIS), QColor(_TEXT_DIS_SUB)
        else:
            c_main, c_sub = QColor(_TEXT_MAIN), QColor(_TEXT_SUB)

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        hint = str(index.data(HINT_ROLE) or "")
        checked = bool(index.data(CHECK_ROLE))
        base_font = option.font
        right = rect.right() - 10

        # 末位对勾（当前值）：用路径绘制，避免字体缺字形时显示成方块
        if checked:
            pen = QPen(c_sub)
            pen.setWidthF(1.7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            cx, cy = right - 5, rect.center().y()
            path = QPainterPath()
            path.moveTo(cx - 4.2, cy + 0.2)
            path.lineTo(cx - 1.2, cy + 3.0)
            path.lineTo(cx + 4.4, cy - 3.2)
            painter.drawPath(path)
            right -= 19

        # 右侧辅助说明
        if hint:
            f_h = QFont(base_font)
            f_h.setPointSizeF(7.9)
            painter.setFont(f_h)
            painter.setPen(c_sub)
            w = QFontMetrics(f_h).horizontalAdvance(hint)
            painter.drawText(QRect(right - w, rect.top(), w, rect.height()),
                             Qt.AlignmentFlag.AlignCenter, hint)
            right -= w + 10

        # 主文案（超宽省略）
        f_m = QFont(base_font)
        f_m.setPointSizeF(9.5)
        f_m.setBold(selected)
        painter.setFont(f_m)
        painter.setPen(c_main)
        left = rect.left() + 10
        avail = max(right - left, 12)
        shown = QFontMetrics(f_m).elidedText(text, Qt.TextElideMode.ElideRight, avail)
        painter.drawText(QRect(left, rect.top(), avail, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, shown)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        base = super().sizeHint(option, index)
        hint = str(index.data(HINT_ROLE) or "")
        extra = 0
        if hint:
            f = QFont(option.font)
            f.setPointSizeF(7.9)
            extra = QFontMetrics(f).horizontalAdvance(hint) + 20
        return QSize(base.width() + extra + 22, 33)


def set_combo_items(combo: QComboBox, items) -> None:
    """填充下拉并启用自绘：items = [(显示文案, data, 右侧说明或空)...]。"""
    combo.blockSignals(True)
    combo.clear()
    for row in items:
        label, data = row[0], row[1]
        hint = row[2] if len(row) > 2 else ""
        combo.addItem(label, data)
        combo.setItemData(combo.count() - 1, hint, HINT_ROLE)
    combo.blockSignals(False)
    bind_hint_combo(combo)


def bind_hint_combo(combo: QComboBox) -> None:
    """给已有下拉挂自绘 delegate，并让当前值带对勾（可重复调用）。"""
    if not isinstance(combo.itemDelegate(), HintItemDelegate):
        combo.setItemDelegate(HintItemDelegate(combo))
    _sync_combo_check(combo)
    if not getattr(combo, "_hint_bound", False):
        combo._hint_bound = True
        combo.currentIndexChanged.connect(lambda _i, c=combo: _sync_combo_check(c))


def _sync_combo_check(combo: QComboBox) -> None:
    """把「当前值」标记写入 CHECK_ROLE，供 delegate 画对勾。"""
    cur = combo.currentIndex()
    for i in range(combo.count()):
        combo.setItemData(i, i == cur, CHECK_ROLE)