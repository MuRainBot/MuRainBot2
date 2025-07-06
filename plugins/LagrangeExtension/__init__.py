#   __  __       ____       _         ____        _
#  |  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_
#  | |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __|
#  | |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_
#  |_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|

"""
Lagrange实现端扩展插件
可能更新不及时，如果有偏差请再issue内告诉我或者直接跟我提pr
"""

from murainbot.core import PluginManager

plugin_info = PluginManager.PluginInfo(
    NAME="LagrangeExtension",
    AUTHOR="Xiaosu",
    VERSION="1.0.0",
    DESCRIPTION="用于支持一些Lagrange扩展的消息段和操作",
    HELP_MSG="",
    IS_HIDDEN=True
)


from plugins.LagrangeExtension import Actions, Segments, Events
