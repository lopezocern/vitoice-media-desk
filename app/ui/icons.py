"""内联线性图标：用 QPainter 手绘，随主题与选中态换色。

不依赖 QtSvg / 外部图标文件，绿色版打包零额外运行时插件。
每个图标返回 QIcon，`brand=True` 时用品牌色（用于侧栏选中态）。

高 DPI：不再只渲染一张 18px 位图再让 Qt 放大插值。改为按
「应用内请求的逻辑尺寸（16/18）× 常见缩放比（1.0~3.0）」预渲染
多档物理像素，QIcon 按当前屏 DPR 直接命中同像素量的图，
100% / 125% / 150% / 200% / 250% / 300% 下都是原生清晰度。
"""
from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_S = 18                                   # 绘图坐标系基准画布（逻辑单位）
_LOGICAL = (16, 18)                       # 应用内实际请求的图标尺寸
_DPRS = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0)   # 常见屏幕缩放比
_PHYS = sorted({max(1, round(n * d)) for n in _LOGICAL for d in _DPRS})

_BRAND = QColor("#4f5bd5")
_NORMAL = QColor("#454f66")  # 与侧栏导航文字 #3a4256 更接近，视觉统一


def _pixmap(fn, color: str, phys: int) -> QPixmap:
    """按物理像素 phys 绘制，内部坐标系始终是 18×18。"""
    pm = QPixmap(phys, phys)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    k = phys / _S
    p.scale(k, k)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    fn(p)
    p.end()
    return pm


@lru_cache(maxsize=64)
def _render(fn, color: str) -> QIcon:
    """多档位 QIcon；缓存避免每次切页/重绘都重画全部图标。"""
    icon = QIcon()
    for phys in _PHYS:
        icon.addPixmap(_pixmap(fn, color, phys))
    return icon


def nav_icon(kind: str, brand: bool = False) -> QIcon:
    color = _BRAND if brand else _NORMAL
    return _render(_DRAWERS[kind], color.name())


def window_icon(kind: str) -> QIcon:
    return _render(_WINDOW.get(kind, _wd.menu), "#3a4256")


class _draw:
    """每个方法：用给定 QPainter 画一个 18px 线性图标（内容区约 2~16）。"""

    @staticmethod
    def overview(p: QPainter) -> None:
        p.drawRoundedRect(QRectF(2, 2, 5.6, 5.6), 1.4, 1.4)
        p.drawRoundedRect(QRectF(10.4, 2, 5.6, 5.6), 1.4, 1.4)
        p.drawRoundedRect(QRectF(2, 10.4, 5.6, 5.6), 1.4, 1.4)
        p.drawRoundedRect(QRectF(10.4, 10.4, 5.6, 5.6), 1.4, 1.4)

    @staticmethod
    def compress(p: QPainter) -> None:
        p.drawRoundedRect(QRectF(1.8, 3, 14.4, 12), 3, 3)
        tri = QPainterPath()
        tri.moveTo(6.8, 5.8)
        tri.lineTo(13.4, 9)
        tri.lineTo(6.8, 12.2)
        tri.closeSubpath()
        brush = QColor(p.pen().color())
        p.setBrush(brush)
        p.drawPath(tri)

    @staticmethod
    def cut(p: QPainter) -> None:
        p.drawLine(QPointF(3.5, 4.5), QPointF(13.5, 12.5))
        p.drawLine(QPointF(3.5, 12.5), QPointF(13.5, 4.5))
        p.drawEllipse(QPointF(4.6, 4.0), 1.5, 1.5)
        p.drawEllipse(QPointF(4.6, 13.2), 1.5, 1.5)

    @staticmethod
    def concat(p: QPainter) -> None:
        p.drawLine(QPointF(2, 9), QPointF(11, 9))
        p.drawLine(QPointF(16, 9), QPointF(9, 9))
        p.drawLine(QPointF(4, 6), QPointF(2, 9))
        p.drawLine(QPointF(4, 12), QPointF(2, 9))
        p.drawLine(QPointF(14, 6), QPointF(16, 9))
        p.drawLine(QPointF(14, 12), QPointF(16, 9))

    @staticmethod
    def convert(p: QPainter) -> None:
        cx, cy, r = 9, 9, 6.4
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 30 * 16, 300 * 16)
        bx = cx + r * math.cos(math.radians(30))
        by = cy - r * math.sin(math.radians(30))
        p.drawLine(QPointF(bx, by), QPointF(bx + 2.4, by - 1.4))
        p.drawLine(QPointF(bx, by), QPointF(bx + 1.8, by + 1.9))

    @staticmethod
    def rename(p: QPainter) -> None:
        p.drawRoundedRect(QRectF(2, 4, 14, 11), 2, 2)
        path = QPainterPath(QPointF(2, 8))
        path.lineTo(6.4, 8.2)
        path.lineTo(8, 10)
        path.lineTo(16, 10.2)
        path.lineTo(16, 8)
        p.drawPath(path)

    @staticmethod
    def settings(p: QPainter) -> None:
        p.drawEllipse(QPointF(9, 9), 2.6, 2.6)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            x0 = 9 + math.cos(rad) * 5
            y0 = 9 + math.sin(rad) * 5
            x1 = 9 + math.cos(rad) * 7.2
            y1 = 9 + math.sin(rad) * 7.2
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


_DRAWERS = {
    "overview": _draw.overview,
    "compress": _draw.compress,
    "cut": _draw.cut,
    "concat": _draw.concat,
    "convert": _draw.convert,
    "rename": _draw.rename,
    "settings": _draw.settings,
}


class _wd:
    """标题栏控制 / 折叠按钮的线性图标（18px 画布）。"""

    @staticmethod
    def menu(p: QPainter) -> None:
        for y in (6.2, 9, 11.8):
            p.drawLine(QPointF(2, y), QPointF(16, y))

    @staticmethod
    def min(p: QPainter) -> None:
        p.drawLine(QPointF(3, 13.2), QPointF(15, 13.2))

    @staticmethod
    def max(p: QPainter) -> None:
        p.drawRoundedRect(QRectF(3.6, 3.6, 10.8, 10.8), 1.5, 1.5)

    @staticmethod
    def restore(p: QPainter) -> None:
        p.drawRoundedRect(QRectF(3.4, 6, 8.6, 8.6), 1.4, 1.4)
        p.drawRoundedRect(QRectF(6.2, 3.4, 8.6, 8.6), 1.4, 1.4)

    @staticmethod
    def close(p: QPainter) -> None:
        p.drawLine(QPointF(5, 5), QPointF(13, 13))
        p.drawLine(QPointF(13, 5), QPointF(5, 13))


_WINDOW = {
    "menu": _wd.menu,
    "min": _wd.min,
    "max": _wd.max,
    "restore": _wd.restore,
    "close": _wd.close,
}