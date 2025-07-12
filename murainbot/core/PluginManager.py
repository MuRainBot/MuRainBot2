"""
插件管理器
"""

import dataclasses
import importlib
import inspect
import os
import sys
from types import ModuleType
from typing import TypedDict

from murainbot.common import save_exc_dump
from murainbot.paths import paths
from murainbot.core import ConfigManager
from murainbot.utils.Logger import get_logger

logger = get_logger()


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
        if not self.ENABLED:
            raise NotEnabledPluginException
        if self.extra is None:
            self.extra = {}


class PluginDict(TypedDict):
    """
    插件信息字典
    """
    name: str
    plugin: ModuleType | None
    info: PluginInfo | None
    file_path: str
    path: str


plugins: list[PluginDict] = []
found_plugins: list[PluginDict] = []


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
    full_path = plugin["path"]
    is_package = os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "__init__.py"))

    # 计算导入路径
    # 获取相对于 WORK_PATH 的路径，例如 "plugins/AIChat" 或 "plugins/single_file_plugin.py"
    relative_plugin_path = os.path.relpath(full_path, start=paths.WORK_PATH)

    # 将路径分隔符替换为点，例如 "plugins.AIChat" 或 "plugins.single_file_plugin"
    import_path = relative_plugin_path.replace(os.sep, '.')
    if not is_package and import_path.endswith('.py'):
        import_path = import_path[:-3]  # 去掉 .py 后缀

    logger.debug(f"计算 {name} 得到的导入路径: {import_path}")

    try:
        logger.debug(f"尝试加载: {import_path}")
        module = importlib.import_module(import_path)
    except ImportError as e:
        logger.error(f"加载 {import_path} 失败: {repr(e)}", exc_info=True)
        raise

    plugin_info = None
    try:
        if isinstance(module.plugin_info, PluginInfo):
            plugin_info = module.plugin_info
        else:
            logger.warning(f"插件 {name} 的 plugin_info 并非 PluginInfo 类型，无法获取插件信息")
    except AttributeError:
        logger.warning(f"插件 {name} 未定义 plugin_info 属性，无法获取插件信息")

    return module, plugin_info


def load_plugins():
    """
    加载插件
    """
    global plugins, found_plugins

    work_dir_str = str(paths.WORK_PATH.resolve())
    if work_dir_str not in sys.path:
        logger.debug(f"将项目工作目录 '{work_dir_str}' 添加到 sys.path。")
        sys.path.insert(0, work_dir_str)

    found_plugins = []
    # 获取插件目录下的所有文件
    for plugin in os.listdir(paths.PLUGINS_PATH):
        if plugin == "__pycache__":
            continue
        full_path = os.path.join(paths.PLUGINS_PATH, plugin)
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
            logger.error(f"尝试加载插件 {full_path} 时失败！ 原因:{repr(e)}"
                         f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                         exc_info=True)
            continue

        logger.debug(f"插件 {name}({full_path}) 加载成功！")


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
                    logger.error(f"尝试加载被依赖的插件 {plugin_name} 时失败！ 原因:{repr(e)}"
                                 f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                                 exc_info=True)
                    raise e
                logger.debug(f"由于插件依赖，插件 {plugin_name} 加载成功！")
            else:
                logger.debug(f"由于插件依赖，插件 {plugin_name} 已被加载，跳过加载")
            return plugin
    else:
        raise FileNotFoundError(f"插件 {plugin_name} 不存在或不符合要求，无法加载依赖")


def get_caller_plugin_data(ignore_self=False):
    """
    获取调用者的插件数据
    Args:
         ignore_self: bool，是否忽略第一个是插件调用者
    Returns:
        plugin_data: dict | None
    """

    skip_self_flag = None if ignore_self else True

    stack = inspect.stack()[1:]
    for frame_info in stack:
        filename = frame_info.filename

        normalized_filename = os.path.normpath(filename)
        normalized_plugins_path = os.path.normpath(paths.PLUGINS_PATH)

        if normalized_filename.startswith(normalized_plugins_path):
            for plugin in found_plugins:
                normalized_plugin_file_path = os.path.normpath(plugin["file_path"])
                plugin_dir, plugin_file = os.path.split(normalized_plugin_file_path)

                if plugin_dir == normalized_plugins_path:
                    if normalized_plugin_file_path != normalized_filename:
                        continue
                else:
                    if not normalized_filename.startswith(plugin_dir):
                        continue
                if skip_self_flag is None:
                    skip_self_flag = plugin
                else:
                    if plugin != skip_self_flag:
                        return plugin
    return None
