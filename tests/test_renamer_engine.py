"""文件整理重命名引擎的验收测试（无 Qt 依赖，可直接 python 运行）。

覆盖需求《文件整理模块重构-需求设计（精简）》的验收示例 A1–A6
与变量语法/参数化序列/忽略大小写/未知变量提示/落地 plans 转换。
"""
import datetime as dt
import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent.parent))

from app.renamer import (
    Item, Operation, Rule, apply_rule, rule_to_plans,
)


def _it(stem, ext=".jpg", parent="f",
        c=dt.datetime(2026, 7, 28, 21, 34, 43),
        m=dt.datetime(2026, 9, 11, 19, 16, 48)):
    return Item(path=_P("x"), stem=stem, ext=ext, parent=parent, ctime=c, mtime=m)


def _names(rows):
    return [r["new"] for r in rows]


def test_template_create_time_seq():
    items = [_it(f"photo_{i}") for i in range(3)]
    r = Rule(operation=Operation.TEMPLATE,
             template="${create_time:yyyy-MM-dd}_${seq:start=1;increment=1;padding=3}",
             keep_ext=True)
    rows = apply_rule(items, r)
    assert _names(rows) == ["2026-07-28_001.jpg", "2026-07-28_002.jpg",
                            "2026-07-28_003.jpg"], _names(rows)


def test_find_replace_regex():
    r = Rule(operation=Operation.FIND_REPLACE, find=r"^Z ",
             replace="", regex=True, keep_ext=True)
    row = apply_rule([_it("Z 张韶涵_P_019")], r)[0]
    assert row["new"] == "张韶涵_P_019.jpg"
    assert row["changed"]


def test_delete_chars():
    r = Rule(operation=Operation.DELETE_CHARS, start=0, count=5,
             from_end=False, keep_ext=True)
    assert apply_rule([_it("abcdeFGH")], r)[0]["new"] == "FGH.jpg"
    r2 = Rule(operation=Operation.DELETE_CHARS, start=2, count=2,
              from_end=True, keep_ext=True)
    assert apply_rule([_it("abcde")], r2)[0]["new"] == "abc.jpg"


def test_transform_lower():
    r = Rule(operation=Operation.TRANSFORM, transform="lower", keep_ext=True)
    assert apply_rule([_it("Z 张韶涵_P_019")], r)[0]["new"] == "z 张韶涵_p_019.jpg"


def test_set_ext_only_existing():
    r = Rule(operation=Operation.SET_EXT, ext=".jpeg", only_existing=True)
    rows = apply_rule([_it("a", ".jpg"), _it("b", "")], r)
    assert rows[0]["new"] == "a.jpeg"
    assert rows[1]["new"] == "b"          # 无扩展名不改
    assert rows[1]["changed"] is False
    r2 = Rule(operation=Operation.SET_EXT, ext=".mp4", only_existing=False)
    assert apply_rule([_it("b", "")], r2)[0]["new"] == "b.mp4"


def test_pinyin_preset():
    r = Rule(operation=Operation.TEMPLATE, template="${pinyin_prefix}",
             keep_ext=True)
    rows = apply_rule([_it("测试视频", ".mp4"), _it("Video", ".mp4")], r)
    assert rows[0]["new"] == "C 测试视频.mp4", rows[0]["new"]
    assert rows[1]["changed"] is False     # 英文开头跳过（前后一致）


def test_seq_params():
    r = Rule(operation=Operation.TEMPLATE,
             template="${seq:start=10;increment=2;padding=4}", keep_ext=True)
    items = [_it(f"x{i}") for i in range(3)]
    assert _names(apply_rule(items, r)) == ["0010.jpg", "0012.jpg", "0014.jpg"]


def test_ignore_case_single_replacement():
    r = Rule(operation=Operation.FIND_REPLACE, find="photo", replace="Pic",
             regex=False, ignore_case=True, replace_all=False, keep_ext=True)
    row = apply_rule([_it("PHOTO_a")], r)[0]
    assert row["new"] == "Pic_a.jpg", row["new"]


def test_unknown_variable_notes():
    r = Rule(operation=Operation.TEMPLATE, template="${foo}", keep_ext=True)
    row = apply_rule([_it("a")], r)[0]
    assert row["note"] and not row["new"]


def test_rule_to_plans():
    from app.renamer import Operation, Rule, apply_rule
    r = Rule(operation=Operation.TEMPLATE, template="${pinyin_prefix}",
             keep_ext=True)
    rows = apply_rule([_it("测试视频", ".mp4")], r)
    plans = rule_to_plans(rows)
    assert len(plans) == 1
    assert plans[0].old == "x"
    # Path("x") 是仅文件名的占位路径，with_name 结果不含目录前缀
    assert plans[0].new == "C 测试视频.mp4", plans[0].new


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa
                failures += 1
                print("FAIL", name, "->", repr(e))
    print("引擎测试:", "PASS" if failures == 0 else f"FAIL {failures}")
    raise SystemExit(1 if failures else 0)