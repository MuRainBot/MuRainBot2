"""
插件管理器
"""

import dataclasses
import importlib
import sys
import traceback

from Lib.common import save_exc_dump
from Lib.constants import *
from Lib.core import ConfigManager
from Lib.core.EventManager import event_listener
from Lib.core.ListenerServer import EscalationEvent
from Lib.utils.Logger import get_logger

logger = get_logger()

plugins: list[dict] = []
found_plugins: list[dict] = []
has_main_func_plugins: list[dict] = []

if not os.path.exists(PLUGINS_PATH):
    os.makedirs(PLUGINS_PATH)


class NotEnabledPluginException(Exception):
    """
    插件未启用的异常
    """
    pass


def load_plugin(plugin):
    """
    加载插件
    Args:
        plugin: 插件信息
    """
    name = plugin["name"]
    file_path = plugin["file_path"]

    # 创建模块规范
    spec = importlib.util.spec_from_file_location(name, file_path)

    # 创建新模块
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    plugin_info = None
    try:
        if isinstance(module.plugin_info, PluginInfo):
            plugin_info = module.plugin_info
        else:
            logger.warning(f"插件 {name} 的 plugin_info 并非 PluginInfo 类型，无法获取插件信息")
    except AttributeError:
        logger.warning(f"插件 {name} 未定义 plugin_info 属性，无法获取插件信息")

    # 获取相对路径
    relative_path = os.path.relpath(plugin["path"], start=WORK_PATH)

    # 替换文件分隔符为点
    relative_path = relative_path.replace(os.sep, '.')

    # 去除最后的 .py 后缀
    if relative_path.endswith('.py'):
        relative_path = relative_path[:-3]  # 去掉 .py

    # 将模块添加到sys.modules内
    sys.modules[relative_path] = module

    return module, plugin_info


def load_plugins():
    """
    加载插件
    """
    global plugins, found_plugins

    found_plugins = []
    # 获取插件目录下的所有文件
    for plugin in os.listdir(PLUGINS_PATH):
        if plugin == "__pycache__":
            continue
        full_path = os.path.join(PLUGINS_PATH, plugin)
        if (
                os.path.isdir(full_path) and
                os.path.exists(os.path.join(full_path, "__init__.py")) and
                os.path.isfile(os.path.join(full_path, "__init__.py"))
        ):
            file_path = os.path.join(os.path.join(full_path, "__init__.py"))
            name = plugin
        elif os.path.isfile(full_path) and full_path.endswith(".py"):
            file_path = full_path
            name = os.path.split(file_path)[1]
        else:
            logger.warning(f"{full_path} 不是一个有效的插件")
            continue
        logger.debug(f"找到插件 {file_path} 待加载")
        plugin = {"name": name, "plugin": None, "info": None, "file_path": file_path, "path": full_path}
        found_plugins.append(plugin)

    plugins = []

    for plugin in found_plugins:
        name = plugin["name"]
        full_path = plugin["path"]

        if plugin["plugin"] is not None:
            # 由于其他原因已被加载（例如插件依赖）
            logger.debug(f"插件 {name} 已被加载，跳过加载")
            continue

        logger.debug(f"开始尝试加载插件 {full_path}")

        try:
            module, plugin_info = load_plugin(plugin)

            plugin["info"] = plugin_info
            plugin["plugin"] = module
            plugins.append(plugin)
        except NotEnabledPluginException:
            logger.warning(f"插件 {name}({full_path}) 已被禁用，将不会被加载")
            continue
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"尝试加载插件 {full_path} 时失败")
            else:
                dump_path = None
            logger.error(f"尝试加载插件 {full_path} 时失败！ 原因:{repr(e)}\n"
                         f"{"".join(traceback.format_exc())}"
                         f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}")
            continue

        logger.debug(f"插件 {name}({full_path}) 加载成功！")


@dataclasses.dataclass
class PluginInfo:
    """
    插件信息
    """
    NAME: str  # 插件名称
    AUTHOR: str  # 插件作者
    VERSION: str  # 插件版本
    DESCRIPTION: str  # 插件描述
    HELP_MSG: str  # 插件帮助
    ENABLED: bool = True  # 插件是否启用
    IS_HIDDEN: bool = False  # 插件是否隐藏（在/help命令中）
    extra: dict | None = None  # 一个字典，可以用于存储任意信息。其他插件可以通过约定 extra 字典的键名来达成收集某些特殊信息的目的。

    def __post_init__(self):
        if self.ENABLED is not True:
            raise NotEnabledPluginException
        if self.extra is None:
            self.extra = {}


def requirement_plugin(plugin_name: str):
    """
    插件依赖
    Args:
        plugin_name: 插件的名称，如果依赖的是库形式的插件则是库文件夹的名称，如果依赖的是文件形式则是插件文件的名称（文件名称包含后缀）

    Returns:
        依赖的插件的信息
    """
    logger.debug(f"由于插件依赖，正在尝试加载插件 {plugin_name}")
    for plugin in found_plugins:
        if plugin["name"] == plugin_name:
            if plugin not in plugins:
                try:
                    module, plugin_info = load_plugin(plugin)
                    plugin["info"] = plugin_info
                    plugin["plugin"] = module
                    plugins.append(plugin)
                except NotEnabledPluginException:
                    logger.error(f"被依赖的插件 {plugin_name} 已被禁用，无法加载依赖")
                    raise Exception(f"被依赖的插件 {plugin_name} 已被禁用，无法加载依赖")
                except Exception as e:
                    if ConfigManager.GlobalConfig().debug.save_dump:
                        dump_path = save_exc_dump(f"尝试加载被依赖的插件 {plugin_name} 时失败！")
                    else:
                        dump_path = None
                    logger.error(f"尝试加载被依赖的插件 {plugin_name} 时失败！ 原因:{repr(e)}\n"
                                 f"{"".join(traceback.format_exc())}"
                                 f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}")
                    raise e
                logger.debug(f"由于插件依赖，插件 {plugin_name} 加载成功！")
            else:
                logger.debug(f"由于插件依赖，插件 {plugin_name} 已被加载，跳过加载")
            return plugin
    else:
        raise FileNotFoundError(f"插件 {plugin_name} 不存在或不符合要求，无法加载依赖")


# 该方法已被弃用
def run_plugin_main(event_data):
    """
    运行插件的main函数
    Args:
        event_data: 事件数据
    """
    global has_main_func_plugins
    for plugin in has_main_func_plugins:
        logger.debug(f"执行插件: {plugin['name']}")
        try:
            plugin["plugin"].main(event_data, WORK_PATH)
        except Exception as e:
            logger.error(f"执行插件{plugin['name']}时发生错误: {repr(e)}")
            continue


@event_listener(EscalationEvent)
def run_plugin_main_wrapper(event):
    """
    运行插件的main函数
    Args:
        event: 事件
    """
    run_plugin_main(event.event_data)
