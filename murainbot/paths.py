"""
MRB2的路径管理
"""
import os
from pathlib import Path


class PathManager:
    """
    路径管理器
    """
    def __init__(self, work_path: Path):
        self.WORK_PATH = work_path
        self.DATA_PATH = self.WORK_PATH / "data"
        self.LOGS_PATH = self.WORK_PATH / "logs"
        self.DUMPS_PATH = self.WORK_PATH / "exc_dumps"
        self.PLUGINS_PATH = self.WORK_PATH / "plugins"
        self.CONFIG_PATH = self.WORK_PATH / "config.yml"
        self.PLUGIN_CONFIGS_PATH = self.WORK_PATH / "plugin_configs"
        self.CACHE_PATH = self.DATA_PATH / "cache"

    def ensure_all_dirs_exist(self):
        """
        确保所有必需的目录都存在
        """
        self.DATA_PATH.mkdir(exist_ok=True)
        self.LOGS_PATH.mkdir(exist_ok=True)
        self.DUMPS_PATH.mkdir(exist_ok=True)
        self.PLUGINS_PATH.mkdir(exist_ok=True)
        self.PLUGIN_CONFIGS_PATH.mkdir(exist_ok=True)
        self.CACHE_PATH.mkdir(exist_ok=True)


class PathManagerProxy:
    """
    路径代理类，会在首次操作时把自己替换掉。
    """

    def __init__(self):
        """
        初始化代理对象，存储初始化 PathManager 所需的 work_path。
        """
        object.__setattr__(self, '_initialized', False)  # 标记是否已初始化真实对象

    def _initialize_and_transform(self):
        """
        这个函数负责初始化真正的 PathManager 实例，并使代理对象“替换掉自己”。
        它通过改变自身的 __class__ 和更新 __dict__ 来实现。
        """
        if object.__getattribute__(self, '_initialized'):
            return  # 已经初始化过了，直接返回

        work_path = os.getcwd()

        print(f"由于Path在未被正常初始化的时候调用，临时初始化，工作目录: {work_path}")

        init_paths(work_path)
        real_instance = paths

        self.__dict__.update(real_instance.__dict__)

        self.__class__ = PathManager

        object.__setattr__(self, '_initialized', True)

    def __getattr__(self, name):
        """
        当访问代理对象上不存在的属性时（包括方法），此方法会被调用。
        它会触发真实 PathManager 对象的初始化。
        """
        # 如果当前对象尚未初始化为 PathManager，则进行初始化和转换
        if not object.__getattribute__(self, '_initialized'):
            self._initialize_and_transform()

        # 此时，self 已经变成了 PathManager 实例，其属性已在 __dict__ 或 PathManager 的方法中
        # 再次尝试从自身获取属性，这次会成功（如果 PathManager 有该属性/方法）
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """
        当设置代理对象的属性时，此方法会被调用。
        它也会触发真实 PathManager 对象的初始化。
        """
        # 如果正在设置代理自身内部的延迟参数或初始化标记，直接通过基类设置，避免递归
        if name in ['_initialized']:
            object.__setattr__(self, name, value)
        else:
            # 否则，表示用户正在操作一个业务属性，触发初始化
            if not object.__getattribute__(self, '_initialized'):
                self._initialize_and_transform()
            # 初始化完成后，通过基类设置属性，因为现在 self 已经是 PathManager
            object.__setattr__(self, name, value)

    def __delattr__(self, name):
        """
        当删除代理对象的属性时，此方法会被调用。
        它也会触发真实 PathManager 对象的初始化。
        """
        if name in ['_initialized']:
            object.__delattr__(self, name)
        else:
            if not object.__getattribute__(self, '_initialized'):
                self._initialize_and_transform()
            object.__delattr__(self, name)


paths: PathManager = PathManagerProxy()


def init_paths(work_path_str: str):
    """
    初始化路径管理器
    Args:
        work_path_str: 工作目录
    """
    global paths
    if isinstance(paths, PathManagerProxy):
        paths = PathManager(Path(work_path_str))


# 如果是 MRB2 开发环境，自动初始化
if os.path.isdir(os.path.join(os.getcwd(), "murainbot")) and os.path.isdir(os.path.join(os.getcwd(), "plugins")):
    init_paths(os.getcwd())
