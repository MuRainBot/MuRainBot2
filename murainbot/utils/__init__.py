"""
MRB2 Lib 工具模块
"""

import importlib
from typing import TYPE_CHECKING


__all__ = [
    "Logger",
    "QQRichText",
    "Actions",
    "AutoRestartOnebot",
    "CommandManager",
    "EventClassifier",
    "EventHandlers",
    "PluginConfig",
    "QQDataCacher",
    "StateManager",
]


if TYPE_CHECKING:
    from . import Logger
    from . import EventClassifier
    from . import StateManager
    from . import QQRichText
    from . import QQDataCacher
    from . import Actions
    from . import EventHandlers
    from . import AutoRestartOnebot
    from . import PluginConfig
    from . import CommandManager


def __getattr__(name: str):
    """当访问 murainbot.name 时，按需导入并返回。"""
    if name in __all__:
        module = importlib.import_module(f".{name}", __name__)
        return getattr(module, name)

    # 如果找不到，抛出标准的 AttributeError
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """让 dir(murainbot) 和 tab 自动补全能正常工作。"""
    return list(__all__)
