"""视频压缩页面：拖拽/选择文件 -> 设置参数 -> 批量入队压缩，实时进度。

对应 PRD：视频压缩 P1。UI 以卡片式布局，参数带 ? 帮助与状态。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from .. import state
from ..config import AppConfig
from ..task import CANCELLED, RUNNING, SUCCESS, CompressionTask, TaskPool
from .widgets import DropBox, HelpLabel, Segmented, TaskRow, form_label, page_head, section_title

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".ts", ".m4v", ".flv"}
_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]
_CRF_DEFAULTS = {"balanced": 18, "fast": 26, "ultrafast": 28}


def human_size(n: float) -> str:
    v = float(n)
    for u in _SIZE_UNITS:
        if v < 1024 or u == _SIZE_UNITS[-1]:
            return f"{v:.1f} {u}"
        v /= 1024


class CompressionPage(QWidget):
    started_all = Signal()
    task_count_changed = Signal(int, int, int)  # running, done, failed

    def __init__(self, pool: TaskPool, parent=None):
        super().__init__(parent)
        self._pool = pool
        self._tasks: dict[str, CompressionTask] = {}
        self._rows: dict[str, TaskRow] = {}
        self._done = self._failed = self._cancelled = 0
        self._env = None
        self._user_override_crf = False

        self._build_ui()
        state.state.env_changed.connect(self._on_env_change)
        if state.state.env is not None:
            self._on_env_change()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 12)
        outer.setSpacing(12)

        # 整页滚动主体：高级参数展开后页面变长滚动，不再积压压缩列表
        self.scroll = QScrollArea()
        self.scroll.setObjectName("PageScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(12)

        # 页面头（设计稿 .page-head：标题 + 副标题）
        head = QHBoxLayout()
        head.addLayout(page_head("视频压缩", "多文件拖入，硬件加速，实时进度"))
        head.addStretch(1)
        blay.addLayout(head)

        # 拖拽区（两行文字；整块可点击，等同「添加文件」）
        self.dropbox = DropBox("把多个视频拖到这里，或点击添加",
                               "支持批量 · mp4 / mkv / mov / webm / avi / ts")
        self.dropbox.clicked.connect(self._pick_files)
        self.dropbox.files_dropped.connect(self.add_files)
        blay.addWidget(self.dropbox)

        # 任务列表
        blay.addLayout(section_title("任务列表"))

        self.listarea = QScrollArea()
        self.listarea.setWidgetResizable(True)
        self.listarea.setObjectName("TaskList")
        self.listarea.setMinimumHeight(240)
        self.listcontainer = QWidget()
        self.listlay = QVBoxLayout(self.listcontainer)
        self.listlay.setContentsMargins(0, 0, 0, 0)
        self.listlay.setSpacing(4)
        self.listlay.addStretch(1)
        self.empty_hint = QLabel("暂无文件 — 拖拽视频到上方虚线框，或点击上方虚线框添加")
        self.empty_hint.setObjectName("EmptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.listlay.addWidget(self.empty_hint)
        self.listlay.addStretch(1)
        self.listarea.setWidget(self.listcontainer)
        blay.addWidget(self.listarea)

        # 参数区（表单卡片：标签列对齐）
        blay.addLayout(section_title("压缩参数"))

        card = QFrame()
        card.setObjectName("SettingCard")
        form = QFormLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        f_speed = QHBoxLayout()
        f_speed.setSpacing(6)
        self.speed = Segmented([
            ("超快", "ultrafast"),
            ("平衡", "balanced"),
            ("快速", "fast"),
        ])
        self.speed.setCurrentData("balanced")
        self.speed.currentChanged.connect(self._on_speed_changed)
        f_speed.addWidget(self.speed)
        f_speed.addWidget(HelpLabel("处理速度与压缩成效的取舍档。平衡适合绝大多数情况。"))
        f_speed.addStretch(1)
        form.addRow(form_label("压缩档位"), f_speed)

        f_gpu = QHBoxLayout()
        f_gpu.setSpacing(8)
        self.gpu = QCheckBox("开启硬件加速")
        self.gpu.setChecked(bool(AppConfig.instance().get("gpu_enabled")))
        self.gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gpu.toggled.connect(self._on_gpu_toggled)
        f_gpu.addWidget(self.gpu)
        self.gpu_sel = QComboBox()
        self.gpu_sel.addItem("自动（推荐）", "auto")
        self.gpu_sel.currentIndexChanged.connect(self._on_gpu_sel_changed)
        f_gpu.addWidget(self.gpu_sel)
        f_gpu.addWidget(HelpLabel("需 NVIDIA 显卡且当前 FFmpeg 含 NVENC；未检测到时自动回退软件编码。"))
        f_gpu.addStretch(1)
        form.addRow(form_label("硬件加速"), f_gpu)

        f_enc = QHBoxLayout()
        f_enc.setSpacing(6)
        self.enc_lbl = QLabel("检测中…")
        self.enc_lbl.setObjectName("Pill")
        self.enc_lbl.setProperty("soft", True)
        self.enc_lbl.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.enc_lbl.setToolTip("编码器由硬件自动检测；无可用 GPU 时回退软件编码 libx264。")
        f_enc.addWidget(self.enc_lbl)
        f_enc.addWidget(HelpLabel("由硬件自动检测（优先 NVIDIA），无 GPU 自动回退软件编码。"))
        f_enc.addStretch(1)
        form.addRow(form_label("编码器"), f_enc)

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
        self.od_pick.clicked.connect(self._pick_outdir)
        f_od.addWidget(self.od_custom, 1)
        f_od.addWidget(self.od_pick)
        form.addRow(form_label("输出目录"), f_od)

        self.adv = QPushButton("展开高级参数（CRF / 分辨率 / 帧率 / 并发 / 命名）")
        self.adv.setObjectName("Expander")
        self.adv.setCheckable(True)
        self.adv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv.setToolTip("显示 / 隐藏高级参数")
        self.adv.toggled.connect(self._on_adv_toggled)
        form.addRow(self.adv)
        blay.addWidget(card)

        # 高级参数（折叠卡片）
        self.adv_card = QFrame()
        self.adv_card.setObjectName("SettingCard")
        self.adv_card.setVisible(False)
        al = QFormLayout(self.adv_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.setHorizontalSpacing(12)
        al.setVerticalSpacing(10)

        f_crf = QHBoxLayout()
        f_crf.setSpacing(6)
        self.crf = QSpinBox()
        self.crf.setRange(0, 51)
        self.crf.setValue(AppConfig.instance().crf())
        self.crf.valueChanged.connect(self._mark_crf_override)
        f_crf.addWidget(self.crf)
        f_crf.addWidget(HelpLabel("数值越低越清晰、文件越大（0-51）。默认按速度档自动给出。"))
        f_crf.addStretch(1)
        al.addRow(form_label("CRF（画质）"), f_crf)

        f_res = QHBoxLayout()
        f_res.setSpacing(6)
        self.res = QComboBox()
        self.res.addItem("保持原尺寸", "keep")
        self.res.addItem("统一 1080p", "1080")
        self.res.addItem("统一 720p", "720")
        self.res.addItem("指定（宽×高）", "custom")
        self.res.currentIndexChanged.connect(self._on_res_changed)
        f_res.addWidget(self.res)
        self.res_w = QSpinBox(); self.res_w.setRange(2, 7680); self.res_w.setValue(1920)
        self.res_h = QSpinBox(); self.res_h.setRange(2, 4320); self.res_h.setValue(1080)
        self.res_w.setVisible(False); self.res_h.setVisible(False)
        f_res.addWidget(self.res_w)
        f_res.addWidget(form_label("×"))
        f_res.addWidget(self.res_h)
        f_res.addStretch(1)
        al.addRow(form_label("分辨率"), f_res)

        f_fps = QHBoxLayout()
        f_fps.setSpacing(6)
        self.fps = QComboBox()
        self.fps.addItem("保持原值", "keep")
        self.fps.addItem("指定", "custom")
        self.fps.currentIndexChanged.connect(self._on_fps_changed)
        f_fps.addWidget(self.fps)
        self.fps_v = QSpinBox(); self.fps_v.setRange(1, 240); self.fps_v.setValue(30)
        self.fps_v.setVisible(False)
        f_fps.addWidget(self.fps_v)
        f_fps.addStretch(1)
        al.addRow(form_label("帧率"), f_fps)

        f_conc = QHBoxLayout()
        f_conc.setSpacing(6)
        self.conc = QSpinBox()
        self.conc.setRange(0, 16)
        self.conc.setValue(AppConfig.instance().get_compress("concurrency") or 0)
        self.conc.setToolTip("0 = 自动（min 4, CPU核）")
        f_conc.addWidget(self.conc)
        f_conc.addWidget(HelpLabel("同时处理几路。0 自动；越大越快但越占 CPU。"))
        f_conc.addStretch(1)
        al.addRow(form_label("同时压缩（路）"), f_conc)

        self.suffix_edit = QLineEdit(AppConfig.instance().get_compress("suffix"))
        al.addRow(form_label("输出命名后缀"), self.suffix_edit)
        blay.addWidget(self.adv_card)
        self._on_od_changed()

        self.scroll.setWidget(body)
        self.scroll.viewport().installEventFilter(self)
        outer.addWidget(self.scroll, 1)

        # 底部操作（设计稿 .footer-actions：左提示/统计 + 右按钮组）
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.summary = QLabel("待添加文件")
        self.summary.setObjectName("Summary")
        actions.addWidget(self.summary)
        actions.addStretch(1)
        self.stop_btn = QPushButton("停止本轮")
        self.stop_btn.setObjectName("Ghost")
        self.stop_btn.clicked.connect(self._stop_all)
        self.add_btn = QPushButton("追加文件")
        self.add_btn.setObjectName("Ghost")
        self.add_btn.clicked.connect(self._pick_files)
        self.start_btn = QPushButton("开始压缩")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self._start)
        actions.addWidget(self.stop_btn)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.start_btn)
        outer.addLayout(actions)

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

    # ---------------- env ----------------
    def _on_env_change(self) -> None:
        self._env = state.state.env
        if self._env is None:
            return
        # 开关与全局配置保持一致（设置页/本页互切都走 env_changed 广播）
        cfg_on = bool(AppConfig.instance().get("gpu_enabled"))
        self.gpu.blockSignals(True)
        self.gpu.setChecked(cfg_on)
        self.gpu.blockSignals(False)
        # 选择框：自动 + 已检出的硬编（剔除失效的持久化选择）
        encoders = self._env.gpu_encoders or []
        self.gpu_sel.blockSignals(True)
        self.gpu_sel.clear()
        self.gpu_sel.addItem("自动（推荐）", "auto")
        for name in encoders:
            self.gpu_sel.addItem(name, name)
        sel = AppConfig.instance().get("gpu_encoder") or "auto"
        if sel not in [self.gpu_sel.itemData(i) for i in range(self.gpu_sel.count())]:
            sel = "auto"
            AppConfig.instance().set("gpu_encoder", "auto")
        self.gpu_sel.setCurrentIndex(
            [self.gpu_sel.itemData(i) for i in range(self.gpu_sel.count())].index(sel))
        self.gpu_sel.blockSignals(False)
        self._sync_gpu_row()
        self._refresh_enc_pill()

    def _refresh_enc_pill(self) -> None:
        """编码器胶囊：软编码显示灰底（soft），硬编高亮主题色——与转换页一致。"""
        env = self._env
        gpu_used = bool(self._env and self._env.gpu_encoders
                        and self.gpu.isChecked())
        enc = self._effective_encoder() if gpu_used else "libx264"
        label = enc if gpu_used else f"软件编码 · {enc}"
        self.enc_lbl.setText(label)
        self.enc_lbl.setProperty("soft", not gpu_used)
        self.enc_lbl.style().unpolish(self.enc_lbl)
        self.enc_lbl.style().polish(self.enc_lbl)
        if env:
            self.enc_lbl.setToolTip(env.label)

    def _effective_encoder(self) -> str:
        """按 开关 + 选择框 计算实际使用的编码器。"""
        if not self.gpu.isChecked() or not self._env:
            return "libx264"
        if not self._env.gpu_encoders:
            return "libx264"
        sel = self.gpu_sel.currentData()
        if sel != "auto" and sel in self._env.gpu_encoders:
            return sel
        return self._env.encoder  # auto：hevc 优先

    def _sync_gpu_row(self) -> None:
        """开关/选择框可用态：无硬编或关闭时选择框禁用。"""
        has = bool(self._env and self._env.gpu_encoders)
        self.gpu_sel.setEnabled(self.gpu.isChecked() and has)
        if not has:
            self.gpu_sel.setCurrentIndex(0)

    def _on_gpu_toggled(self, on: bool) -> None:
        # 与设置页同一机制：落库 + env_changed 广播，各页即时联动
        AppConfig.instance().set("gpu_enabled", bool(on))
        state.state.env_changed.emit()
        self._sync_gpu_row()
        self._refresh_enc_pill()

    def _on_gpu_sel_changed(self) -> None:
        AppConfig.instance().set("gpu_encoder", self.gpu_sel.currentData())
        self._refresh_enc_pill()

    # ---------------- 参数联动 ----------------
    def _on_adv_toggled(self, on: bool) -> None:
        self.adv.setChecked(on)
        self.adv_card.setVisible(on)
        self.adv.setText(
            ("收起高级参数（CRF / 分辨率 / 帧率 / 并发 / 命名）  ▴"
             if on else
             "展开高级参数（CRF / 分辨率 / 帧率 / 并发 / 命名）  ▾"))

    def _mark_crf_override(self, _: int) -> None:
        self._user_override_crf = True

    def _on_speed_changed(self) -> None:
        if not self._user_override_crf:
            self.crf.setValue(_CRF_DEFAULTS.get(self.speed.currentData(), 18))

    def _on_res_changed(self) -> None:
        show = self.res.currentData() == "custom"
        self.res_w.setVisible(show); self.res_h.setVisible(show)

    def _on_fps_changed(self) -> None:
        self.fps_v.setVisible(self.fps.currentData() == "custom")

    def _on_od_changed(self) -> None:
        custom = self.od_mode.currentData() == "custom"
        self.od_custom.setEnabled(custom); self.od_pick.setEnabled(custom)

    def _pick_outdir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.od_custom.text() or str(Path.home()))
        if d:
            self.od_custom.setText(d)

    def _pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mkv *.mov *.webm *.avi *.ts *.m4v *.flv);;所有文件 (*)")
        self.add_files(files)

    # ---------------- 文件列表与拖拽 ----------------
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
            if raw in self._tasks:
                continue
            self._make_row(p)

    def _make_row(self, p: Path) -> None:
        row = TaskRow(p.name, human_size(p.stat().st_size))
        row.remove_requested.connect(lambda r, src=p: self._remove_row(src))
        self.listlay.insertWidget(self.listlay.count() - 1, row)
        self._rows[str(p)] = row
        self._tasks[str(p)] = None
        self._refresh_summary()

    def _remove_row(self, src: Path) -> None:
        k = str(src)
        task = self._tasks.get(k)
        if task and task.status is RUNNING:
            task.request_stop()
        self._tasks.pop(k, None)
        row = self._rows.pop(k, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._refresh_summary()

    # ---------------- 运行 ----------------
    def _start(self) -> None:
        pending = [k for k, t in self._tasks.items() if t is None]
        if not pending:
            QMessageBox.information(self, "提示", "请先添加要压缩的视频。")
            return

        cfg = AppConfig.instance()
        enc = self._effective_encoder()
        custom_res = self.res.currentData() == "custom"
        params = {
            "encoder": enc,
            "crf": self.crf.value(),
            "preset": cfg.preset(),
            "resolution": self.res.currentData(),
            "resolution_w": self.res_w.value() if custom_res else None,
            "resolution_h": self.res_h.value() if custom_res else None,
            "fps": self.fps.currentData(),
            "fps_value": self.fps_v.value(),
            "suffix": self.suffix_edit.text().strip() or "_compressed",
        }
        cfg.set_compress("speed_mode", self.speed.currentData())
        cfg.set_compress("crf", self.crf.value())
        cfg.set_compress("resolution", self.res.currentData())
        cfg.set_compress("fps", self.fps.currentData())
        cfg.set_compress("concurrency", self.conc.value())
        cfg.set_compress("suffix", params["suffix"])
        cfg.set("output_dir_mode", self.od_mode.currentData())
        if self.od_mode.currentData() == "custom":
            cfg.set("output_dir_custom", self.od_custom.text())

        for k in pending:
            task = CompressionTask(k, dict(params))
            statekey = k
            task.signals.progress.connect(
                lambda pct, sk=statekey: self._on_progress(sk, pct))
            task.signals.finished.connect(self._on_finished)
            self._tasks[k] = task
            self._rows[k].set_waiting()
            self._pool.add(task)
        self.started_all.emit()

    def _stop_all(self) -> None:
        for t in self._tasks.values():
            if t is not None and t.status is RUNNING:
                t.request_stop()

    # ---------------- 事件 ----------------
    def _on_progress(self, key: str, pct: int) -> None:
        row = self._rows.get(key)
        if row is not None:
            row.set_running()
            row.set_progress(pct)

    def _on_finished(self, task: CompressionTask) -> None:
        row = self._rows.get(task.input_path)
        if row is None:
            return
        if task.status is SUCCESS:
            ratio = task.size_ratio()
            row.set_done(True, f"{human_size(task.result_size)}（{ratio:.0%}）",
                         f"输出：{Path(task.output_path).name}")
            self._done += 1
        elif task.status is CANCELLED:
            row.set_cancelled()
            self._cancelled += 1
        else:
            row.set_done(False, human_size(task.orig_size), task.message)
            self._failed += 1
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        self.summary.setText(
            f"共 {len(self._tasks)} 个 ｜ 完成 {self._done} ｜ 失败 {self._failed} ｜ 取消 {self._cancelled}")
        self.empty_hint.setVisible(len(self._tasks) == 0)
        running = sum(1 for t in self._tasks.values() if t and t.status is RUNNING)
        self.task_count_changed.emit(running, self._done, self._failed)

    def snapshot_counts(self) -> tuple[int, int, int]:
        running = sum(1 for t in self._tasks.values() if t and t.status is RUNNING)
        return running, self._done, self._failed