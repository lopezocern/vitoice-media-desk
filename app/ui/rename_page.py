"""文件整理页面（重写）：规则驱动批量重命名器。

左侧规则配置面板 + 右侧「原名称 → 转换后名称」双列实时预览。
支持 5 类操作（查找替换 / 组合命名模板 / 删除字符 / 转换 / 设置扩展名），
内置拼音前缀预设与垃圾文件清理动作。全程干跑预览、确认后落地。
引擎见 `app/renamer.py`（纯 Python，可独立测试）。
"""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ..renamer import (
    TRANSFORM_LABELS, Operation, Rule, apply_plans, apply_rule, load_items,
    plan_cleanup, rule_to_plans,
)
from .widgets import HelpLabel

_COLOR_OLD = "#9aa3bd"
_COLOR_NEW = "#1c2333"
_COLOR_ERR = "#d1495b"
_COLOR_OK = "#2f9e54"


class _VarButton(QPushButton):
    """模板变量的快速插入按钮，点击即把关键字文本追加进模板。"""

    def __init__(self, text: str, value: str, target: QLineEdit):
        super().__init__(text)
        self._value = value
        self._target = target
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("Ghost")
        self.clicked.connect(self._insert)

    def _insert(self) -> None:
        cur = self._target
        cur.insert(self._value)
        cur.setFocus()


class _DateTimeDialog(QDialog):
    """复刻截图：选时间源（创建时间 / 修改时间）+ 模板格式，一键插入变量。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("日期时间")
        self.selected = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        hint = QLabel("选择时间源与格式，插入到名称模板")
        hint.setStyleSheet("color:#8b93ab;font-size:12px;")
        lay.addWidget(hint)
        fmts = ["yyyyMMdd", "yyyy-MM-dd", "yyyy-MM-dd_HH-mm-ss"]
        for src, name in (("create_time", "创建时间"), ("modify_time", "修改时间")):
            row = QHBoxLayout()
            row.setSpacing(6)
            tag = QLabel(name)
            tag.setMinimumWidth(64)
            row.addWidget(tag)
            for f in fmts:
                b = QPushButton(f)
                b.setObjectName("Ghost")
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.clicked.connect(
                    lambda _=False, s=src, ff=f: self._choose(s, ff))
                row.addWidget(b, 1)
            lay.addLayout(row)
        gap = QHBoxLayout()
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        gap.addStretch(1)
        gap.addWidget(cancel)
        lay.addLayout(gap)

    def _choose(self, src: str, fmt: str) -> None:
        self.selected = f"${{{src}:{fmt}}}"
        self.accept()


class RenamePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._rows = []            # [Row] 预览行（老化复用，只更新文本）
        self._rule_hint = QLabel()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(120)
        self._refresh_timer.timeout.connect(self._render)
        self._build_ui()
        self._build_config_ui()
        self._apply_hint("选择目标目录并点击扫描，然后配置规则查看预览。")

    # ------------------------------------------------------------------
    # 界面骨架
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 12)
        outer.setSpacing(10)

        outer.addWidget(QLabel("文件整理"))
        meta = QLabel("规则驱动批量重命名：操作类型 + 实时预览，确认后落地。")
        meta.setObjectName("TaskMeta")
        outer.addWidget(meta)

        # 目标目录行
        src = QHBoxLayout()
        src.addWidget(QLabel("目标目录"))
        self.src_input = QLineEdit()
        self.src_input.setPlaceholderText("选择要整理的文件夹…")
        self.scan_btn = QPushButton("扫描")
        self.scan_btn.setObjectName("Ghost")
        self.scan_btn.clicked.connect(self._scan)
        self.pick_btn = QPushButton("浏览…")
        self.pick_btn.setObjectName("Ghost")
        self.pick_btn.clicked.connect(self._pick_dir)
        src.addWidget(self.src_input, 1)
        src.addWidget(self.scan_btn)
        src.addWidget(self.pick_btn)
        outer.addLayout(src)

        # 左右两栏主体
        body = QHBoxLayout()
        body.setSpacing(14)

        # --- 左：规则配置 ---
        left = QFrame()
        left.setObjectName("Card")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(14, 12, 14, 12)
        lv.setSpacing(10)
        op_t = QLabel("操作类型")
        op_t.setObjectName("SectionLabel")
        lv.addWidget(op_t)
        self.op_combo = QComboBox()
        for label, op in [("查找替换", Operation.FIND_REPLACE),
                          ("组合命名模板", Operation.TEMPLATE),
                          ("删除字符", Operation.DELETE_CHARS),
                          ("转换", Operation.TRANSFORM),
                          ("设置扩展名", Operation.SET_EXT)]:
            self.op_combo.addItem(label, op)
        self.op_combo.currentIndexChanged.connect(
            lambda op_idx: (self._config_stack.setCurrentIndex(op_idx),
                            self._sync_keep_ext_visible(), self._schedule_refresh()))
        lv.addWidget(self.op_combo)

        self._config_stack = QStackedWidget()
        lv.addWidget(self._config_stack)

        self.keep_ext = QCheckBox("保留扩展名")
        self.keep_ext.setChecked(True)
        self.keep_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keep_ext.toggled.connect(self._schedule_refresh)
        lv.addWidget(self.keep_ext)

        self._rule_hint.setObjectName("Summary")
        self._rule_hint.setWordWrap(True)
        lv.addWidget(self._rule_hint)

        lv.addSpacing(2)
        self.clean_btn = QPushButton("清理垃圾文件…")
        self.clean_btn.setObjectName("Ghost")
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.clicked.connect(self._clean)
        lv.addWidget(self.clean_btn)
        lv.addStretch(1)
        # 左栏固定到适度宽度，把更多空间留给右侧预览表（文件整理核心在核对结果）
        left.setMaximumWidth(360)
        body.addWidget(left, 0)

        # --- 右：文件预览表 ---
        right = QVBoxLayout()
        right.setSpacing(8)
        # 表头
        head = QHBoxLayout()
        h_old = QLabel("原名称")
        h_old.setObjectName("SectionLabel")
        h_new = QLabel("转换后名称")
        h_new.setObjectName("SectionLabel")
        self.count_label = QLabel("共 0 项")
        self.count_label.setObjectName("Summary")
        head.addWidget(h_old, 1)
        head.addSpacing(34)
        head.addWidget(h_new, 1)
        head.addStretch(1)
        head.addWidget(self.count_label)
        right.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("TaskList")
        self.container = QWidget()
        self.list_lay = QVBoxLayout(self.container)
        self.list_lay.setContentsMargins(6, 6, 6, 6)
        self.list_lay.setSpacing(0)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.container)
        right.addWidget(self.scroll, 1)

        actions = QHBoxLayout()
        self.reset_btn = QPushButton("重置规则")
        self.reset_btn.setObjectName("Ghost")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset)
        self.apply_btn = QPushButton("应用更改")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.clicked.connect(self._apply)
        actions.addWidget(self.reset_btn)
        actions.addStretch(1)
        actions.addWidget(self.apply_btn)
        right.addLayout(actions)

        body.addLayout(right, 1)
        outer.addLayout(body, 1)

    # ------------------------------------------------------------------
    # 各类操作的参数区
    # ------------------------------------------------------------------
    def _build_config_ui(self) -> None:
        pages = {
            Operation.FIND_REPLACE: self._cfg_find_replace(),
            Operation.TEMPLATE: self._cfg_template(),
            Operation.DELETE_CHARS: self._cfg_delete(),
            Operation.TRANSFORM: self._cfg_transform(),
            Operation.SET_EXT: self._cfg_setext(),
        }
        for op in [Operation.FIND_REPLACE, Operation.TEMPLATE,
                   Operation.DELETE_CHARS, Operation.TRANSFORM,
                   Operation.SET_EXT]:
            self._config_stack.addWidget(pages[op])
        # 默认模板操作
        idx = self._config_stack.count() and 1 or 0
        self.op_combo.setCurrentIndex(idx)

    def _cfg_box(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(8)
        return lay

    def _cfg_find_replace(self) -> QWidget:
        w = QWidget()
        lay = self._cfg_box()
        lay.addWidget(QLabel("查找"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("要查找的文本或正则")
        self.find_input.textChanged.connect(self._schedule_refresh)
        lay.addWidget(self.find_input)
        self.regex_chk = QCheckBox("使用正则表达式")
        self.ignore_chk = QCheckBox("忽略大小写")
        self.all_chk = QCheckBox("全部替换")
        self.all_chk.setChecked(True)
        for c in (self.regex_chk, self.ignore_chk, self.all_chk):
            c.setCursor(Qt.CursorShape.PointingHandCursor)
            c.toggled.connect(self._schedule_refresh)
            lay.addWidget(c)
        lay.addSpacing(4)
        lay.addWidget(QLabel("替换"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("替换为（留空 = 删除）")
        self.replace_input.textChanged.connect(self._schedule_refresh)
        lay.addWidget(self.replace_input)
        lay.addStretch(1)
        w.setLayout(lay)
        return w

    def _cfg_template(self) -> QWidget:
        w = QWidget()
        lay = self._cfg_box()
        hl = QHBoxLayout()
        hl.addWidget(QLabel("名称（不含扩展名）"))
        preset = QPushButton("拼音前缀")
        preset.setObjectName("Ghost")
        preset.setCursor(Qt.CursorShape.PointingHandCursor)
        preset.clicked.connect(lambda: self.template_input.setText("${pinyin_prefix}"))
        hl.addStretch(1)
        hl.addWidget(preset)
        lay.addLayout(hl)

        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("如 ${create_time:yyyy-MM-dd}_${seq:start=1;increment=1;padding=3}")
        self.template_input.textChanged.connect(self._schedule_refresh)
        lay.addWidget(self.template_input)
        lay.addWidget(HelpLabel("点下方按钮插入变量；普通文字可混写。"))

        grid = QHBoxLayout()
        grid.setSpacing(4)
        # val 为 None 表示占位按钮（依赖媒体库元数据，本轮暂无数据源）；
        # val == "__datetime__" 表示「日期时间」选择弹窗入口。
        vars_ = [("原名称", "${original}"), ("文件夹", "${folder}"),
                 ("标签名", None),
                 ("来源网站", None), ("日期时间", "__datetime__"), ("序列号", "${seq:start=1;increment=1;padding=3}"),
                 ("随机串", "${random:6}"), ("UUID", "${uuid}")]
        for i in range(0, len(vars_), 3):
            row = QHBoxLayout()
            row.setSpacing(4)
            for text, val in vars_[i:i + 3]:
                if val is None:
                    b = QPushButton(text)
                    b.setObjectName("Ghost")
                    b.setCursor(Qt.CursorShape.PointingHandCursor)
                    b.clicked.connect(
                        lambda _=False, t=text: QMessageBox.information(
                            self, "暂不支持",
                            f"「{t}」依赖媒体标签/来源元数据，当前暂无数据源。"))
                    row.addWidget(b)
                elif val == "__datetime__":
                    b = QPushButton(text)
                    b.setObjectName("Ghost")
                    b.setCursor(Qt.CursorShape.PointingHandCursor)
                    b.clicked.connect(self._open_datetime)
                    row.addWidget(b)
                else:
                    row.addWidget(_VarButton(text, val, self.template_input))
            grid.addLayout(row)
        lay.addLayout(grid)
        lay.addStretch(1)
        w.setLayout(lay)
        return w

    def _open_datetime(self) -> None:
        dlg = _DateTimeDialog(self)
        if dlg.exec() and dlg.selected:
            self.template_input.insert(dlg.selected)
            self.template_input.setFocus()

    def _cfg_delete(self) -> QWidget:
        w = QWidget()
        lay = self._cfg_box()
        policy = QHBoxLayout()
        self.from_end_radio = QRadioButton("从开头")
        self.from_begin_radio = QRadioButton("从末尾")
        self.from_begin_radio.setChecked(True)
        for r in (self.from_begin_radio, self.from_end_radio):
            r.setCursor(Qt.CursorShape.PointingHandCursor)
            r.toggled.connect(self._schedule_refresh)
            policy.addWidget(r)
        policy.addStretch(1)
        lay.addLayout(policy)

        row = QHBoxLayout()
        row.addWidget(QLabel("起始位置"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 10**6)
        self.start_spin.valueChanged.connect(self._schedule_refresh)
        row.addWidget(self.start_spin, 1)
        row.addWidget(QLabel("删除字符数"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 10**6)
        self.count_spin.setValue(1)
        self.count_spin.valueChanged.connect(self._schedule_refresh)
        row.addWidget(self.count_spin, 1)
        lay.addLayout(row)
        lay.addStretch(1)
        w.setLayout(lay)
        return w

    def _cfg_transform(self) -> QWidget:
        w = QWidget()
        lay = self._cfg_box()
        lay.addWidget(QLabel("转换规则"))
        self.transform_combo = QComboBox()
        for key, label in TRANSFORM_LABELS.items():
            self.transform_combo.addItem(label, key)
        self.transform_combo.currentIndexChanged.connect(self._schedule_refresh)
        lay.addWidget(self.transform_combo)
        lay.addWidget(HelpLabel("作用于主名称；保留扩展名时扩展名不受影响。"))
        lay.addStretch(1)
        w.setLayout(lay)
        return w

    def _cfg_setext(self) -> QWidget:
        w = QWidget()
        lay = self._cfg_box()
        lay.addWidget(QLabel("新扩展名"))
        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("如 .jpg / .mp4（不含点也可）")
        self.ext_input.textChanged.connect(self._schedule_refresh)
        lay.addWidget(self.ext_input)
        self.only_ext_chk = QCheckBox("只更改现有扩展名")
        self.only_ext_chk.setChecked(True)
        self.only_ext_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.only_ext_chk.toggled.connect(self._schedule_refresh)
        lay.addWidget(self.only_ext_chk)
        lay.addStretch(1)
        w.setLayout(lay)
        return w

    # ------------------------------------------------------------------
    # 规则读取
    # ------------------------------------------------------------------
    def _build_rule(self) -> Rule:
        op = self.op_combo.currentData()
        r = Rule(operation=op, keep_ext=self.keep_ext.isChecked())
        if op == Operation.FIND_REPLACE:
            r.find, r.replace = self.find_input.text(), self.replace_input.text()
            r.regex, r.ignore_case, r.replace_all = (
                self.regex_chk.isChecked(), self.ignore_chk.isChecked(),
                self.all_chk.isChecked())
        elif op == Operation.TEMPLATE:
            r.template = self.template_input.text()
        elif op == Operation.DELETE_CHARS:
            r.start, r.count = self.start_spin.value(), self.count_spin.value()
            r.from_end = self.from_end_radio.isChecked()
        elif op == Operation.TRANSFORM:
            r.transform = self.transform_combo.currentData()
        elif op == Operation.SET_EXT:
            r.ext = self.ext_input.text()
            r.only_existing = self.only_ext_chk.isChecked()
        return r

    # ------------------------------------------------------------------
    # 扫描 / 预览 / 落地
    # ------------------------------------------------------------------
    def _pick_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择要整理的文件夹",
                                             self.src_input.text() or str(Path.home()))
        if d:
            self.src_input.setText(d)

    def _scan(self) -> None:
        raw = self.src_input.text().strip()
        src = Path(raw)
        if not raw or not src.is_dir():
            QMessageBox.warning(self, "目录无效", "请选择有效的目标文件夹。")
            return
        items = load_items(src)
        self._items = items
        self._clear_rows()
        if items:
            self._render()
            self._apply_hint(f"共 {len(items)} 项，配置规则实时查看预览。")
        else:
            self._apply_hint("目录下没有可处理的文件。")
        self.count_label.setText(f"共 {len(items)} 项")

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.hide()
            row.setParent(None)
            row.deleteLater()
        self._rows = []

    def _sync_keep_ext_visible(self) -> None:
        self.keep_ext.setVisible(self.op_combo.currentData() != Operation.SET_EXT)

    def _schedule_refresh(self) -> None:
        if not self._items:
            return
        self._refresh_timer.start()

    def _apply_hint(self, text: str, color: str = "") -> None:
        self._rule_hint.setText(text)
        self._rule_hint.setStyleSheet(f"color:{color};" if color else "")

    def _render(self) -> None:
        if not self._items:
            return
        rule = self._build_rule()
        rows = apply_rule(self._items, rule)
        changed = sum(1 for r in rows if r["changed"])
        errors = [r for r in rows if r["note"]]
        while len(self._rows) < len(rows):
            self._rows.append(_Row(self.container))
            self.list_lay.insertWidget(self.list_lay.count() - 1, self._rows[-1])
        for rowwidget, row in zip(self._rows, rows):
            rowwidget.set(row["old"], row["new"], row["note"], row["changed"])
        for rowwidget in self._rows[len(rows):]:
            rowwidget.set("", "", "", False)
            rowwidget.hide()
        for rowwidget, row in zip(self._rows, rows):
            rowwidget.setVisible(True)

        if errors:
            self._apply_hint(f"将变化 {changed} 项 · {len(errors)} 项有误（见红色行），应用将被跳过",
                             _COLOR_ERR)
        elif not rule.template and rule.operation == Operation.TEMPLATE:
            self._apply_hint("请先输入模板或点击变量按钮。", _COLOR_OLD)
        else:
            self._apply_hint(f"将变化 {changed} 项", _COLOR_OK if changed else _COLOR_OLD)

    def _reset(self) -> None:
        if self.op_combo.currentData() == Operation.TEMPLATE:
            self.template_input.clear()
        elif self.op_combo.currentData() == Operation.FIND_REPLACE:
            self.find_input.clear(); self.replace_input.clear()
        elif self.op_combo.currentData() == Operation.SET_EXT:
            self.ext_input.clear()
        elif self.op_combo.currentData() == Operation.DELETE_CHARS:
            self.start_spin.setValue(0); self.count_spin.setValue(1)
        self._render_after_reset()

    def _render_after_reset(self) -> None:
        if self._items:
            self._render()

    def _apply(self) -> None:
        if not self._items:
            return
        rule = self._build_rule()
        rows = apply_rule(self._items, rule)
        plans = rule_to_plans(rows)
        errors = [r for r in rows if r["note"]]
        if errors:
            QMessageBox.warning(self, "存在无效配置",
                                f"{len(errors)} 项规则无效，已取消应用。\n请修正后用红色行提示定位。")
            self._render()
            return
        if not plans:
            QMessageBox.information(self, "无需更改", "当前规则不会改变任何文件。")
            return
        changed = len(plans)
        q = QMessageBox.question(
            self, "确认应用", f"确认将 {changed} 个文件重命名？\n\n此操作会覆盖目标名称，请先确认预览无误。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if q != QMessageBox.StandardButton.Yes:
            return
        apply_plans(plans, dry_run=False)
        self._apply_hint(f"已完成重命名 {changed} 项", _COLOR_OK)
        self.count_label.setText(f"共 {len(self._items)} 项")
        # 刷新文件列表（已落地的 path 变化）
        raw = self.src_input.text().strip()
        if raw and Path(raw).is_dir():
            self._items = load_items(Path(raw))
            self._clear_rows()
            self._render()

    def _clean(self) -> None:
        raw = self.src_input.text().strip()
        src = Path(raw)
        if not raw or not src.is_dir():
            QMessageBox.warning(self, "目录无效", "请先选择有效的目标文件夹。")
            return
        plans = plan_cleanup(src)
        if not plans:
            QMessageBox.information(self, "无需清理", "未发现垃圾文件（Thumbs.db / tmp / part 等）。")
            return
        names = "\n".join([Path(p.old).name for p in plans[:50]])
        if len(plans) > 50:
            names += f"\n… 及另外 {len(plans) - 50} 项"
        q = QMessageBox.question(
            self, "确认清理", f"确认删除以下 {len(plans)} 个垃圾文件？此操作不可撤销。\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if q != QMessageBox.StandardButton.Yes:
            return
        apply_plans(plans, dry_run=False)
        self._apply_hint(f"已清理 {len(plans)} 个垃圾文件", _COLOR_OK)


class _Row(QWidget):
    """预览表的一行：原名称 → 转换后名称；错误整行红色。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(8)
        self.old = QLabel("")
        self.old.setObjectName("TaskMeta")
        self.old.setStyleSheet(f"color:{_COLOR_OLD};")
        self.arrow = QLabel("→")
        self.arrow.setObjectName("TaskMeta")
        self.arrow.setStyleSheet(f"color:{_COLOR_OLD};")
        self.new = QLabel("")
        self.new.setObjectName("TaskMeta")
        self.new.setStyleSheet(f"color:{_COLOR_NEW};font-weight:600;")
        lay.addWidget(self.old, 1)
        lay.addWidget(self.arrow)
        lay.addSpacing(26)
        lay.addWidget(self.new, 1)
        lay.addStretch(1)

    def set(self, old: str, new: str, note: str, changed: bool) -> None:
        self.old.setText(old)
        if note:
            self.old.setStyleSheet(f"color:{_COLOR_ERR};")
            self.new.setText(f"✕ {note}")
            self.new.setStyleSheet(f"color:{_COLOR_ERR};")
        elif changed:
            self.old.setStyleSheet(f"color:{_COLOR_OLD};")
            self.new.setText(new)
            self.new.setStyleSheet(f"color:{_COLOR_NEW};font-weight:600;")
        else:
            self.old.setStyleSheet(f"color:{_COLOR_OLD};")
            self.new.setText("—")
            self.new.setStyleSheet(f"color:{_COLOR_OLD};")