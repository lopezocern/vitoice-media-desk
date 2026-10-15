"""视频压缩页面：拖拽/选择文件 -> 设置参数 -> 批量入队压缩，实时进度。

对应 PRD：视频压缩 P1。UI 以卡片式布局，参数带 ? 帮助与状态。
"""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSlider,
    QSpinBox, QVBoxLayout, QWidget,
)

from .. import env as appenv, state
from ..config import AppConfig
from ..task import CANCELLED, RUNNING, SUCCESS, CompressionTask, TaskPool
from .widgets import (
    DropBox, HelpLabel, OutputDirRow, Segmented, TaskRow, form_label,
    page_head, section_title,
)

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".ts", ".m4v", ".flv"}
_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]

# 四档位（从慢到快）：CRF 16 → 20 → 23 → 28，画质/体积递减、编码速度递增。
# ratio 为输出体积相对原文件的典型区间（启发式经验值，依内容复杂度浮动）。
_CRF_DEFAULTS = {"best": 16, "high": 20, "standard": 23, "fast": 28}
_BR_DEFAULTS = {"best": 8.0, "high": 6.0, "standard": 4.5, "fast": 3.0}
_SPEED_META = {
    "best": {
        "name": "极致画质",
        "tagline": "最高保真 · 压缩幅度温和，体积偏大、耗时最长",
        "ratio": (0.30, 0.55),
        "sw": "软编约 0.3–0.8 倍实时",
        "hw": "硬编约 5–12 倍实时",
    },
    "high": {
        "name": "高画质",
        "tagline": "高保真重编码 · 体积明显小于原片",
        "ratio": (0.22, 0.45),
        "sw": "软编约 0.6–1.5 倍实时",
        "hw": "硬编约 6–15 倍实时",
    },
    "standard": {
        "name": "均衡",
        "tagline": "推荐默认 · 速度与体积兼顾，多数场景的最优解",
        "ratio": (0.18, 0.38),
        "sw": "软编约 1–3 倍实时",
        "hw": "硬编约 8–20 倍实时",
    },
    "fast": {
        "name": "快速",
        "tagline": "速度优先 · 编码最快、体积最小，画质有可感损失",
        "ratio": (0.12, 0.30),
        "sw": "软编约 4–8 倍实时",
        "hw": "硬编约 15–40 倍实时",
    },
}

# 分辨率降档时，预估体积/有效码率按像素比例近似下调
_RES_FACTOR = {"keep": 1.0, "1920x1080": 1.0, "1280x720": 0.62,
               "854x480": 0.42, "640x360": 0.30, "custom": 0.55}


def _crf_tag(v: int) -> str:
    """CRF 值的画质语义标签（滑杆旁）。"""
    if v <= 16:
        return "极高画质"
    if v <= 20:
        return "高画质"
    if v <= 26:
        return "中上画质"
    if v <= 30:
        return "中等画质"
    if v <= 34:
        return "体积优先"
    return "极致压缩"


def _fmt_duration(secs: float) -> str:
    """总时长友好显示（码率模式预估用）。"""
    s = int(secs)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h} 小时 {m} 分"
    if m:
        return f"{m} 分 {sec} 秒"
    return f"{sec} 秒"


def human_size(n: float) -> str:
    v = float(n)
    for u in _SIZE_UNITS:
        if v < 1024 or u == _SIZE_UNITS[-1]:
            return f"{v:.1f} {u}"
        v /= 1024


class CompressionPage(QWidget):
    started_all = Signal()
    task_count_changed = Signal(int, int, int)  # running, done, failed
    durations_ready = Signal()                  # 后台时长探测完成（跨线程排队回主线程）

    def __init__(self, pool: TaskPool, parent=None):
        super().__init__(parent)
        self._pool = pool
        self._tasks: dict[str, CompressionTask] = {}
        self._rows: dict[str, TaskRow] = {}
        self._done = self._failed = self._cancelled = 0
        self._env = None
        self._user_override_crf = False   # 手动拖过 CRF：切档位时保留并标「已自定义」
        self._user_override_br = False    # 手动拖过目标码率
        self._rate_mode = "crf"           # crf / bitrate
        self._durations: dict[str, float] = {}  # 文件路径 -> 时长（秒）
        self._probing = False

        self._build_ui()
        self._restore_config()   # 档位/CRF/码率/模式/分辨率 从配置恢复
        self._refresh_preset_info()  # env 未就绪时也先按默认档位展示说明
        self.durations_ready.connect(self._on_durations_ready)
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
        f_speed.setSpacing(8)
        self.speed = Segmented([
            ("极致画质", "best"),
            ("高画质", "high"),
            ("均衡", "standard"),
            ("快速", "fast"),
        ])
        self.speed.currentChanged.connect(self._on_speed_changed)
        f_speed.addWidget(self.speed)
        f_speed.addWidget(HelpLabel(
            "从慢到快：极致画质最保真、耗时最长；快速编码最快、体积最小。"
            "手动改过的参数会标「已自定义」，切档位时保留。"))
        self.custom_tag = QLabel("已自定义")
        self.custom_tag.setObjectName("CustomTag")
        self.custom_tag.setVisible(False)
        self.custom_tag.setToolTip(
            "当前模式的参数已手动修改：切换档位时保留不覆盖；点「恢复档位默认」可重新跟随档位。")
        f_speed.addWidget(self.custom_tag)
        f_speed.addStretch(1)
        form.addRow(form_label("压缩档位"), f_speed)

        # 档位说明卡：选中哪个档位，就展示该档位的取舍说明与预估体积/码率/速度
        self.preset_info = QFrame()
        self.preset_info.setObjectName("PresetInfo")
        ilay = QVBoxLayout(self.preset_info)
        ilay.setContentsMargins(12, 9, 12, 9)
        ilay.setSpacing(3)
        ihead = QHBoxLayout()
        ihead.setSpacing(8)
        self.pi_name = QLabel("")
        self.pi_name.setStyleSheet(
            "font-size:12.5px;font-weight:700;color:#1c2333;")
        self.pi_crf = QLabel("")
        self.pi_crf.setStyleSheet(
            "font-size:11px;font-weight:600;color:#4f5bd5;"
            "background:#eef0fe;border-radius:999px;padding:2px 10px;")
        ihead.addWidget(self.pi_name)
        ihead.addStretch(1)
        ihead.addWidget(self.pi_crf)
        ilay.addLayout(ihead)
        self.pi_detail = QLabel("")
        self.pi_detail.setStyleSheet("color:#5c6478;font-size:11.5px;")
        self.pi_detail.setWordWrap(True)
        ilay.addWidget(self.pi_detail)
        form.addRow(self.preset_info)

        # 码率控制：CRF（恒定画质）⇄ 目标码率（Mbps）双模式
        f_rate = QHBoxLayout()
        f_rate.setSpacing(8)
        self.rate_mode_seg = Segmented([
            ("CRF（恒定画质）", "crf"),
            ("目标码率", "bitrate"),
        ])
        self.rate_mode_seg.currentChanged.connect(self._on_rate_mode_changed)
        f_rate.addWidget(self.rate_mode_seg)
        f_rate.addWidget(HelpLabel(
            "CRF：给定期望画质，码率随画面复杂度自动浮动；"
            "目标码率：直接指定 Mbps，体积按「码率×时长」精确预估。"))
        f_rate.addStretch(1)
        form.addRow(form_label("码率控制"), f_rate)

        self.mode_zone = QFrame()
        self.mode_zone.setObjectName("ModeZone")
        mz = QHBoxLayout(self.mode_zone)
        mz.setContentsMargins(10, 8, 10, 8)
        mz.setSpacing(10)

        # CRF 模式控件：滑杆 0-51 + 数值 pill + 语义标签 + 恢复档位默认
        self.crf_zone = QWidget()
        cz = QHBoxLayout(self.crf_zone)
        cz.setContentsMargins(0, 0, 0, 0)
        cz.setSpacing(10)
        crf_name = QLabel("CRF")
        crf_name.setObjectName("ZoneName")
        cz.addWidget(crf_name)
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setObjectName("ParamSlider")
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(23)
        self.crf_slider.valueChanged.connect(self._on_crf_changed)
        cz.addWidget(self.crf_slider, 1)
        self.crf_val = QLabel("23")
        self.crf_val.setObjectName("RangeVal")
        cz.addWidget(self.crf_val)
        self.crf_tag = QLabel("中上画质")
        self.crf_tag.setObjectName("RangeTag")
        cz.addWidget(self.crf_tag)
        self.crf_reset = QPushButton("恢复档位默认")
        self.crf_reset.setObjectName("MiniBtn")
        self.crf_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crf_reset.setToolTip("CRF 回到当前档位的默认值，并重新跟随档位联动。")
        self.crf_reset.clicked.connect(self._on_crf_reset)
        cz.addWidget(self.crf_reset)
        mz.addWidget(self.crf_zone, 1)

        # 目标码率模式控件：滑杆 0.5-20 Mbps（内部 ×10）+ 数值 + 恢复档位默认
        self.br_zone = QWidget()
        bz = QHBoxLayout(self.br_zone)
        bz.setContentsMargins(0, 0, 0, 0)
        bz.setSpacing(10)
        br_name = QLabel("目标码率")
        br_name.setObjectName("ZoneName")
        bz.addWidget(br_name)
        self.br_slider = QSlider(Qt.Orientation.Horizontal)
        self.br_slider.setObjectName("ParamSlider")
        self.br_slider.setRange(5, 200)
        self.br_slider.setValue(45)
        self.br_slider.valueChanged.connect(self._on_br_changed)
        bz.addWidget(self.br_slider, 1)
        self.br_val = QLabel("4.5")
        self.br_val.setObjectName("RangeVal")
        bz.addWidget(self.br_val)
        br_unit = QLabel("Mbps")
        br_unit.setObjectName("RangeTag")
        bz.addWidget(br_unit)
        self.br_reset = QPushButton("恢复档位默认")
        self.br_reset.setObjectName("MiniBtn")
        self.br_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.br_reset.setToolTip("目标码率回到当前档位的建议值，并重新跟随档位联动。")
        self.br_reset.clicked.connect(self._on_br_reset)
        bz.addWidget(self.br_reset)
        bz.addWidget(HelpLabel("预估体积 = 码率 × 总时长 ÷ 8"))
        self.br_zone.setVisible(False)
        mz.addWidget(self.br_zone, 1)
        form.addRow(self.mode_zone)

        # 分辨率：从高级参数上移，预设与转换页对齐
        f_res = QHBoxLayout()
        f_res.setSpacing(6)
        self.res = QComboBox()
        self.res.addItem("保持原尺寸", "keep")
        self.res.addItem("1920 × 1080（1080p）", "1920x1080")
        self.res.addItem("1280 × 720（720p）", "1280x720")
        self.res.addItem("854 × 480（480p）", "854x480")
        self.res.addItem("640 × 360（360p）", "640x360")
        self.res.addItem("自定义宽 × 高", "custom")
        self.res.currentIndexChanged.connect(self._on_res_changed)
        f_res.addWidget(self.res)
        self.res_w = QSpinBox(); self.res_w.setRange(2, 7680); self.res_w.setValue(1920)
        self.res_h = QSpinBox(); self.res_h.setRange(2, 4320); self.res_h.setValue(1080)
        self.res_w.setVisible(False); self.res_h.setVisible(False)
        f_res.addWidget(self.res_w)
        f_res.addWidget(form_label("×"))
        f_res.addWidget(self.res_h)
        f_res.addWidget(HelpLabel("降档分辨率时，说明卡预估按像素比例同步下调。"))
        f_res.addStretch(1)
        form.addRow(form_label("分辨率"), f_res)

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
        self.od = OutputDirRow()
        f_od.addWidget(self.od)
        form.addRow(form_label("输出目录"), f_od)

        self.adv = QPushButton("展开高级参数（帧率 / 并发 / 命名）")
        self.adv.setObjectName("Expander")
        self.adv.setCheckable(True)
        self.adv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv.setToolTip("显示 / 隐藏高级参数")
        self.adv.toggled.connect(self._on_adv_toggled)
        form.addRow(self.adv)
        blay.addWidget(card)

        # 高级参数（折叠卡片）：CRF / 分辨率已上移基础区，仅留低频项
        self.adv_card = QFrame()
        self.adv_card.setObjectName("SettingCard")
        self.adv_card.setVisible(False)
        al = QFormLayout(self.adv_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.setHorizontalSpacing(12)
        al.setVerticalSpacing(10)

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
        self._refresh_preset_info()
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
        # 与设置页/转换页同一机制：落库 + env_changed 广播（单源 helper），各页即时联动
        state.set_gpu_enabled(on)
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
            ("收起高级参数（帧率 / 并发 / 命名）  ▴"
             if on else
             "展开高级参数（帧率 / 并发 / 命名）  ▾"))

    # ---------------- 档位联动（档位 = 预设包） ----------------
    def _on_speed_changed(self) -> None:
        """切换档位：未手动覆盖的 CRF / 码率跟随档位，已覆盖的保留并标「已自定义」。"""
        key = self.speed.currentData()
        if not self._user_override_crf:
            # 程序化联动不算“用户手动改”：屏蔽信号避免误置 override 锁死联动
            self.crf_slider.blockSignals(True)
            self.crf_slider.setValue(_CRF_DEFAULTS.get(key, 23))
            self.crf_slider.blockSignals(False)
            self._sync_crf_labels()
        if not self._user_override_br:
            self.br_slider.blockSignals(True)
            self.br_slider.setValue(round(_BR_DEFAULTS.get(key, 4.5) * 10))
            self.br_slider.blockSignals(False)
            self._sync_br_labels()
        self._refresh_preset_info()

    # ---- CRF / 码率滑杆 ----
    def _on_crf_changed(self, _: int) -> None:
        self._user_override_crf = True
        self._sync_crf_labels()
        self._refresh_preset_info()

    def _on_crf_reset(self) -> None:
        self._user_override_crf = False
        self.crf_slider.blockSignals(True)
        self.crf_slider.setValue(_CRF_DEFAULTS.get(self.speed.currentData(), 23))
        self.crf_slider.blockSignals(False)
        self._sync_crf_labels()
        self._refresh_preset_info()

    def _on_br_changed(self, _: int) -> None:
        self._user_override_br = True
        self._sync_br_labels()
        self._refresh_preset_info()

    def _on_br_reset(self) -> None:
        self._user_override_br = False
        self.br_slider.blockSignals(True)
        self.br_slider.setValue(round(_BR_DEFAULTS.get(self.speed.currentData(), 4.5) * 10))
        self.br_slider.blockSignals(False)
        self._sync_br_labels()
        self._refresh_preset_info()

    def _sync_crf_labels(self) -> None:
        v = self.crf_slider.value()
        self.crf_val.setText(str(v))
        self.crf_tag.setText(_crf_tag(v))

    def _sync_br_labels(self) -> None:
        self.br_val.setText(f"{self.br_slider.value() / 10:.1f}")

    def _on_rate_mode_changed(self) -> None:
        self._rate_mode = self.rate_mode_seg.currentData() or "crf"
        crf_mode = self._rate_mode == "crf"
        self.crf_zone.setVisible(crf_mode)
        self.br_zone.setVisible(not crf_mode)
        self._refresh_preset_info()

    # ---------------- 配置恢复 ----------------
    def _restore_config(self) -> None:
        """启动时恢复上次的档位/CRF/码率/模式/分辨率（含旧版三档迁移值）。"""
        cfg = AppConfig.instance()
        sm = cfg.get_compress("speed_mode") or "standard"
        if sm not in _SPEED_META:
            sm = "standard"
        self.speed.setCurrentData(sm)  # emit → CRF/码率联动到该档位默认值

        crf_saved = cfg.get_compress("crf")
        crf_v = int(crf_saved) if crf_saved not in (None, "") else _CRF_DEFAULTS[sm]
        if crf_v != _CRF_DEFAULTS[sm]:
            self._user_override_crf = True
            self.crf_slider.blockSignals(True)
            self.crf_slider.setValue(crf_v)
            self.crf_slider.blockSignals(False)
            self._sync_crf_labels()

        br_saved = cfg.get_compress("bitrate")
        br_v = float(br_saved) if br_saved else _BR_DEFAULTS[sm]
        if abs(br_v - _BR_DEFAULTS[sm]) > 0.01:
            self._user_override_br = True
            self.br_slider.blockSignals(True)
            self.br_slider.setValue(round(br_v * 10))
            self.br_slider.blockSignals(False)
            self._sync_br_labels()

        self._rate_mode = "bitrate" if cfg.get_compress("rate_mode") == "bitrate" else "crf"
        self.rate_mode_seg.setCurrentData(self._rate_mode)  # emit → 切换 zone + 刷新说明卡

        res_saved = cfg.get_compress("resolution") or "keep"
        res_saved = {"1080": "1920x1080", "720": "1280x720"}.get(res_saved, res_saved)
        idx = self.res.findData(res_saved)
        self.res.setCurrentIndex(idx if idx >= 0 else 0)  # emit → _on_res_changed
        if res_saved == "custom":
            self.res_w.setValue(int(cfg.get_compress("resolution_w") or 1920))
            self.res_h.setValue(int(cfg.get_compress("resolution_h") or 1080))

    # ---------------- 说明卡（全联动） ----------------
    def _refresh_preset_info(self) -> None:
        """档位/CRF/码率/模式/分辨率/文件列表/GPU 任一变化时，更新说明卡预估。"""
        key = self.speed.currentData()
        m = _SPEED_META.get(key, _SPEED_META["standard"])
        envst = state.state.env
        hw = self.gpu.isChecked() and envst is not None and bool(envst.gpu_encoders)
        speed_txt = m["hw"] if hw else m["sw"]
        f = _RES_FACTOR.get(self.res.currentData(), 1.0)
        try:
            total = sum(Path(k).stat().st_size for k in self._tasks)
        except OSError:
            total = 0

        if self._rate_mode == "crf":
            # CRF 联动预估：以档位默认 CRF 为基准，
            # 每调低 6 体积约 ×2、调高 6 约 ×0.5（x264 经验值）
            crf = self.crf_slider.value()
            k = 2 ** ((_CRF_DEFAULTS.get(key, 23) - crf) / 6)
            lo, hi = m["ratio"][0] * f * k, m["ratio"][1] * f * k
            if total > 0:
                size = (f"本批 {len(self._tasks)} 个文件共 {human_size(total)}"
                        f" → 预计约 {human_size(total * lo)}–{human_size(total * hi)}")
            else:
                size = f"预估体积约为原文件的 {round(lo * 100)}%–{round(hi * 100)}%"
            self.pi_crf.setText(f"CRF {crf} · 恒定画质/可变码率")
            detail = f"{size} · {speed_txt} · 实际结果依画面复杂度浮动"
        else:
            # 目标码率模式：预估体积 = 码率 × 总时长 ÷ 8，精确可预估
            mbps = self.br_slider.value() / 10 * f
            total_dur = sum(self._durations.get(k, 0.0) for k in self._tasks)
            if total > 0 and total_dur > 0:
                est_bytes = mbps * total_dur / 8 * 1024 * 1024
                size = (f"本批 {len(self._tasks)} 个 · 约 {_fmt_duration(total_dur)}"
                        f" × {mbps:.1f} Mbps → 精确约 {human_size(est_bytes)}")
            elif total > 0:
                size = f"正在读取本批总时长，稍候按 {mbps:.1f} Mbps 精确预估…"
            else:
                size = f"体积 = {mbps:.1f} Mbps × 总时长 ÷ 8，可精确预估"
            self.pi_crf.setText(f"目标 {mbps:.1f} Mbps · 恒定码率")
            detail = f"{size} · {speed_txt}"

        self.pi_name.setText(f"{m['name']} — {m['tagline']}")
        self.pi_detail.setText(detail)
        overridden = (self._user_override_crf if self._rate_mode == "crf"
                      else self._user_override_br)
        self.custom_tag.setVisible(overridden)

    def _on_res_changed(self) -> None:
        show = self.res.currentData() == "custom"
        self.res_w.setVisible(show); self.res_h.setVisible(show)
        self._refresh_preset_info()

    # ---------------- 时长探测（码率模式的预估需要总时长） ----------------
    def _schedule_probe(self) -> None:
        """后台线程 ffprobe 本批未探测文件的时长，完成后经信号回主线程刷新。"""
        todo = [k for k in self._tasks if k not in self._durations]
        if not todo or self._probing:
            return
        self._probing = True

        def worker() -> None:
            try:
                for k in todo:
                    if k not in self._tasks:  # 探测期间已被移除
                        continue
                    ms = appenv.probe_duration_ms(Path(k))
                    self._durations[k] = (ms or 0) / 1000
            finally:
                self._probing = False
                self.durations_ready.emit()  # 跨线程自动排队到主线程

        threading.Thread(target=worker, daemon=True).start()

    def _on_durations_ready(self) -> None:
        self._refresh_preset_info()

    def _on_fps_changed(self) -> None:
        self.fps_v.setVisible(self.fps.currentData() == "custom")

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
        self._schedule_probe()
        self._refresh_preset_info()

    def _remove_row(self, src: Path) -> None:
        k = str(src)
        task = self._tasks.get(k)
        if task and task.status == RUNNING:
            task.request_stop()
        self._tasks.pop(k, None)
        row = self._rows.pop(k, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._refresh_summary()
        self._refresh_preset_info()

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
            "crf": self.crf_slider.value(),
            "rate_mode": self._rate_mode,
            "bitrate": self.br_slider.value() / 10,
            "preset": cfg.preset(),
            "resolution": self.res.currentData(),
            "resolution_w": self.res_w.value() if custom_res else None,
            "resolution_h": self.res_h.value() if custom_res else None,
            "fps": self.fps.currentData(),
            "fps_value": self.fps_v.value(),
            "suffix": self.suffix_edit.text().strip() or "_compressed",
        }
        compress_vals = {
            "speed_mode": self.speed.currentData(),
            "crf": self.crf_slider.value(),
            "rate_mode": self._rate_mode,
            "bitrate": params["bitrate"],
            "resolution": self.res.currentData(),
            "fps": self.fps.currentData(),
            "concurrency": self.conc.value(),
            "suffix": params["suffix"],
        }
        if custom_res:
            compress_vals["resolution_w"] = self.res_w.value()
            compress_vals["resolution_h"] = self.res_h.value()
        cfg.update_section("compress", compress_vals)   # 批量一次落盘
        top_vals = {"output_dir_mode": self.od.mode_data()}
        if self.od.mode_data() == "custom":
            top_vals["output_dir_custom"] = self.od.custom_text()
        cfg.update(top_vals)

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
            if t is not None and t.status == RUNNING:
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
        if task.status == SUCCESS:
            ratio = task.size_ratio()
            row.set_done(True, f"{human_size(task.result_size)}（{ratio:.0%}）",
                         f"输出：{Path(task.output_path).name}")
            self._done += 1
        elif task.status == CANCELLED:
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
        running = sum(1 for t in self._tasks.values() if t and t.status == RUNNING)
        self.task_count_changed.emit(running, self._done, self._failed)

    def snapshot_counts(self) -> tuple[int, int, int]:
        running = sum(1 for t in self._tasks.values() if t and t.status == RUNNING)
        return running, self._done, self._failed