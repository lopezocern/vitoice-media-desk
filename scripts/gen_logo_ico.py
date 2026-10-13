"""从品牌 logo 生成多分辨率 ico（16/24/32/48/64/128/256），供 exe/文件/任务栏图标使用。

压缩使用 PNG 存储（Vista+ 均支持 PNG-in-ICO），逐尺寸平滑缩放保留品牌 V 图形。
"""
from __future__ import annotations

import struct
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "assets" / "logo.png"
OUT_ICO = ROOT / "app" / "assets" / "logo.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def write_ico(pngs: list[bytes], path: Path) -> None:
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = bytearray()
    for png in pngs:
        entries += struct.pack("<BBBBHHII", 0, 0, 0, 0, 0, 32, len(png), offset)
        offset += len(png)
    path.write_bytes(header + bytes(entries) + b"".join(pngs))


def png_bytes(img) -> bytes:
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImageWriter

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    w = QImageWriter(buf, b"png")
    w.write(img)
    buf.close()
    return bytes(buf.data())


def main() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QPixmap

    if not SRC.exists():
        print(f"缺少源 logo: {SRC}")
        sys.exit(1)
    app = QGuiApplication([])
    src = QPixmap(str(SRC))
    if src.isNull():
        print(f"logo 解析失败: {SRC}")
        sys.exit(1)

    # 居中裁成正方形（图标容器须正方）
    edge = min(src.width(), src.height())
    src = src.copy((src.width() - edge) // 2, (src.height() - edge) // 2, edge, edge)

    pngs = [
        png_bytes(src.scaled(s, s, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation).toImage())
        for s in SIZES
    ]
    write_ico(pngs, OUT_ICO)
    print(f"已生成 {OUT_ICO}（尺寸 {SIZES}）")


if __name__ == "__main__":
    main()