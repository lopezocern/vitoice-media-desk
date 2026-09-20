"""阶段一自检（无头 offscreen）：
1. 界面构造：主窗口 / 压缩页 / 设置页的控件齐全可创建；
2. 配置读写回环；
3. 环境探测（FFmpeg / 编码器）；
4. 压缩命令构建（离线条断言，不执行 ffmpeg）。

注意：本开发环境的 ffmpeg 为精简裁剪版（无 lavfi、仅 libx264），
无法本地生成样本做真实压测。真实压缩请在装有完整 ffmpeg 的机器上执行。
用法：.venv\\Scripts\\python.exe tests\\smoke_test.py  （设置 QT_QPA_PLATFORM=offscreen）
"""
from __future__ import annotations

import os
import sys
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


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from app.config import AppConfig, init_env
    from app.env import probe_env
    from app.ffmpeg_runner import (
        build_audio_extract_cmd, build_compress_cmd, build_concat_cmd,
        build_convert_cmd, build_cut_cmd, parse_time_to_secs, write_concat_list,
    )
    from app.renamer import apply_plans, plan_cleanup, plan_rename
    from app.task import TaskPool
    from app.ui.main_window import MainWindow
    from app.ui.styles import QSS

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    init_env()

    print("== 1) 桌面壳层构造 ==")
    win = MainWindow(TaskPool())
    win.show()
    comp = win._pages["视频压缩"]
    cut = win._pages["视频切割"]
    concat = win._pages["视频拼接"]
    conv = win._pages["格式转换"]
    rname = win._pages["文件整理"]
    settings = win._pages["全局设置"]
    for lbl, cond in [
        ("侧边栏 7 项", len(win.sidebar._buttons) == 7),
        ("压缩页存在", comp is not None),
        ("切割页存在", cut is not None),
        ("拼接页存在", concat is not None),
        ("转换页存在", conv is not None),
        ("整理页存在", rname is not None),
        ("设置页存在", settings is not None),
        ("压缩页含添加按钮", hasattr(comp, "add_btn")),
        ("压缩页含开始按钮", hasattr(comp, "start_btn")),
        ("压缩页含编码器标签", hasattr(comp, "enc_lbl")),
        ("压缩页含 CRF", hasattr(comp, "crf")),
        ("压缩页含分辨率", hasattr(comp, "res")),
        ("切割页含模式选择", hasattr(cut, "mode")),
        ("切割页含 CRF", hasattr(cut, "crf")),
        ("切割页含开始按钮", hasattr(cut, "start_btn")),
        ("拼接页含模式选择", hasattr(concat, "mode")),
        ("拼接页含输出后缀", hasattr(concat, "suffix")),
        ("拼接页含开始按钮", hasattr(concat, "start_btn")),
        ("转换页含格式选择", hasattr(conv, "fmt")),
        ("转换页含分辨率", hasattr(conv, "res")),
        ("转换页含 GPU", hasattr(conv, "gpu")),
        ("转换页含提取音频", hasattr(conv, "audio_only")),
        ("转换页含开始按钮", hasattr(conv, "start_btn")),
        ("整理页含目录输入", hasattr(rname, "src_input")),
        ("整理页含操作类型下拉", hasattr(rname, "op_combo")),
        ("整理页含重置规则按钮", hasattr(rname, "reset_btn")),
        ("设置页含 FFmpeg 输入", hasattr(settings, "ff_input")),
        ("设置页含 GPU 开关", hasattr(settings, "gpu")),
        ("底部任务栏已建", hasattr(win, "bar_running")),
    ]:
        check(lbl, cond)

    print("== 2) 配置读写回环 ==")
    cfg = AppConfig.instance()
    cfg.set_compress("suffix", "__test")
    check("写入后缀", True)
    check("读回后缀", cfg.get_compress("suffix") == "__test", cfg.get_compress("suffix"))
    cfg.set_compress("suffix", "_compressed")
    check("还原后缀", cfg.get_compress("suffix") == "_compressed")

    print("== 3) 环境探测 ==")
    probe = probe_env()
    check("ffmpeg 可运行", probe.ffmpeg_ok)
    # 编码器随 gpu_enabled 切换（探测与开关解耦后，硬编可用性由 ffmpeg 决定）
    cfg = AppConfig.instance()
    saved = cfg.get("gpu_enabled")
    try:
        cfg.set("gpu_enabled", False)
        check("GPU 关闭时编码器为 libx264", probe.encoder == "libx264", probe.encoder)
        if probe.gpu_encoders:
            cfg.set("gpu_enabled", True)
            check("GPU 开启且硬编可用时为 nvenc", probe.encoder in probe.gpu_encoders, probe.encoder)
        else:
            check("GPU 开启但无硬编时回退 libx264", probe.encoder == "libx264", probe.encoder)
    finally:
        cfg.set("gpu_enabled", saved)
    print(f"     环境标签: {probe.label}")

    print("== 4) 压缩命令构建（离线断言） ==")
    keep = build_compress_cmd("a.mp4", "o.mp4", "libx264", 28, "ultrafast",
                              "keep", None, None, "keep", 30)
    check("keep 无 scale", all("-vf" not in c for c in keep) and "scale" not in " ".join(keep))
    check("libx264 含 -crf 28", "-crf" in keep and "28" in keep)

    scale = " ".join(build_compress_cmd("a.mp4", "o.mp4", "libx264", 18, "medium",
                                        "1080", None, None, "keep", 30))
    check("1080 含 scale=-2:1080", "scale=-2:1080" in scale, scale)

    nv = " ".join(build_compress_cmd("a.mp4", "o.mp4", "hevc_nvenc", 18, "medium",
                                     "keep", None, None, "keep", 30))
    check("nvenc 用 -cq 与 p4", "-cq" in nv and "p4" in nv, nv)

    print("== 5) 切割命令构建（离线断言） ==")
    rc = " ".join(build_cut_cmd("a.mp4", "o.mp4", "00:00:00", "00:01:30",
                                "reencode", "libx264", 20, "fast"))
    check("重编码含 -ss/-to", "-ss" in rc and "-to" in rc, rc)
    check("重编码含 libx264/crf", "libx264" in rc and "-crf" in rc and "20" in rc)
    check("重编码 -ss 在 -i 之后", rc.index("-ss") > rc.index("-i"), rc)

    cc = " ".join(build_cut_cmd("a.mp4", "o.mp4", "00:00:00", "00:00:10", "copy"))
    check("流复制含 -c copy", "-c" in cc and "copy" in cc, cc)
    check("流复制 -ss 在 -i 之前", cc.index("-ss") < cc.index("-i"), cc)

    check("时间解析 HH:MM:SS", parse_time_to_secs("01:02:03") == 3723)
    check("时间解析 MM:SS", parse_time_to_secs("05:30") == 330)
    check("时间解析 纯秒", parse_time_to_secs("90") == 90)

    print("== 6) 拼接命令构建（离线断言） ==")
    from app.ffmpeg_runner import write_concat_list as _wc
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".txt")
    _wc(tmp, ["C:/v/a.mp4", "C:/v/b.mp4"])
    content = open(tmp, encoding="utf-8").read()
    os.remove(tmp)
    check("列表文件含 file 行", content.count("file '") == 2, repr(content))
    check("顺序保留 a 在 b 前", content.index("a.mp4") < content.index("b.mp4"), repr(content))

    cc = " ".join(build_concat_cmd("list.txt", "o.mp4", "copy"))
    check("流复制含 -f concat", "-f" in cc and "concat" in cc, cc)
    check("流复制含 -c copy", "-c" in cc and "copy" in cc, cc)
    check("流复制含 -safe 0", "-safe" in cc and "0" in cc, cc)

    rc = " ".join(build_concat_cmd("list.txt", "o.mp4", "reencode", "libx264", 18, "fast"))
    check("重编码含 libx264/crf", "libx264" in rc and "-crf" in rc and "18" in rc, rc)
    check("重编码含 aac", "-c:a" in rc and "aac" in rc, rc)

    print("== 7) 格式转换命令构建（离线断言） ==")
    m = " ".join(build_convert_cmd("a.mp4", "a.webm", fmt="webm", quality="balance"))
    check("webm 含 libvpx", "libvpx" in m and "webm" in m, m)
    check("webm 含量率与 g", "-b:v" in m and "-g" in m and "30" in m, m)

    mp = " ".join(build_convert_cmd("a.mp4", "a.mkv", fmt="mkv", quality="high",
                                    resolution="1280x720"))
    check("mkv 缩放含 -vf scale", "-vf" in mp and "scale=1280x720" in mp, mp)
    check("mkv 高清画质 crf=18", "-crf" in mp and "18" in mp, mp)

    noa = " ".join(build_convert_cmd("a.mp4", "a.mp4", fmt="mp4", audio="none"))
    check("去掉音频含 -an", "-an" in noa, noa)

    ext = " ".join(build_audio_extract_cmd("a.mp4", "a.m4a"))
    check("提取音频含 -vn 与 aac", "-vn" in ext and "aac" in ext, ext)

    print("== 8) 文件整理（功能级，临时目录） ==")
    import tempfile, sys as _sys
    tmpd = Path(tempfile.mkdtemp(prefix="mdesk_"))
    (tmpd / "测试视频.mp4").write_bytes(b"x")
    (tmpd / "Thumbs.db").write_bytes(b"x")
    (tmpd / "already.mp4").write_bytes(b"x")
    try:
        rp = plan_rename(tmpd, "files")
        check("识别中文名文件", len(rp) == 1 and "测试视频" in rp[0].new, str(rp))
        check("拼音前缀大写字母", rp and rp[0].new[:1].isalpha() and rp[0].new[0].isupper(),
              repr(rp[0].new) if rp else "空")
        apply_plans(rp, dry_run=True)
        check("干跑不落地", (tmpd / "测试视频.mp4").exists())
        apply_plans(rp, dry_run=False)
        check("应用后已重命名", (tmpd / rp[0].new).exists() and not (tmpd / "测试视频.mp4").exists())

        cp = plan_cleanup(tmpd)
        check("识别垃圾文件", any("Thumbs.db" in c.old for c in cp), str(cp))
        apply_plans(cp, dry_run=False)
        check("垃圾文件已删除", not (tmpd / "Thumbs.db").exists())
    finally:
        import shutil as _sh
        _sh.rmtree(tmpd, ignore_errors=True)

    print("== 9) 随包 FFmpeg 路径探测 ==")
    from app.env import _bundle_bit
    bb = _bundle_bit("ffmpeg.exe", base=Path(tempfile.mkdtemp()))
    check("随包缺路径返回 None", bb is None, repr(bb))
    tmpb = Path(tempfile.mkdtemp(prefix="mdesk_b_"))
    (tmpb / "ffmpeg").mkdir(parents=True)
    (tmpb / "ffmpeg" / "bin").mkdir()
    (tmpb / "ffmpeg" / "bin" / "ffmpeg.exe").write_bytes(b"")
    got = _bundle_bit("ffmpeg.exe", base=tmpb)
    check("随包命中返回绝对路径", bool(got) and Path(got).name == "ffmpeg.exe"
          and Path(got).parent.name == "bin"
          and Path(got).parent.parent.name == "ffmpeg", repr(got))

    print(f"\n结果: PASS {len(PASS)}  FAIL {len(FAIL)}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())