"""
插件配置管理
"""

import inspect

from Lib.core import ConfigManager, PluginManager
from Lib.constants import *


class PluginConfig(ConfigManager.ConfigManager):
    """
    插件配置管理
    """
    def __init__(
            self,
            plugin_name: str = None,
            default_config: str | dict = None
    ):
        """
        Args:
            plugin_name: 插件名称，留空自动获取
            default_config: 默认配置，选填
        """
        if plugin_name is None:
            stack = inspect.stack()
            stack.reverse()
            while stack:
                frame, filename, line_number, function_name, lines, index = stack.pop(0)
                if filename.startswith(PLUGINS_PATH):
                    for plugin in PluginManager.plugins:
                        head, tail = os.path.split(plugin["file_path"])
                        if head == PLUGINS_PATH:
                            # 是文件类型的插件
                            if plugin["file_path"] == filename:
                                plugin_name = plugin["name"]
                        else:
                            # 是库类型的插件
                            if filename.startswith(os.path.split(plugin["file_path"])[0]):
                                plugin_name = plugin["name"]
        super().__init__(os.path.join(PLUGIN_CONFIGS_PATH, f"{plugin_name}.yml"), default_config)
        self.plugin_name = plugin_name
