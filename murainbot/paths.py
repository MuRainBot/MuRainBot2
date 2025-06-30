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


# 全局变量，在CLI启动时被赋值
paths: PathManager = None


def init_paths(work_path_str: str):
    """
    初始化路径管理器
    Args:
        work_path_str: 工作目录
    """
    global paths
    paths = PathManager(Path(work_path_str))


if os.path.isdir(os.path.join(os.getcwd(), "murainbot")):
    init_paths(os.getcwd())
