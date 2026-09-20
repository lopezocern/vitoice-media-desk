"""视频切割页面：拖拽/选择文件 -> 逐个设置时间段 -> 批量切割，实时进度。

对应 legacy `video_music/FFmpeg_cut.py`，收拢进桌面台（阶段二）。
支持「精确重编码」与「快速流复制」两种方式；每个文件可设多个时间段，
每段时间输出 `源名_<i>.<ext>`。
"""
from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from .. import state
from ..config import AppConfig
from ..ffmpeg_runner import parse_time_to_secs
from ..task import CANCELLED, RUNNING, SUCCESS, CutTask, TaskPool
from .compression import VIDEO_EXTS, human_size
from .timefield import TimeField, fmt_secs, parse_ts
from .widgets import (
    DropBox, HelpLabel, Segmented, _COLOR_OK, _COLOR_RUN, _COLOR_ERR,
    _COLOR_WAIT, form_label, page_head, section_title,
)

_PRESET_BY_SPEED = {"balanced": "medium", "fast": "fast", "ultrafast": "ultrafast"}
_DEFAULTS_CRF = {"balanced": 18, "fast": 20, "ultrafast": 23}


class CutRow(QWidget):
    """切割文件行：文件名 + 时间段汇总 + 编辑时间段 + 进度。"""

    edit_requested = Signal(object)    # self
    remove_requested = Signal(object)  # self

    def __init__(self, name: str, size_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.name_lbl = QLabel(name)
        self.name_lbl.setObjectName("TaskName")
        self.name_lbl.setToolTip(name)
        self.name_lbl.setMinimumWidth(150)
        top.addWidget(self.name_lbl, 1)
        self.size_lbl = QLabel(size_text)
        self.size_lbl.setObjectName("TaskMeta")
        top.addWidget(self.size_lbl, 0)
        self.edit_btn = QPushButton("时间段")
        self.edit_btn.setObjectName("Ghost")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setToolTip("设置这段的切割时间段（开始 - 结束）")
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self))
        top.addWidget(self.edit_btn, 0)
        lay.addLayout(top)

        self.info_lbl = QLabel("未设置时间段")
        self.info_lbl.setObjectName("TaskMeta")
        lay.addWidget(self.info_lbl)

        bot = QHBoxLayout()
        bot.setSpacing(10)
        self.bar = QProgressBar()
        self.bar.setObjectName("TaskBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        bot.addWidget(self.bar, 1)
        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setObjectName("TaskPct")
        self.pct_lbl.setFixedWidth(40)
        bot.addWidget(self.pct_lbl, 0)
        close = QToolButton()
        close.setText("×")
        close.setObjectName("TaskRemove")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(lambda: self.remove_requested.emit(self))
        bot.addWidget(close, 0)
        lay.addLayout(bot)

    def set_segments_text(self, text: str) -> None:
        self.info_lbl.setText(text)

    def set_progress(self, pct: int) -> None:
        self.bar.setValue(min(max(pct, 0), 100))
        self.pct_lbl.setText(f"{pct}%")
        self.pct_lbl.setStyleSheet("")

    def set_running(self) -> None:
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_RUN};font-weight:700;")

    def set_waiting(self) -> None:
        self.set_progress(0)
        self.pct_lbl.setText("等待中")
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_WAIT};")

    def set_done(self, ok: bool, text: str) -> None:
        self.bar.setValue(100 if ok else 0)
        color = _COLOR_OK if ok else _COLOR_ERR
        self.pct_lbl.setText(text)
        self.pct_lbl.setStyleSheet(f"color:{color};font-weight:700;")

    def set_cancelled(self) -> None:
        self.bar.setValue(0)
        self.pct_lbl.setText("已取消")
        self.pct_lbl.setStyleSheet(f"color:{_COLOR_WAIT};font-weight:700;")


class CutDialog(QDialog):
    """时间段编辑对话框：一个文件的多段 (开始-结束)。"""

    def __init__(self, parent, existing: list[list[str]]):
        super().__init__(parent)
        self.setWindowTitle("设置切割时间段")
        self.resize(720, 460)
        self._rows: list[tuple[TimeField, TimeField, QLabel]] = []
        self._build(existing)

    def _build(self, existing: list[list[str]]) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        tip = QLabel("每段「开始 - 结束」。可直接微调 时:分:秒；粘贴文本自动识别 "
                     "秒/MM:SS/HH:MM:SS 并拆分多段。每段输出为一个文件。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#8b93ab;font-size:12px;")
        lay.addWidget(tip)

        self.listarea = QScrollArea()
        self.listarea.setWidgetResizable(True)
        self.container = QWidget()
        self.clist = QVBoxLayout(self.container)
        self.clist.setContentsMargins(0, 0, 0, 0)
        self.clist.setSpacing(8)
        self.clist.addStretch(1)
        self.listarea.setWidget(self.container)
        lay.addWidget(self.listarea, 1)

        init = [(parse_ts(x[0]) or 0, parse_ts(x[1]) or 0)
                for x in (existing or [["00:00:00", "00:00:00"]])]
        for ss, es in init:
            self._add_row(ss, es)

        bar = QHBoxLayout()
        self.fmt_combo = QComboBox()
        for label, val in [("格式：自动识别", "auto"), ("秒", "s"),
                           ("MM:SS", "ms"), ("HH:MM:SS", "hms")]:
            self.fmt_combo.addItem(label, val)
        self.fmt_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn = QPushButton("📋 粘贴时间")
        self.paste_btn.setObjectName("Ghost")
        self.paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.clicked.connect(self._paste_clipboard)
        self._tot_lbl = QLabel("")
        self._tot_lbl.setStyleSheet("color:#8b93ab;font-size:12px;")
        add = QPushButton("+ 添加时间段")
        add.setObjectName("Ghost")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.setToolTip("新增一段，开始时间自动接上一段结束")
        add.clicked.connect(self._add_tail)
        bar.addWidget(self.fmt_combo)
        bar.addWidget(self.paste_btn)
        bar.addStretch(1)
        bar.addWidget(self._tot_lbl)
        bar.addWidget(add)
        lay.addLayout(bar)

        btns = QHBoxLayout()
        ok = QPushButton("确定")
        ok.setObjectName("Primary")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)
        self._refresh_totals()

    def _add_row(self, start_sec: int, end_sec: int) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        s = TimeField(); e = TimeField()
        s.set_secs(start_sec); e.set_secs(end_sec)
        s.setToolTip("开始时间：三栏微调或粘贴")
        e.setToolTip("结束时间：三栏微调或粘贴")
        dash = QLabel("—")
        dash.setStyleSheet("color:#8b93ab;")
        dur = QLabel("—")
        dur.setMinimumWidth(64)
        dur.setAlignment(Qt.AlignmentFlag.AlignRight)
        dur.setStyleSheet(
            "color:#8b93ab;font-size:12px;font-variant-numeric:tabular-nums;")
        chain = QPushButton("接上段")
        chain.setObjectName("Ghost")
        chain.setCursor(Qt.CursorShape.PointingHandCursor)
        chain.setToolTip("把开始时间设为上一段结束，实现连续切割")
        delbtn = QPushButton("删除")
        delbtn.setObjectName("Ghost")
        delbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        h.addWidget(s, 1)
        h.addWidget(dash, 0)
        h.addWidget(e, 1)
        h.addWidget(dur, 0)
        h.addWidget(chain, 0)
        h.addWidget(delbtn, 0)
        self.clist.insertWidget(self.clist.count() - 1, row)
        self._rows.append((s, e, dur))
        s.valueChanged.connect(self._refresh_totals)
        e.valueChanged.connect(self._refresh_totals)
        chain.clicked.connect(
            lambda: (s.set_secs(self._prev_end(row)), self._refresh_totals()))
        delbtn.clicked.connect(lambda: self._del_row(row))

    def _prev_end(self, row: QWidget) -> int:
        idx = next(i for i, r in enumerate(self._rows)
                   if r[0].parentWidget() is row)
        return self._rows[idx - 1][1].secs() if idx > 0 else 0

    def _del_row(self, row: QWidget) -> None:
        self._rows.remove(
            next(r for r in self._rows if r[0].parentWidget() is row))
        row.setParent(None)
        row.deleteLater()
        self._refresh_totals()

    def _add_tail(self) -> None:
        prev = self._rows[-1][1].secs() if self._rows else 0
        self._add_row(prev, prev)
        self._refresh_totals()

    def _refresh_totals(self) -> None:
        total = 0
        n = 0
        valid = True
        for s, e, dur in self._rows:
            ss, es = s.secs(), e.secs()
            if es <= ss:
                dur.setText("时长无效")
                dur.setStyleSheet(
                    "color:#d1495b;font-size:12px;font-weight:600;")
                valid = False
                continue
            dur.setText(fmt_secs(es - ss))
            dur.setStyleSheet(
                "color:#8b93ab;font-size:12px;"
                "font-variant-numeric:tabular-nums;")
            total += es - ss
            n += 1
        if self._rows and valid:
            self._tot_lbl.setText(f"{n} 段 · 总时长 {fmt_secs(total)}")
        elif self._rows:
            self._tot_lbl.setText("存在无效时间段")
        else:
            self._tot_lbl.setText("")

    def _parse_paste(self, text: str, fmt: str) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            a, b = None, None
            parts = [x.strip() for x in re.split(r"[-–—～~]", line)]
            if len(parts) == 2:
                a, b = parse_ts(parts[0], fmt), parse_ts(parts[1], fmt)
            else:
                cells = [x for x in re.split(r"[\s,，]+", line) if x]
                if len(cells) == 2:
                    a, b = parse_ts(cells[0], fmt), parse_ts(cells[1], fmt)
            if a is not None and b is not None and b > a:
                pairs.append((a, b))
        return pairs

    def _paste_clipboard(self) -> None:
        text = (QApplication.clipboard().text() or "").strip()
        if not text:
            return
        fmt = self.fmt_combo.currentData()
        segs = self._parse_paste(text, fmt)
        if not segs:
            QMessageBox.information(self, "无法识别",
                                    f"未能从剪贴板解析出时间区间：\n{text}")
            return
        if (len(self._rows) == 1 and self._rows[0][0].secs() == 0
                and self._rows[0][1].secs() == 0):
            self._del_row(self._rows[0][0].parentWidget())
        for a, b in segs:
            self._add_row(a, b)
        self._refresh_totals()

    def _accept(self) -> None:
        segs: list[list[str]] = []
        for s, e, _dur in self._rows:
            ss, es = s.secs(), e.secs()
            if es <= ss:
                QMessageBox.warning(
                    self, "时间段无效",
                    f"「{fmt_secs(ss)} - {fmt_secs(es)}」结束必须晚于开始。")
                return
            segs.append([fmt_secs(ss), fmt_secs(es)])
        self._result = segs
        self.accept()

    def result_segments(self) -> list[list[str]]:
        return getattr(self, "_result", [])


class CutPage(QWidget):
    task_count_changed = Signal(int, int, int)  # running, done, failed

    def __init__(self, pool: TaskPool, parent=None):
        super().__init__(parent)
        self._pool = pool
        self._tasks: dict[str, CutTask] = {}
        self._rows: dict[str, CutRow] = {}
        self._segments: dict[str, list[list[str]]] = {}
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
        head.addLayout(page_head("视频切割", "按时间段切割，快速流复制 / 精确重编码"))
        head.addStretch(1)
        blay.addLayout(head)

        self.dropbox = DropBox("把多个视频拖到这里，或点击添加",
                               "支持批量 · 每个文件可设置多段时间段")
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

        rt = section_title("切割参数")
        blay.addLayout(rt)

        card = QFrame()
        card.setObjectName("SettingCard")
        form = QFormLayout(card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        f_mode = QHBoxLayout()
        f_mode.setSpacing(6)
        self.mode = QComboBox()
        self.mode.addItem("快速流复制（速度快）", "copy")
        self.mode.addItem("精确重编码（默认）", "reencode")
        self.mode.setCurrentIndex(1)  # 与标签「默认」一致
        self.mode.currentIndexChanged.connect(self._on_mode_changed)
        f_mode.addWidget(self.mode)
        f_mode.addStretch(1)
        form.addRow(form_label("切割方式"), f_mode)

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
        self.crf.setValue(int(AppConfig.instance().get_cut("crf") or 20))
        f_crf.addWidget(self.crf)
        f_crf.addWidget(HelpLabel("数值越低越清晰、文件越大。仅重编码时生效。"))
        f_crf.addStretch(1)
        form.addRow(form_label("CRF（画质）"), f_crf)

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
        self._on_mode_changed()  # 初始同步 speed/crf 可用态（须在全部参数控件创建后）
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
        self.start_btn = QPushButton("开始切割")
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

    # ---- env / 参数联动 ----
    def _on_env_change(self) -> None:
        self._env = state.state.env

    def _on_mode_changed(self) -> None:
        reenc = self.mode.currentData() == "reencode"
        self.speed.setEnabled(reenc)
        self.crf.setEnabled(reenc)

    def _on_speed_changed(self, *_args) -> None:
        self.crf.setValue(_DEFAULTS_CRF.get(self.speed.currentData(), 20))

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

    # ---- 文件列表 / 拖拽 ----
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
            row = CutRow(p.name, human_size(p.stat().st_size))
            row.edit_requested.connect(lambda r, s=key: self._edit_segments(s))
            row.remove_requested.connect(lambda r, s=key: self._remove_row(s))
            self.listlay.insertWidget(self.listlay.count() - 1, row)
            self._rows[key] = row
            self._tasks[key] = None
            self._segments[key] = []
            self._refresh_summary()

    def _remove_row(self, key: str) -> None:
        task = self._tasks.get(key)
        if task is not None and task.status is RUNNING:
            task.request_stop()
        self._tasks.pop(key, None)
        self._segments.pop(key, None)
        row = self._rows.pop(key, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._refresh_summary()

    def _edit_segments(self, key: str) -> None:
        task = self._tasks.get(key)
        if task is not None and task.status is RUNNING:
            QMessageBox.information(self, "提示", "正在切割中，请先停止。")
            return
        dlg = CutDialog(self, self._segments.get(key, []))
        if dlg.exec():
            segs = dlg.result_segments()
            self._segments[key] = segs
            row = self._rows.get(key)
            if row:
                row.set_segments_text(f"{len(segs)} 段 · " + " / ".join(
                    f"{s}~{e}" for s, e in segs))
            self._refresh_summary()

    # ---- 运行 ----
    def _start(self) -> None:
        pending = [k for k, t in self._tasks.items() if t is None]
        without = [k for k in pending if not self._segments.get(k)]
        if not pending:
            QMessageBox.information(self, "提示", "请先添加要切割的视频。")
            return
        to_run = [k for k in pending if k not in without]
        if not to_run:
            QMessageBox.warning(self, "缺少时间段",
                                "请先为视频「设置时间段」（至少一个 开始-结束）。")
            return

        cfg = AppConfig.instance()
        mode = self.mode.currentData()
        enc = self._env.encoder if self._env else "libx264"
        params = {
            "mode": mode,
            "encoder": enc,
            "crf": self.crf.value(),
            "preset": _PRESET_BY_SPEED[self.speed.currentData()],
        }
        cfg.set_cut("mode", mode)
        cfg.set_cut("crf", self.crf.value())
        cfg.set_cut("preset", params["preset"])
        cfg.set("output_dir_mode", self.od_mode.currentData())
        if self.od_mode.currentData() == "custom":
            cfg.set("output_dir_custom", self.od_custom.text())

        for k in to_run:
            task = CutTask(k, [list(s) for s in self._segments[k]], dict(params))
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

    def _on_finished(self, task: CutTask) -> None:
        row = self._rows.get(task.input_path)
        if row is None:
            return
        if task.status is SUCCESS:
            row.set_done(True, "完成")
            row.set_segments_text(f"已输出 {len(task.outputs)} 个文件")
            self._done += 1
        elif task.status is CANCELLED:
            row.set_cancelled()
            self._cancelled += 1
        else:
            row.set_done(False, "失败")
            row.setToolTip(task.message)
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