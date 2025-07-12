"""
MRB2示例插件 - 帮助插件
"""


#   __  __       ____       _         ____        _
#  |  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_
#  | |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __|
#  | |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_
#  |_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|

from murainbot import *
from murainbot.core import PluginManager, ConfigManager

logger = Logger.get_logger()

command_start = ConfigManager.GlobalConfig().command.command_start[0]

plugin_info = PluginManager.PluginInfo(
    NAME="Helper",
    AUTHOR="Xiaosu",
    VERSION="1.0.0",
    DESCRIPTION="用于获取插件帮助信息",
    HELP_MSG=f"发送 {command_start}help 或 {command_start}帮助 以获取所有插件的帮助信息"
)


@common.function_cache(1)
def get_help_text():
    """
    获取所有插件的帮助信息
    Returns:
        str: 帮助信息
    """
    plugins = PluginManager.plugins
    text = f"{ConfigManager.GlobalConfig().account.nick_name} 帮助"
    for plugin in plugins:
        try:
            plugin_info = plugin["info"]
            if plugin_info.DESCRIPTION and plugin_info.IS_HIDDEN is False:
                text += f"\n{plugin_info.NAME} - {plugin_info.DESCRIPTION}"
        except Exception as e:
            logger.warning(f"获取插件{plugin['name']}信息时发生错误: {repr(e)}")
    text += f"\n----------\n发送{command_start}help <插件名>或{command_start}帮助 <插件名>以获取插件详细帮助信息"
    return text


matcher = CommandManager.on_command("help", {"帮助"})


@matcher.register_command(f"help {CommandManager.OptionalArg(CommandManager.TextArg("plugin_name"))}")
def on_help(event_data: CommandManager.CommandEvent, plugin_name: str = None):
    """
    帮助命令处理
    """
    if plugin_name is None:
        event_data.reply(get_help_text())
    else:
        plugin_name = plugin_name.lower()
        for plugin in PluginManager.plugins:
            try:
                plugin_info = plugin["info"]
                if plugin_info is None:
                    continue
                if plugin_info.NAME.lower() == plugin_name and plugin_info.IS_HIDDEN is False:
                    event_data.reply(plugin_info.HELP_MSG + f"\n----------\n发送{command_start}help或"
                                                            f"{command_start}帮助以获取全部的插件帮助信息")
                    return
            except Exception as e:
                logger.warning(f"获取插件{plugin['name']}信息时发生错误: {repr(e)}")
                continue
        else:
            event_data.reply("没有找到此插件，请检查是否有拼写错误")
