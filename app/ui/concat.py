"""视频拼接页面：按顺序添加多个视频 -> 拼成一个文件，实时进度。

对应 legacy `video_music/FFmpeg_Splicing.py`，收拢进桌面台（阶段二）。
基于 ffmpeg concat demuxer：快速流复制（-c copy，各段编码需一致）
或精确重编码（统一编码）。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from .. import state
from ..config import AppConfig
from ..task import CANCELLED, RUNNING, SUCCESS, ConcatTask, TaskPool
from .compression import VIDEO_EXTS, human_size
from .widgets import (
    DropBox, HelpLabel, Segmented, _COLOR_RUN, _COLOR_OK, _COLOR_ERR,
    _COLOR_WAIT, form_label, page_head, section_title,
)

_PRESET_BY_SPEED = {"balanced": "medium", "fast": "fast", "ultrafast": "ultrafast"}
_CRF_BY_SPEED = {"balanced": 18, "fast": 20, "ultrafast": 23}


class ConcatRow(QWidget):
    """输入文件行：序号 + 名称 + 上移/下移/移除。"""

    move_up = Signal(object)
    move_down = Signal(object)
    remove_requested = Signal(object)

    def __init__(self, index: int, name: str, size_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 4, 4)
        lay.setSpacing(8)
        self.index_lbl = QLabel(str(index))
        self.index_lbl.setMinimumWidth(24)
        self.index_lbl.setStyleSheet("color:#3b47d6;font-weight:700;")
        lay.addWidget(self.index_lbl, 0)
        self.name_lbl = QLabel(name)
        self.name_lbl.setObjectName("TaskName")
        self.name_lbl.setToolTip(name)
        self.name_lbl.setMinimumWidth(180)
        lay.addWidget(self.name_lbl, 1)
        self.size_lbl = QLabel(size_text)
        self.size_lbl.setObjectName("TaskMeta")
        lay.addWidget(self.size_lbl, 0)
        for label, sig in (("▲", self.move_up), ("▼", self.move_down)):
            b = QToolButton()
            b.setText(label)
            b.setObjectName("ReorderBtn")
            b.setToolTip("上移" if label == "▲" else "下移")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=sig: s.emit(self))
            lay.addWidget(b, 0)
        close = QToolButton()
        close.setText("×")
        close.setObjectName("TaskRemove")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(close, 0)

    def set_index(self, i: int) -> None:
        self.index_lbl.setText(str(i))


class ConcatPage(QWidget):
    def __init__(self, pool: TaskPool, parent=None):
        super().__init__(parent)
        self._pool = pool
        self._inputs: list[str] = []
        self._rows: dict[str, ConcatRow] = {}
        self._env = None
        self._task: ConcatTask | None = None
        self._build_ui()
        state.state.env_changed.connect(self._on_env_change)
        if state.state.env is not None:
            self._on_env_change()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 12)
        outer.setSpacing(12)

        # 整页滚动主体：参数全展开时页面变长滚动，不挤压任务列表
        self.scroll = QScrollArea()
        self.scroll.setObjectName("PageScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(12)

        head = QHBoxLayout()
        head.addLayout(page_head("视频拼接", "多视频按序拼接，快速流复制 / 统一重编码"))
        head.addStretch(1)
        blay.addLayout(head)

        self.dropbox = DropBox("把要拼接的视频按顺序拖到这里，或点击添加",
                               "列表自上而下即拼接顺序")
        self.dropbox.clicked.connect(self._pick_files)
        self.dropbox.files_dropped.connect(self.add_files)
        blay.addWidget(self.dropbox)
        self.setAcceptDrops(True)

        blay.addLayout(section_title("拼接文件"))

        self.listarea = QScrollArea()
        self.listarea.setWidgetResizable(True)
        self.listarea.setObjectName("TaskList")
        self.listarea.setMinimumHeight(240)
        self.listcontainer = QWidget()
        self.listlay = QVBoxLayout(self.listcontainer)
        self.listlay.setContentsMargins(0, 0, 0, 0)
        self.listlay.setSpacing(4)
        self.listlay.addStretch(1)
        self.empty_hint = QLabel("暂无文件 — 拖拽或点击上方虚线框添加，列表自上而下即拼接顺序")
        self.empty_hint.setObjectName("EmptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.listlay.addWidget(self.empty_hint)
        self.listlay.addStretch(1)
        self.listarea.setWidget(self.listcontainer)
        blay.addWidget(self.listarea)

        blay.addLayout(section_title("拼接参数"))

        card = QFrame()
        card.setObjectName("SettingCard")
        form = QFormLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        f_mode = QHBoxLayout()
        f_mode.setSpacing(6)
        self.mode = QComboBox()
        self.mode.addItem("快速流复制（推荐，编码一致时）", "copy")
        self.mode.addItem("精确重编码（统一编码）", "reencode")
        self.mode.currentIndexChanged.connect(self._on_mode_changed)
        f_mode.addWidget(self.mode)
        f_mode.addStretch(1)
        form.addRow(form_label("拼接方式"), f_mode)

        f_speed = QHBoxLayout()
        f_speed.setSpacing(6)
        self.speed = Segmented([
            ("超快", "ultrafast"),
            ("平衡", "balanced"),
            ("快速", "fast"),
        ])
        self.speed.setCurrentData("fast")
        self.speed.currentChanged.connect(self._on_speed_changed)
        f_speed.addWidget(self.speed)
        f_speed.addWidget(HelpLabel("仅重编码时生效。"))
        f_speed.addStretch(1)
        form.addRow(form_label("重编码速度"), f_speed)

        f_crf = QHBoxLayout()
        f_crf.setSpacing(6)
        self.crf = QSpinBox()
        self.crf.setRange(0, 51)
        self.crf.setValue(int(AppConfig.instance().get_concat("crf") or 20))
        f_crf.addWidget(self.crf)
        f_crf.addWidget(HelpLabel("数值越低越清晰、文件越大。仅重编码时生效。"))
        f_crf.addStretch(1)
        form.addRow(form_label("CRF（画质）"), f_crf)

        f_suffix = QHBoxLayout()
        f_suffix.setSpacing(6)
        self.suffix = QLineEdit(AppConfig.instance().get_concat("suffix"))
        f_suffix.addWidget(self.suffix)
        f_suffix.addStretch(1)
        form.addRow(form_label("输出命名后缀"), f_suffix)

        f_od = QHBoxLayout()
        f_od.setSpacing(8)
        self.od_mode = QComboBox()
        self.od_mode.addItem("同源目录 /out", "same")
        self.od_mode.addItem("指定目录", "custom")
        self.od_mode.currentIndexChanged.connect(self._on_od_changed)
        f_od.addWidget(self.od_mode)
        self.od_custom = QLineEdit(AppConfig.instance().get("output_dir_custom"))
        self.od_custom.setPlaceholderText("选择输出目录…")
        self.od_custom.setReadOnly(True)
        self.od_pick = QPushButton("浏览…")
        self.od_pick.setObjectName("Ghost")
        self.od_pick.clicked.connect(self._pick_outdir)
        f_od.addWidget(self.od_custom, 1)
        f_od.addWidget(self.od_pick)
        form.addRow(form_label("输出目录"), f_od)
        blay.addWidget(card)
        self._on_mode_changed()  # 初始同步 speed/crf 可用态（默认 copy 时禁用）
        self._on_od_changed()    # 初始同步输出目录行可用态

        self.scroll.setWidget(body)
        self.scroll.viewport().installEventFilter(self)
        outer.addWidget(self.scroll, 1)

        # 底部操作（设计稿 .footer-actions：左提示/统计 + 右按钮组）
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.summary = QLabel("0 个文件，待添加")
        self.summary.setObjectName("Summary")
        actions.addWidget(self.summary)
        actions.addStretch(1)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("Ghost")
        self.stop_btn.clicked.connect(self._stop)
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.clicked.connect(self._clear)
        self.add_btn = QPushButton("追加文件")
        self.add_btn.setObjectName("Ghost")
        self.add_btn.clicked.connect(self._pick_files)
        self.start_btn = QPushButton("开始拼接")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self._start)
        actions.addWidget(self.stop_btn)
        actions.addWidget(self.clear_btn)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.start_btn)
        outer.addLayout(actions)

        # 全局进度（拼接为单个作业）
        prog = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setObjectName("TaskBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(10)
        self.bar.setTextVisible(True)
        self.status_lbl = QLabel("就绪")
        self.status_lbl.setObjectName("TaskMeta")
        prog.addWidget(self.bar, 1)
        prog.addWidget(self.status_lbl, 0)
        outer.addLayout(prog)

    # ---------------- 拖拽（页面滚动后，拖拽事件由 viewport 接收） ----------------
    def eventFilter(self, obj, ev) -> bool:
        if ev.type() == QEvent.Type.DragEnter and ev.mimeData().hasUrls():
            ev.acceptProposedAction()
            return True
        if ev.type() == QEvent.Type.Drop:
            paths = [u.toLocalFile() for u in ev.mimeData().urls()]
            ev.acceptProposedAction()
            self.add_files(paths)
            return True
        return super().eventFilter(obj, ev)

    # ---- env / 参数联动 ----
    def _on_env_change(self) -> None:
        self._env = state.state.env

    def _on_mode_changed(self) -> None:
        reenc = self.mode.currentData() == "reencode"
        self.speed.setEnabled(reenc)
        self.crf.setEnabled(reenc)

    def _on_speed_changed(self, *_args) -> None:
        self.crf.setValue(_CRF_BY_SPEED.get(self.speed.currentData(), 20))

    def _on_od_changed(self) -> None:
        custom = self.od_mode.currentData() == "custom"
        self.od_custom.setEnabled(custom)
        self.od_pick.setEnabled(custom)

    def _pick_outdir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择输出目录",
                                             self.od_custom.text() or str(Path.home()))
        if d:
            self.od_custom.setText(d)

    def _pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mkv *.mov *.webm *.avi *.ts *.m4v *.flv);;所有文件 (*)")
        self.add_files(files)

    # ---- 列表 / 拖拽 ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        event.acceptProposedAction()
        self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        for raw in paths:
            p = Path(raw)
            if not p.exists() or not p.is_file():
                continue
            if p.suffix.lower() not in VIDEO_EXTS:
                QMessageBox.information(self, "已跳过", f"非视频文件已跳过：{p.name}")
                continue
            key = str(p)
            if key in self._inputs:
                continue
            self._inputs.append(key)
            row = ConcatRow(len(self._inputs), p.name, human_size(p.stat().st_size))
            row.move_up.connect(lambda r, k=key: self._move(k, -1))
            row.move_down.connect(lambda r, k=key: self._move(k, 1))
            row.remove_requested.connect(lambda r, k=key: self._remove(k))
            self.listlay.insertWidget(self.listlay.count() - 1, row)
            self._rows[key] = row
            self._rerender_indexes()
            self._refresh_summary()

    def _move(self, key: str, delta: int) -> None:
        i = self._inputs.index(key)
        j = i + delta
        if not (0 <= j < len(self._inputs)):
            return
        self._inputs[i], self._inputs[j] = self._inputs[j], self._inputs[i]
        self._rerender_indexes()

    def _rerender_indexes(self) -> None:
        # 按 _inputs 顺序重排子组件，保证布局与顺序一致
        for i, key in enumerate(self._inputs, 1):
            self._rows[key].set_index(i)
            self.listlay.removeWidget(self._rows[key])
            self.listlay.insertWidget(self.listlay.count() - 1, self._rows[key])

    def _remove(self, key: str) -> None:
        if key in self._inputs:
            self._inputs.remove(key)
        row = self._rows.pop(key, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._rerender_indexes()
        self._refresh_summary()

    def _clear(self) -> None:
        if self._task is not None and self._task.status is RUNNING:
            QMessageBox.information(self, "提示", "拼接进行中，请先停止。")
            return
        self._inputs.clear()
        for row in self._rows.values():
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._rerender_indexes()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        self.summary.setText(f"{len(self._inputs)} 个文件 ｜ 按当前列表顺序拼接")
        self.empty_hint.setVisible(len(self._inputs) == 0)

    # ---- 运行 ----
    def _start(self) -> None:
        if self._task is not None and self._task.status is RUNNING:
            QMessageBox.information(self, "提示", "已有拼接任务在运行。")
            return
        if len(self._inputs) < 2:
            QMessageBox.warning(self, "文件不足", "请至少添加 2 个视频（且顺序为拼接顺序）。")
            return

        cfg = AppConfig.instance()
        mode = self.mode.currentData()
        enc = self._env.encoder if self._env else "libx264"
        params = {
            "mode": mode,
            "encoder": enc,
            "crf": self.crf.value(),
            "preset": _PRESET_BY_SPEED[self.speed.currentData()],
            "suffix": self.suffix.text().strip() or "_concat",
        }
        cfg.set_concat("mode", mode)
        cfg.set_concat("crf", self.crf.value())
        cfg.set_concat("preset", params["preset"])
        cfg.set_concat("suffix", params["suffix"])
        cfg.set("output_dir_mode", self.od_mode.currentData())
        if self.od_mode.currentData() == "custom":
            cfg.set("output_dir_custom", self.od_custom.text())

        task = ConcatTask(list(self._inputs), dict(params))
        self._task = task
        task.signals.progress.connect(self._on_progress)
        task.signals.finished.connect(self._on_finished)
        self._set_state(RUNNING, "拼接中…")
        self.status_lbl.setText(f"拼接 {len(self._inputs)} 个文件…")
        self._pool.add(task)

    def _stop(self) -> None:
        if self._task is not None and self._task.status is RUNNING:
            self._task.request_stop()

    def _on_progress(self, pct: int) -> None:
        self.bar.setValue(pct)

    def _on_finished(self, task: ConcatTask) -> None:
        if task.status is SUCCESS:
            self.bar.setValue(100)
            self.status_lbl.setText(f"完成：{Path(task.output_path).name}")
            self.status_lbl.setStyleSheet(f"color:{_COLOR_OK};font-weight:600;")
        elif task.status is CANCELLED:
            self.status_lbl.setText("已取消")
            self.status_lbl.setStyleSheet(f"color:{_COLOR_WAIT};font-weight:600;")
        else:
            self.status_lbl.setText("失败")
            self.status_lbl.setStyleSheet(f"color:{_COLOR_ERR};font-weight:600;")
            self.status_lbl.setToolTip(task.message)
        self._task = None

    def _set_state(self, status: str, text: str) -> None:
        self.status_lbl.setText(text)
        if status is RUNNING:
            self.status_lbl.setStyleSheet(f"color:{_COLOR_RUN};font-weight:600;")