"""绿色便携版发布脚本。

仅使用 PySide6-Essentials（QtCore/QtGui/QtWidgets），避免打入 WebEngine 等未用
模块，显著瘦身。步骤：
  1) 准备构建虚拟环境 .venv-build（装 PySide6-Essentials + PyInstaller + pypinyin）
  2) pyinstaller 打 onedir 绿色目录（dist/MediaDesk），排除 .env 与重型 Qt 模块
  3) 把完整版 FFmpeg essentials（ffmpeg.exe/ffprobe.exe）放入 dist/MediaDesk/ffmpeg/bin
  4) 打印产物体积
用法：
  python scripts/portable_build.py          # 全流程
  python scripts/portable_build.py --skip-ffmpeg   # 暂不拉 FFmpeg（体积小）
"""
from __future__ import annotations

import os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_VENV = ROOT / ".venv-build"
DIST = ROOT / "dist" / "MediaDesk"
COMPLIANCE = ROOT / "docs" / "compliance" / "LICENSE_NOTICE.md"
ASSETS = ROOT / "app" / "assets"
LOGO_ICO = ASSETS / "logo.ico"

# 本项目完全用不到的 PySide6 重型/附加模块，逐个排除
EXCLUDE_MODULES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtDesigner",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtRemoteObjects", "PySide6.QtSerialPort", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtPrintSupport", "PySide6.QtSpatialAudio",
]


def _run(cmd, **kw):
    print(">>", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def prepare_venv() -> Path:
    if BUILD_VENV.exists():
        return BUILD_VENV
    _run([sys.executable, "-m", "venv", str(BUILD_VENV)])
    py = BUILD_VENV / "Scripts" / "python.exe"
    _run([py, "-m", "pip", "install", "--upgrade", "pip"])
    # 刻意装 Essentials 而非全量 PySide6，是体积关键
    _run([py, "-m", "pip", "install",
          "PySide6-Essentials", "PyInstaller>=6.0", "pypinyin>=0.55"])
    return BUILD_VENV


def build(venv: Path):
    py = venv / "Scripts" / "python.exe"
    args = [py, "-m", "PyInstaller", "--noconfirm", "--clean"]
    args += ["--onedir", "--windowed", "--name", "MediaDesk"]
    for mod in EXCLUDE_MODULES:
        args += ["--exclude-module", mod]
    if COMPLIANCE.exists():
        args += ["--add-data", f"{COMPLIANCE};docs/compliance"]
    # 品牌 logo：内嵌到资源（源码 _logo_path() 取 _MEIPASS/assets）
    if ASSETS.exists():
        args += ["--add-data", f"{ASSETS};assets"]
    # exe / 文件 / 任务栏图标：多分辨率 logo.ico
    if LOGO_ICO.exists():
        args += ["--icon", str(LOGO_ICO)]
    args.append(str(ROOT / "main.py"))
    _run(args)


def stage_ffmpeg():
    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from fetch_ffmpeg import fetch_ffmpeg
    fetch_ffmpeg(DIST / "ffmpeg" / "bin")
    # 把多分辨率图标复制到产物根，供桌面快捷方式引用
    if LOGO_ICO.exists():
        shutil.copy2(LOGO_ICO, DIST / LOGO_ICO.name)


def measure():
    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"\n产物: {DIST}")
    print(f"体积: {total/1024/1024:.0f} MB")


def main():
    venv = prepare_venv()
    build(venv)
    if "--skip-ffmpeg" not in sys.argv:
        stage_ffmpeg()
    measure()
    print("完成。运行: " + str(DIST / "MediaDesk.exe"))


if __name__ == "__main__":
    main()