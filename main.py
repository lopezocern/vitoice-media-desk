"""MediaDesk 媒体工作台 — 桌面客户端入口。"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _apply_light_palette(app: QApplication) -> None:
    """强制浅色调色板：不受系统深色模式影响。

    QSS 只覆盖了显式样式的控件；viewport、消息框、菜单等原生渲染
    仍取 palette。系统深色模式下这些区域会变黑/白字不可见，故整体锁定浅色。
    """
    pal = QPalette()
    c_text = QColor("#1c2333")
    c_sub = QColor("#64748b")
    pal.setColor(QPalette.ColorRole.Window, QColor("#eef1f8"))
    pal.setColor(QPalette.ColorRole.WindowText, c_text)
    pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f9fe"))
    pal.setColor(QPalette.ColorRole.Text, c_text)
    pal.setColor(QPalette.ColorRole.Button, QColor("#f3f5fb"))
    pal.setColor(QPalette.ColorRole.ButtonText, c_text)
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipText, c_text)
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9aa3bd"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#4f5bd5"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.Light, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.Midlight, QColor("#f2f4fb"))
    pal.setColor(QPalette.ColorRole.Mid, QColor("#d3dae8"))
    pal.setColor(QPalette.ColorRole.Dark, QColor("#c3cadb"))
    pal.setColor(QPalette.ColorRole.Shadow, QColor("#aeb7d8"))
    for group in (QPalette.ColorGroup.Disabled,):
        pal.setColor(group, QPalette.ColorRole.Text, QColor("#9aa3bd"))
        pal.setColor(group, QPalette.ColorRole.WindowText, QColor("#9aa3bd"))
        pal.setColor(group, QPalette.ColorRole.ButtonText, QColor("#9aa3bd"))
    app.setPalette(pal)


def main() -> int:
    # Qt6 默认启用 High-DPI 缩放，无需再设置 AA_EnableHighDpiScaling（已弃用）
    app = QApplication(sys.argv)
    app.setApplicationName("MediaDesk")
    app.setOrganizationName("MediaDesk")
    _apply_light_palette(app)

    from app.config import init_env
    from app.state import start_env_probe
    from app.task import TaskPool
    from app.ui.main_window import MainWindow
    from app.ui.styles import QSS

    init_env()
    app.setStyleSheet(QSS)

    win = MainWindow(TaskPool())
    win.show()
    start_env_probe()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
