"""格式转换页面：目标容器 / 画质 / 分辨率 / GPU / 音频 / 提取音频。

对应 legacy `video_music/mp4towebm.py`，收拢进桌面台（阶段二），
并泛化为 mp4/webm/mkv 多容器转换，附加「仅提取音频」能力。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from .. import state
from ..config import AppConfig
from ..task import CANCELLED, RUNNING, SUCCESS, ConvertTask, TaskPool
from .compression import VIDEO_EXTS, human_size
from .widgets import (
    DropBox, HelpLabel, Segmented, TaskRow, form_label, page_head,
    section_title,
)

_RES_LABELS = [("保持原尺寸", "keep"), ("1920x1080", "1920x1080"),
               ("1280x720", "1280x720"), ("854x480", "854x480"),
               ("640x360", "640x360"), ("自定义", "custom")]


class ConvertPage(QWidget):
    task_count_changed = Signal(int, int, int)  # running, done, failed

    def __init__(self, pool: TaskPool, parent=None):
        super().__init__(parent)
        self._pool = pool
        self._tasks: dict[str, ConvertTask] = {}
        self._rows: dict[str, TaskRow] = {}
        self._done = self._failed = self._cancelled = 0
        self._env = None
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
        head.addLayout(page_head("格式转换", "mp4 / webm / mkv，分辨率 / 画质 / GPU / 音频"))
        head.addStretch(1)
        blay.addLayout(head)

        self.dropbox = DropBox("把视频拖到这里，或点击添加",
                               "支持 mp4 / mkv / mov / webm / avi / ts · 转换输出到设置目录")
        self.dropbox.clicked.connect(self._pick_files)
        self.dropbox.files_dropped.connect(self.add_files)
        blay.addWidget(self.dropbox)
        self.setAcceptDrops(True)

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

        blay.addLayout(section_title("输出设置"))

        card = QFrame()
        card.setObjectName("SettingCard")
        form = QFormLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # 操作类型：转换 / 提取音频（影响下方所有参数）
        f_audio_only = QHBoxLayout()
        f_audio_only.setSpacing(6)
        self.audio_only = QCheckBox("仅提取音频（转为 m4a，不转视频）")
        self.audio_only.setCursor(Qt.CursorShape.PointingHandCursor)
        self.audio_only.toggled.connect(self._on_audio_only_toggled)
        f_audio_only.addWidget(self.audio_only)
        f_audio_only.addWidget(HelpLabel("勾选后仅抽取音轨为 .m4a，下面的容器/画质/分辨率/GPU 均不生效。"))
        f_audio_only.addStretch(1)
        form.addRow(f_audio_only)

        f_fmt = QHBoxLayout()
        f_fmt.setSpacing(6)
        self.fmt = QComboBox()
        self.fmt.addItem("MP4（H.264/H.265）", "mp4")
        self.fmt.addItem("WebM（VP8）", "webm")
        self.fmt.addItem("MKV", "mkv")
        self.fmt.currentIndexChanged.connect(self._on_fmt_changed)
        f_fmt.addWidget(self.fmt)
        f_fmt.addStretch(1)
        form.addRow(form_label("目标格式"), f_fmt)

        f_quality = QHBoxLayout()
        f_quality.setSpacing(6)
        self.quality = Segmented([
            ("高画质", "high"),
            ("平衡", "balance"),
            ("低体积", "small"),
        ])
        self.quality.setCurrentData("balance")
        f_quality.addWidget(self.quality)
        f_quality.addStretch(1)
        form.addRow(form_label("画质"), f_quality)

        f_res = QHBoxLayout()
        f_res.setSpacing(6)
        self.res = QComboBox()
        for label, key in _RES_LABELS:
            self.res.addItem(label, key)
        self.res.currentIndexChanged.connect(self._on_res_changed)
        f_res.addWidget(self.res)
        self.custom_res = QLineEdit()
        self.custom_res.setPlaceholderText("如 1600x900")
        self.custom_res.setEnabled(False)
        self.custom_res.setFixedWidth(120)
        f_res.addWidget(self.custom_res)
        f_res.addStretch(1)
        form.addRow(form_label("分辨率"), f_res)

        f_audio = QHBoxLayout()
        f_audio.setSpacing(6)
        self.audio = QComboBox()
        self.audio.addItem("保留（重编码）", "keep")
        self.audio.addItem("去掉音频", "none")
        f_audio.addWidget(self.audio)
        f_audio.addStretch(1)
        form.addRow(form_label("音频"), f_audio)

        f_gpu = QHBoxLayout()
        f_gpu.setSpacing(6)
        self.gpu = QCheckBox("使用 GPU 硬件编码")
        self.gpu.setChecked(bool(AppConfig.instance().get("gpu_enabled")))
        self.gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gpu.toggled.connect(self._on_gpu_toggled)
        f_gpu.addWidget(self.gpu)
        f_gpu.addWidget(HelpLabel("仅 mp4/mkv 可开（hevc_nvenc）；webm 固定软件编码。需机器有可用的 NVIDIA 编码。"))
        f_gpu.addSpacing(4)
        self.enc_pill = QLabel("")
        self.enc_pill.setObjectName("Pill")
        self.enc_pill.setProperty("soft", "true")
        f_gpu.addWidget(self.enc_pill)
        f_gpu.addStretch(1)
        form.addRow(form_label("硬件加速"), f_gpu)

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
        self._on_od_changed()  # 初始同步输出目录行可用态

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
        self.start_btn = QPushButton("开始转换")
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

    # ---- 联动 ----
    def _on_env_change(self) -> None:
        self._env = state.state.env
        if self._env is not None:
            self._sync_gpu_enabled()
            self._update_enc()

    def _on_audio_only_toggled(self, checked: bool) -> None:
        for w in (self.fmt, self.quality, self.res, self.custom_res, self.gpu, self.audio):
            w.setEnabled(not checked)

    def _on_fmt_changed(self) -> None:
        self._sync_gpu_enabled()
        self._update_enc()

    def _on_gpu_toggled(self, checked: bool) -> None:
        # 勾选 GPU 时给出是否有可用硬编的提示
        if checked and self._env is not None and not self._env.gpu_encoders:
            QMessageBox.information(
                self, "提示", "当前环境未检测到可用的 NVIDIA 硬件编码，将回退到软件编码。")
        self._update_enc()

    def _update_enc(self) -> None:
        env = self._env
        fmt = self.fmt.currentData()
        gpu_on = self.gpu.isChecked() and fmt in ("mp4", "mkv")
        gpu_ok = gpu_on and env is not None and bool(env.gpu_encoders)
        vc = env.encoder if gpu_ok else ("libx264" if fmt != "webm" else "libvpx")
        self.enc_pill.setText(vc)
        self.enc_pill.setProperty("soft", "true" if not gpu_ok else "false")
        style = self.enc_pill.style()
        style.unpolish(self.enc_pill)
        style.polish(self.enc_pill)

    def _sync_gpu_enabled(self) -> None:
        # 勾选态与全局配置同步（压缩页/设置页切换均走 env_changed 广播）
        self.gpu.blockSignals(True)
        self.gpu.setChecked(bool(AppConfig.instance().get("gpu_enabled")))
        self.gpu.blockSignals(False)
        fmt = self.fmt.currentData()
        if self.audio_only.isChecked():
            self.gpu.setEnabled(False)
            return
        self.gpu.setEnabled(fmt in ("mp4", "mkv"))

    def _on_res_changed(self) -> None:
        self.custom_res.setEnabled(self.res.currentData() == "custom")

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
            if key in self._tasks:
                continue
            row = TaskRow(p.name, human_size(p.stat().st_size))
            row.remove_requested.connect(lambda r, s=key: self._remove(s))
            self.listlay.insertWidget(self.listlay.count() - 1, row)
            self._rows[key] = row
            self._tasks[key] = None
            self._refresh_summary()

    def _remove(self, key: str) -> None:
        task = self._tasks.get(key)
        if task is not None and task.status is RUNNING:
            task.request_stop()
        self._tasks.pop(key, None)
        row = self._rows.pop(key, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._refresh_summary()

    def _resolved_resolution(self) -> str | None:
        key = self.res.currentData()
        if key == "custom":
            raw = self.custom_res.text().strip()
            return raw or None
        return None if key == "keep" else key

    # ---- 运行 ----
    def _start(self) -> None:
        pending = [k for k, t in self._tasks.items() if t is None]
        if not pending:
            QMessageBox.information(self, "提示", "请先添加要转换的视频。")
            return

        cfg = AppConfig.instance()
        env = self._env
        audio_only = self.audio_only.isChecked()
        fmt = self.fmt.currentData()
        quality = self.quality.currentData()
        want_gpu = self.gpu.isChecked() and fmt in ("mp4", "mkv")
        gpu_ok = want_gpu and env is not None and bool(env.gpu_encoders)
        vcodec = env.encoder if gpu_ok else ("libx264" if fmt != "webm" else "libvpx")
        resolution = None if audio_only else self._resolved_resolution()

        params = {
            "audio_only": audio_only,
            "fmt": fmt,
            "quality": quality,
            "resolution": resolution,
            "vcodec": vcodec,
            "audio": self.audio.currentData(),
            "preset": "medium",
        }
        cfg.set_convert("fmt", fmt)
        cfg.set_convert("quality", quality)
        cfg.set_convert("gpu", want_gpu)
        cfg.set_convert("audio", params["audio"])
        cfg.set_convert("audio_only", audio_only)
        cfg.set_convert("resolution", self.res.currentData())
        if self.res.currentData() == "custom":
            cfg.set_convert("custom_res", self.custom_res.text().strip())
        cfg.set("output_dir_mode", self.od_mode.currentData())
        if self.od_mode.currentData() == "custom":
            cfg.set("output_dir_custom", self.od_custom.text())

        for k in pending:
            task = ConvertTask(k, dict(params))
            self._tasks[k] = task
            task.signals.progress.connect(lambda pct, sk=k: self._on_progress(sk, pct))
            task.signals.finished.connect(self._on_finished)
            self._rows[k].set_waiting()
            self._pool.add(task)
        self._refresh_summary()

    def _stop_all(self) -> None:
        for t in self._tasks.values():
            if t is not None and t.status is RUNNING:
                t.request_stop()

    # ---- 事件 ----
    def _on_progress(self, key: str, pct: int) -> None:
        row = self._rows.get(key)
        if row is not None:
            row.set_running()
            row.set_progress(pct)

    def _on_finished(self, task: ConvertTask) -> None:
        row = self._rows.get(task.input_path)
        if row is None:
            return
        if task.status is SUCCESS:
            row.set_done(True, Path(task.output_path).name)
            self._done += 1
        elif task.status is CANCELLED:
            row.set_cancelled()
            self._cancelled += 1
        else:
            row.set_done(False, "转换失败", task.message)
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