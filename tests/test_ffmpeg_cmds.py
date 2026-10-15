"""ffmpeg_runner 纯函数单测（命令构建 / 时间解析 / 输出避让 / 半成品清理）。

不执行真实 ffmpeg；环境隔离同 smoke_test（MEDIADESK_CONFIG_DIR 指向
tests/.media-config）。断言只针对参数片段，不含 argv[0] 的 ffmpeg 路径。
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MEDIADESK_CONFIG_DIR", str(ROOT / "tests" / ".media-config"))

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  [{'OK' if cond else 'FAIL'}] {name}" + (f"  | {detail}" if detail else ""))


def args(cmd: list[str]) -> str:
    """去掉 argv[0]（ffmpeg 路径随环境），拼成空格串便于断言。"""
    return " ".join(cmd[1:])


def main() -> int:
    from app.ffmpeg_runner import (
        _enc_args, _unoccupied, build_audio_extract_cmd, build_compress_cmd,
        build_concat_cmd, build_convert_cmd, build_cut_cmd, parse_time_to_secs,
        resolve_output, write_concat_list,
    )
    from app.task import _cleanup_partial
    import app.env as env_mod

    print("== 1) _enc_args（NVENC 单源映射 + 码率双模式）==")
    for preset, expect in [("slow", "p2"), ("medium", "p4"), ("fast", "p5"),
                            ("veryfast", "p7"), ("ultrafast", "p7")]:
        c = args(_enc_args("hevc_nvenc", 18, preset))
        check(f"nvenc {preset} → {expect}", f"-preset {expect}" in c, c)
    c = args(_enc_args("hevc_nvenc", 18, "unknown"))
    check("nvenc 未知 preset 回落 p4", "-preset p4" in c, c)
    c = args(_enc_args("libx264", 20, "fast"))
    check("软编 crf 模式 -crf 20", "-crf 20" in c and "-b:v" not in c, c)
    c = args(_enc_args("libx264", 20, "fast", rate_mode="bitrate", bitrate=6.0))
    check("软编 bitrate 模式 -b:v 6M 无 -crf", "-b:v 6M" in c and "-crf" not in c, c)
    c = args(_enc_args("hevc_nvenc", 20, "fast", rate_mode="bitrate", bitrate=4.5))
    check("nvenc bitrate 模式 -b:v 4.5M 无 -cq", "-b:v 4.5M" in c and "-cq" not in c, c)

    print("== 2) build_compress_cmd ==")
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast"))
    check("默认无 -vf 无 -r", "-vf" not in c and " -r " not in c, c)
    check("软编 -crf 23 + -c:a copy", "-crf 23" in c and "-c:a copy" in c, c)
    check("进度走 pipe", "-progress pipe:1" in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast", resolution="1280x720"))
    check("固定分辨率 scale", "-vf scale=1280:720" in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast", resolution="1080"))
    check("旧值 1080 宽自适应", "-vf scale=-2:1080" in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast",
                                resolution="custom", res_w=1919, res_h=1079))
    check("custom 奇数归偶", "-vf scale=1918:1078" in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast",
                                resolution="custom", res_w=None, res_h=None))
    check("custom 无宽高不加 -vf", "-vf" not in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "libx264", 23, "fast",
                                fps="custom", fps_value=24))
    check("fps 指定 -r 24", " -r 24" in c, c)
    c = args(build_compress_cmd("a.mp4", "o.mp4", "hevc_nvenc", 20, "medium",
                                rate_mode="bitrate", bitrate=8.0))
    check("nvenc 码率模式 -b:v 8M", "-b:v 8M" in c and "-cq" not in c, c)

    print("== 3) build_cut_cmd ==")
    c = args(build_cut_cmd("a.mp4", "o.mp4", "00:01:00", "00:02:00", mode="copy"))
    check("copy：-ss 前置 + -c copy", c.index("-ss") < c.index("-i") and "-c copy" in c, c)
    c = args(build_cut_cmd("a.mp4", "o.mp4", "00:01:00", "00:02:00"))
    check("reencode：-ss 后置 + aac", c.index("-ss") > c.index("-i") and "-c:a aac" in c, c)

    print("== 4) build_concat_cmd ==")
    c = args(build_concat_cmd("list.txt", "o.mp4", mode="copy"))
    check("copy 拼接 -f concat -safe 0", "-f concat -safe 0" in c and "-c copy" in c, c)
    c = args(build_concat_cmd("list.txt", "o.mp4", mode="reencode"))
    check("reencode 拼接带编码参数", "-c:a aac" in c and "-crf 18" in c, c)

    print("== 5) build_convert_cmd ==")
    c = args(build_convert_cmd("a.mp4", "o.webm", fmt="webm", quality="balance"))
    check("webm 强制 libvpx + libvorbis", "-c:v libvpx" in c and "-c:a libvorbis" in c, c)
    check("webm 平衡档 1M", "-b:v 1M" in c, c)
    c = args(build_convert_cmd("a.mp4", "o.webm", fmt="webm", quality="high"))
    check("webm 高画质档 2M", "-b:v 2M" in c, c)
    c = args(build_convert_cmd("a.mp4", "o.mp4", fmt="mp4", quality="small"))
    check("mp4 低体积档 -crf 28", "-c:v libx264" in c and "-crf 28" in c, c)
    c = args(build_convert_cmd("a.mp4", "o.mp4", fmt="mp4", resolution="1280x720"))
    check("分辨率 lanczos + yuv420p", "flags=lanczos" in c and "format=yuv420p" in c, c)
    c = args(build_convert_cmd("a.mp4", "o.mp4", fmt="mp4", audio="none"))
    check("去音频 -an", " -an" in c and "-c:a" not in c, c)

    print("== 6) build_audio_extract_cmd ==")
    c = args(build_audio_extract_cmd("a.mp4", "o.m4a"))
    check("提取音轨 -vn + aac", "-vn" in c and "-c:a aac" in c, c)

    print("== 7) parse_time_to_secs ==")
    check("纯秒", parse_time_to_secs("90") == 90)
    check("分:秒", parse_time_to_secs("1:30") == 90)
    check("时:分:秒", parse_time_to_secs("01:01:30") == 3690)
    try:
        parse_time_to_secs("abc")
        check("非法输入抛 ValueError", False)
    except ValueError:
        check("非法输入抛 ValueError", True)

    print("== 8) resolve_output / _unoccupied 避让 ==")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "a.mp4"
        src.write_bytes(b"x")
        p1 = resolve_output(str(src), td, "_compressed")
        check("首输出原名", p1.endswith("a_compressed.mp4"), p1)
        Path(p1).write_bytes(b"x")
        p2 = resolve_output(str(src), td, "_compressed")
        check("冲突避让 -2", p2.endswith("a_compressed-2.mp4"), p2)
        Path(p2).write_bytes(b"x")
        p3 = resolve_output(str(src), td, "_compressed")
        check("再冲突避让 -3", p3.endswith("a_compressed-3.mp4"), p3)
        src_noext = Path(td) / "noext"
        src_noext.write_bytes(b"x")
        check("无扩展名补 .mp4",
              resolve_output(str(src_noext), td, "_x").endswith("noext_x.mp4"))

        print("== 9) _cleanup_partial 半成品清理与源文件防护 ==")
        partial = Path(td) / "half.mp4"
        partial.write_bytes(b"x")
        _cleanup_partial(str(partial))
        check("半成品删除", not partial.exists())
        keep = Path(td) / "src.mp4"
        keep.write_bytes(b"x")
        _cleanup_partial(str(keep), protect=(str(keep),))
        check("protect 源文件不删", keep.exists())
        other = Path(td) / "other.mp4"
        other.write_bytes(b"x")
        _cleanup_partial(str(other), protect=(str(keep),))
        check("非 protect 照常删", not other.exists())
        _cleanup_partial(str(Path(td) / "notexist.mp4"))
        check("不存在的路径不抛错", True)

        print("== 10) write_concat_list 转义 ==")
        lst = Path(td) / "list.txt"
        tricky = str(Path(td) / "it's a'file.mp4")
        write_concat_list(str(lst), [tricky])
        content = lst.read_text(encoding="utf-8")
        check("单引号转义写入", "it'\\''s a'\\''file.mp4" in content, content.strip())

        print("== 11) probe_duration_ms 缓存 ==")
        calls: list[list[str]] = []
        orig_run = env_mod.subprocess.run

        class _FakeResult:
            stdout = "1.5\n"

        def fake_run(argv, **kw):
            calls.append(argv)
            return _FakeResult()

        env_mod.subprocess.run = fake_run
        try:
            v = Path(td) / "v.mp4"
            v.write_bytes(b"x")
            a = env_mod.probe_duration_ms(v)
            b = env_mod.probe_duration_ms(v)
            check("两次探测仅 1 次子进程（缓存命中）", a == 1500 and b == 1500 and len(calls) == 1,
                  f"a={a} b={b} calls={len(calls)}")
            os.utime(v, (time.time() + 5, time.time() + 5))
            c_ = env_mod.probe_duration_ms(v)
            check("mtime 变化后缓存失效重探", c_ == 1500 and len(calls) == 2,
                  f"calls={len(calls)}")
        finally:
            env_mod.subprocess.run = orig_run

    print(f"\n结果: PASS {len(PASS)}  FAIL {len(FAIL)}")
    if FAIL:
        print("失败项:", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
