"""文件整理引擎：中文名拼音首字母前缀重命名 + 垃圾文件清理。

纯 Python，无 Qt 依赖；核心逻辑支持干跑（只返回计划、不落地），便于预览。
对应 legacy `file_clean/rename_pypinyin.py`，扩展为文件夹+文件、并加入清理能力。
"""
from __future__ import annotations

import datetime
import random
import re
import unicodedata
import urllib.parse
import uuid as _uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# 常见临时/垃圾文件规则（文件名 glob 或精确名）
JUNK_PATTERNS: list[tuple[str, str]] = [
    ("Thumbs.db", "Windows 缩略图缓存"),
    ("desktop.ini", "Windows 目录配置"),
    (".DS_Store", "macOS 目录配置"),
    ("*.tmp", "临时文件"),
    ("*.part", "未下载完整文件"),
    ("*.bak", "备份文件"),
    ("*.old", "旧版本文件"),
    ("*.cache", "缓存文件"),
    ("*.orig", "原始备份"),
]


@dataclass
class Plan:
    old: str
    new: str
    kind: str = "rename"          # rename / cleanup
    note: str = ""
    __items: list = field(default_factory=list, repr=False)

    def accept(self) -> None:
        if self.kind == "rename":
            Path(self.old).rename(self.new)
        else:
            try:
                Path(self.old).unlink()
            except PermissionError:
                pass


def _first_letter(text: str) -> str:
    """取首个中文的拼音首字母（大写）。缺 pypinyin 时降级返回 '#'。"""
    try:
        from pypinyin import Style, pinyin
        result = pinyin(text[:1], style=Style.FIRST_LETTER)
        if result and result[0] and result[0][0]:
            return result[0][0].upper()
    except Exception:
        pass
    return "#"


def is_chinese(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def eligible_for_rename(name: str) -> bool:
    """是否值得加拼音前缀：以中文开头（未被英文/序号开头覆盖）。"""
    return bool(name) and is_chinese(name[0])


def _targets(source: Path, targets: str) -> list[Path]:
    if targets in ("folders", "both"):
        for p in sorted(source.iterdir()):
            if p.is_dir():
                yield p
    if targets in ("files", "both"):
        for p in sorted(source.iterdir()):
            if p.is_file():
                yield p


def plan_rename(source: Path, targets: str = "folders") -> list[Plan]:
    """返回「中文名 → 加拼音首字母前缀」的重命名计划（不落地）。"""
    plans: list[Plan] = []
    for p in _targets(source, targets):
        if not eligible_for_rename(p.name):
            continue
        letter = _first_letter(p.name)
        new_name = f"{letter} {p.name}"
        if new_name == p.name:
            continue
        plans.append(Plan(str(p), str(p.with_name(new_name)), "rename",
                          f"拼音首字母：{letter}"))
    return plans


def plan_cleanup(source: Path) -> list[Plan]:
    """返回匹配垃圾规则的删除计划（不落地）。"""
    plans: list[Plan] = []
    for child in sorted(source.iterdir()):
        for pattern, label in JUNK_PATTERNS:
            matched = child.name == pattern or (
                pattern.startswith("*") and child.name.endswith(pattern[1:]))
            if matched and child.is_file():
                plans.append(Plan(str(child), "", "cleanup", label))
                break
    return plans


def apply_plans(plans: list[Plan], dry_run: bool = True) -> tuple[int, int]:
    """执行计划（重命名/清理）。dry_run=True 时不落地，只返回 (计划数, 落数)。"""
    applied = 0
    if dry_run:
        return len(plans), 0
    for plan in plans:
        plan.accept()
        applied += 1
    return len(plans), applied


# ======================================================================
# 规则驱动批量重命名引擎（阶段三）
# 纯 Python、无 Qt 依赖；核心逻辑一律先算“目标名”、不落地，供实时预览。
# ======================================================================


class Operation(str, Enum):
    FIND_REPLACE = "find_replace"
    TEMPLATE = "template"
    DELETE_CHARS = "delete_chars"
    TRANSFORM = "transform"
    SET_EXT = "set_ext"


@dataclass
class Rule:
    """一条重命名规则。不同 operation 只用到各自参数。"""

    operation: Operation = Operation.TEMPLATE
    keep_ext: bool = True

    # find_replace
    find: str = ""
    replace: str = ""
    regex: bool = False
    ignore_case: bool = False
    replace_all: bool = True

    # template
    template: str = ""

    # delete_chars
    start: int = 0
    count: int = 0
    from_end: bool = False

    # transform
    transform: str = "lower"       # lower/upper/title/capitalize/ascii_fold/url_decode

    # set_ext
    ext: str = ""
    only_existing: bool = True


@dataclass
class Item:
    """扫描到的一个待处理项（UI 预览用）。"""

    path: Path
    stem: str                       # 主名（不含扩展名）
    ext: str                        # 扩展名（含点）或 ""
    parent: str = ""                # 所在目录名
    ctime: datetime.datetime = field(default_factory=datetime.datetime.now)
    mtime: datetime.datetime = field(default_factory=datetime.datetime.now)

    @property
    def original_full(self) -> str:
        return self.stem + self.ext


TRANSFORM_LABELS = {
    "lower": "改为小写 (abc)",
    "upper": "改为大写 (ABC)",
    "title": "改为标题式大写",
    "capitalize": "改为首字母大写 (Abc)",
    "ascii_fold": "移除特殊符号 (äé→ae)",
    "url_decode": "URL 解码 (a%20b→a b)",
}


def load_items(source: Path) -> list[Item]:
    """扫描目录的直属文件为待重命名项（不递归）。"""
    items: list[Item] = []
    for p in sorted(source.iterdir()):
        if not p.is_file():
            continue
        items.append(Item(
            path=p,
            stem=p.stem,
            ext=p.suffix,
            parent=p.parent.name,
            ctime=_to_dt(p.stat().st_ctime),
            mtime=_to_dt(p.stat().st_mtime),
        ))
    return items


def _to_dt(ts: float) -> datetime.datetime:
    try:
        return datetime.datetime.fromtimestamp(ts)
    except (OSError, OverflowError, ValueError):
        return datetime.datetime.now()


# ---- 变量解析 ----
_VAR_RE = re.compile(r"\$\{([^{}]+)\}")
_TIME_TOKENS = {
    "yyyy": "%Y", "MM": "%m", "dd": "%d", "HH": "%H", "mm": "%M", "ss": "%S",
}


def _fmt_time(dt: datetime.datetime, fmt: str) -> str:
    for token, conv in _TIME_TOKENS.items():
        fmt = fmt.replace(token, conv)
    return dt.strftime(fmt)


def _seq_params(template: str) -> tuple[int, int, int]:
    """从模板里解析首个 ${seq:...}，返回 (start, increment, padding)。"""
    m = _VAR_RE.search(template or "")
    if m:
        spec = re.search(r"^seq:(.*)$", m.group(1))
        if spec:
            params: dict[str, int] = {}
            for kv in spec.group(1).split(";"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if v.isdigit():
                        params[k.strip()] = int(v)
            return (params.get("start", 1), params.get("increment", 1),
                    params.get("padding", 3))
    return 1, 1, 3


def _apply_replace(target: str, rule: Rule) -> str:
    find = rule.find
    if rule.regex:
        try:
            flags = re.IGNORECASE if rule.ignore_case else 0
            return re.sub(find, rule.replace, target,
                          count=0 if rule.replace_all else 1, flags=flags)
        except re.error:
            return f"<正则错误>"
    if rule.ignore_case:
        if rule.replace_all:
            return target.replace(find, rule.replace)
        idx = target.lower().find(find.lower())
        if idx < 0:
            return target
        return target[:idx] + rule.replace + target[idx + len(find):]
    return target.replace(find, rule.replace) if rule.replace_all \
        else target.replace(find, rule.replace, 1)


def _delete_chars(target: str, start: int, count: int, from_end: bool) -> str:
    if count <= 0:
        return target
    n = len(target)
    if from_end:
        pos = n - start          # 从末尾计数定位删除起点
        if pos < 0 or pos > n:
            return target
        return target[:pos] + target[pos + count:]
    if start > n:
        return target
    return target[:start] + target[start + count:]


def _transform(target: str, kind: str) -> str:
    if kind == "lower":
        return target.lower()
    if kind == "upper":
        return target.upper()
    if kind == "title":
        return target.title()
    if kind == "capitalize":
        return target[:1].upper() + target[1:]
    if kind == "ascii_fold":
        out = []
        for ch in unicodedata.normalize("NFKD", target):
            if ch.isascii():
                out.append(ch)
        return "".join(out)
    if kind == "url_decode":
        try:
            return urllib.parse.unquote(target)
        except Exception:
            return target
    return target


def _render_template(template: str, item: Item, seq_val: int, random_val: str,
                     uuid_val: str) -> str:

    def repl(m: re.Match) -> str:
        body = m.group(1)
        name = body.split(":", 1)[0].strip()
        arg = body.split(":", 1)[1] if ":" in body else ""
        if name == "original":
            return item.stem
        if name == "folder":
            return item.parent
        if name == "create_time":
            return _fmt_time(item.ctime, arg or "yyyy-MM-dd")
        if name == "modify_time":
            return _fmt_time(item.mtime, arg or "yyyy-MM-dd")
        if name == "seq":
            _, _, padding = _seq_params("${" + body + "}")
            return f"{seq_val:0{padding}d}"
        if name == "random":
            try:
                n = max(1, int(arg or "6"))
            except ValueError:
                n = 6
            return "".join(random_val[:n])
        if name == "uuid":
            return uuid_val
        if name == "pinyin_first":
            return _first_letter(item.stem)
        if name == "pinyin_prefix":
            # 拼音前缀预设：仅中文开头才加「拼音+空格+原名」，否则保持原名（跳过）
            if eligible_for_rename(item.stem):
                return f"{_first_letter(item.stem)} {item.stem}"
            return item.stem
        return f"<%未知:{name}>"

    return _VAR_RE.sub(repl, template)


def _render_one(item: Item, rule: Rule, seq_val: int = 0,
                random_val: str = "", uuid_val: str = "") -> tuple[str, str]:
    """返回 (目标全名, 备注/错误)。错误以 note 标记且 name 置空。"""
    ext = item.ext
    if rule.operation == Operation.SET_EXT:
        new_ext = rule.ext
        if not new_ext:
            return "", "扩展名为空"
        if not new_ext.startswith("."):
            new_ext = "." + new_ext
        if rule.only_existing and not ext:
            return item.original_full, ""        # 无扩展名不改
        return item.stem + new_ext, ""

    target = item.stem if rule.keep_ext else item.original_full
    if target == "":
        return "", "主名为空"

    if rule.operation == Operation.FIND_REPLACE:
        if not rule.find and not rule.regex:
            return "", "查找内容为空"
        new_target = _apply_replace(target, rule)
    elif rule.operation == Operation.TEMPLATE:
        if not (rule.template and rule.template.strip()):
            return "", "模板为空"
        new_target = _render_template(rule.template, item, seq_val, random_val, uuid_val)
    elif rule.operation == Operation.DELETE_CHARS:
        new_target = _delete_chars(target, rule.start, rule.count, rule.from_end)
    elif rule.operation == Operation.TRANSFORM:
        new_target = _transform(target, rule.transform)
    else:
        return "", "暂不支持的操作"

    if "<正则错误>" in new_target:
        return "", "正则表达式无效"
    if "<%已知" in new_target or "<%未知" in new_target:
        return "", "模板包含未知变量"
    name = new_target + ext if rule.keep_ext else new_target
    return name, ""


def apply_rule(items: list[Item], rule: Rule) -> list[dict]:
    """把规则应用到一批文件，返回预览行（不落地）：
    每行 {item, old, new, changed, note}。seq 按列表顺序分配。"""
    if rule.operation == Operation.TEMPLATE:
        start, inc, pad = _seq_params(rule.template)
    else:
        start, inc, pad = 1, 1, 3

    rows: list[dict] = []
    seen_seq = start
    for idx, item in enumerate(items):
        if rule.operation == Operation.TEMPLATE:
            seq_val = seen_seq
            seen_seq += inc
        else:
            seq_val = idx
        random_val = "".join(random.choices(
            "abcdefghijklmnopqrstuvwxyz0123456789", k=12))
        uuid_val = str(_uuid.uuid4())
        new_name, note = _render_one(item, rule, seq_val, random_val, uuid_val)
        rows.append({
            "item": item,
            "old": item.original_full,
            "new": new_name,
            "changed": bool(note == "" and new_name and new_name != item.original_full),
            "note": note,
        })
    return rows


def rule_to_plans(rows: list[dict], kind: str = "rename") -> list[Plan]:
    """把预览行转成待落地 Plan（仅 rename 类型有目标名；错误/未变化可过滤）。"""
    plans: list[Plan] = []
    for row in rows:
        if row.get("note"):
            continue
        if row["changed"]:
            plans.append(Plan(str(row["item"].path),
                              str(row["item"].path.with_name(row["new"])),
                              kind, "规则重命名"))
    return plans