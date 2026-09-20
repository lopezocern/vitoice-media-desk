"""应用级共享状态：环境探测结果在多个页面间复用。

MainWindow 在后台探测后填充 AppState.env 并触发 env_changed，任何页面 connect 后刷新。
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class _EnvState(QObject):
    env_changed = Signal()  # 完成后带 probe 结果

    def __init__(self) -> None:
        super().__init__()
        self.env = None  # EnvProbe 占位，探测完成后填充


state = _EnvState()


def start_env_probe() -> None:
    """后台线程执行环境探测，完成后填充 state.env 并广播 env_changed。"""
    import threading

    from . import env as env_mod

    def work():
        probe = env_mod.probe_env()
        state.env = probe
        state.env_changed.emit()

    threading.Thread(target=work, daemon=True).start()