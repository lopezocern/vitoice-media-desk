"""一次性生成复选框白色对勾资源（写入 app/assets/check-white.png）。

在开发期运行；生成的 PNG 供 styles.py 的 QSS 以绝对路径引用，
兼容 PyInstaller 冻结态（资源随 _MEIPASS 打入）。
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QGuiApplication

QGuiApplication.instance() or QGuiApplication([])

SIZE = 18  # 与 QCheckBox::indicator 尺寸一致
PM = QPixmap(SIZE, SIZE)
PM.fill(Qt.GlobalColor.transparent)
P = QPainter(PM)
P.setRenderHint(QPainter.RenderHint.Antialiasing, True)
pen = QPen(QColor("#ffffff"), 2.4)
pen.setCapStyle(Qt.PenCapStyle.RoundCap)
pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
P.setPen(pen)
# 白色对勾：从 (4.5,9.5) → (8,13) → (13.5,5.5)
P.drawPolyline([
    QPointF(4.5, 9.6),
    QPointF(8.0, 13.0),
    QPointF(13.6, 5.4),
])
P.end()

OUT = Path(__file__).resolve().parent.parent / "app" / "assets" / "check-white.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
assert PM.save(str(OUT), "PNG"), "保存失败"
print(f"生成 {OUT}")