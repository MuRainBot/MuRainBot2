"""
插件配置管理
"""

import os

from murainbot.core import ConfigManager, PluginManager
from murainbot.paths import paths


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
            plugin = PluginManager.get_caller_plugin_data()
            plugin_name = plugin["name"]
        super().__init__(os.path.join(paths.PLUGIN_CONFIGS_PATH, f"{plugin_name}.yml"), default_config)
        self.plugin_name = plugin_name
