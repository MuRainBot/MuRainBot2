"""
MRB2 Lib
"""
from typing import TYPE_CHECKING
import importlib

if TYPE_CHECKING:
    from .utils import *
    from . import common
    from . import core
else:
    def __getattr__(name: str):
        """当访问 murainbot.name 时，按需导入并返回。"""
        if name in __all__:
            module_name = f".utils.{name}"
            if name == "common":
                module_name = ".common"
            elif name.startswith("core."):
                module_name = f".{name}"
            # print(module_name)
            module = importlib.import_module(module_name, __name__)
            return module

        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


    def __dir__():
        """让 dir(murainbot) 和 tab 自动补全能正常工作。"""
        return list(__all__)


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
    "TimerManager",
    "SessionManager",
    "common",
    "core"
]
