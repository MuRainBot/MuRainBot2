"""
配置管理器
"""

import dataclasses
import os
import yaml
from ..paths import *
from ..utils import Logger
from .._defaults import DEFAULT_CONFIG

logger = Logger.get_logger()


class ConfigManager:
    """
    配置管理器
    """
    def __init__(self, config_path, default_config: str | dict = None):
        self.config_path = config_path
        self.default_config = default_config
        self.config = {}
        self.load_config()

    def load_config(self):
        """
        加载配置文件
        Returns:
            None
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"配置文件 {self.config_path} 加载失败，请检查配置文件内容是否正确。"
                             f"如果无法修复，请删除配置文件重新配置，以创建默认配置文件。"
                             f"错误信息：{repr(e)}")
        else:
            try:
                if isinstance(self.default_config, str):
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        f.write(self.default_config)
                        logger.info(f"配置文件 {self.config_path} 不存在，已创建默认配置文件")
                    self.load_config()
                elif isinstance(self.default_config, dict):
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(self.default_config, f)
                        logger.info(f"配置文件 {self.config_path} 不存在，已创建默认配置文件")
                    self.load_config()
                else:
                    logger.error(f"配置文件 {self.config_path} 不存在，且未提供默认配置，无法创建默认配置文件")
                    self.config = {}
            except Exception as e:
                logger.error(f"配置文件 {self.config_path} 创建失败，请检查配置文件路径是否正确。错误信息：{repr(e)}")
                self.config = {}
        self.init()

    def init(self):
        """
        用于初始化配置文件，可自行编写初始化逻辑，例如默认值等
        """
        pass

    def save_config(self):
        """
        保存配置文件
        Returns:
            None
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f)

    def get(self, key, default=None):
        """
        获取配置项
        Args:
            key: 配置项键
            default: 默认值
        Returns:
            配置项值
        """
        return self.config.get(key, default)

    def set(self, key, value):
        """
        设置配置项
        Args:
            key: 配置项键
            value: 配置项值
        Returns:
            None
        """
        self.config[key] = value
        self.init()


class GlobalConfig(ConfigManager):
    """
    MRB2配置管理器
    """
    _instance = None
    _init_flag = False

    @dataclasses.dataclass
    class Account:
        """
        账号相关
        """
        user_id: int
        nick_name: str
        bot_admin: list

    @dataclasses.dataclass
    class Api:
        """
        Api设置
        """
        host: str
        port: int
        access_token: str

    @dataclasses.dataclass
    class Server:
        """
        监听服务器设置
        """
        host: str
        port: int
        server: str
        max_works: int
        secret: str

    @dataclasses.dataclass
    class ThreadPool:
        """
        线程池相关
        """
        max_workers: int

    @dataclasses.dataclass
    class QQDataCache:
        """
        QQ数据缓存设置
        """
        enable: bool
        expire_time: int
        max_cache_size: int

    @dataclasses.dataclass
    class Debug:
        """
        调试模式，若启用框架的日志等级将被设置为debug，不建议在生产环境开启
        """
        enable: bool
        save_dump: bool

    @dataclasses.dataclass
    class AutoRestartOnebot:
        """
        在Onebot实现端状态异常时自动重启Onebot实现端（需开启心跳包）
        """
        enable: bool

    @dataclasses.dataclass
    class Command:
        """
        命令相关
        """
        command_start: list[str]

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.account: GlobalConfig.Account = None
        self.api: GlobalConfig.Api = None
        self.server: GlobalConfig.Server = None
        self.thread_pool: GlobalConfig.ThreadPool = None
        self.qq_data_cache: GlobalConfig.QQDataCache = None
        self.debug: GlobalConfig.Debug = None
        self.auto_restart_onebot: GlobalConfig.AutoRestartOnebot = None
        self.command: GlobalConfig.Command = None
        if not self._init_flag:
            self._init_flag = True
            super().__init__(paths.CONFIG_PATH, DEFAULT_CONFIG)
        else:
            self.init()

    def init(self):
        super().init()
        self.account = self.Account(
            user_id=self.get("account", {}).get("user_id", 0),
            nick_name=self.get("account", {}).get("nick_name", ""),
            bot_admin=self.get("account", {}).get("bot_admin", [])
        )
        self.api = self.Api(
            host=self.get("api", {}).get("host", ""),
            port=self.get("api", {}).get("port", 5700),
            access_token=self.get("api", {}).get("access_token", "")
        )
        self.server = self.Server(
            host=self.get("server", {}).get("host", ""),
            port=self.get("server", {}).get("port", 5701),
            server=self.get("server", {}).get("server", "werkzeug").lower(),
            max_works=self.get("server", {}).get("max_works", 4),
            secret=self.get("server", {}).get("secret", "")
        )
        self.thread_pool = self.ThreadPool(
            max_workers=self.get("thread_pool", {}).get("max_workers", 10)
        )
        self.qq_data_cache = self.QQDataCache(
            enable=self.get("qq_data_cache", {}).get("enable", True),
            expire_time=self.get("qq_data_cache", {}).get("expire_time", 300),
            max_cache_size=self.get("qq_data_cache", {}).get("max_cache_size", 500)
        )
        self.debug = self.Debug(
            enable=self.get("debug", {}).get("enable", False),
            save_dump=self.get("debug", {}).get("save_dump", True)
        )
        self.auto_restart_onebot = self.AutoRestartOnebot(
            enable=self.get("auto_restart_onebot", {}).get("enable", True)
        )
        self.command = self.Command(
            command_start=self.get("command", {}).get("command_start", ["/"])
        )


if __name__ == "__main__":
    test_config = GlobalConfig()
    print(test_config.api)
    test_config.set("api", {"host": "127.0.0.1", "port": 5700})
    print(test_config.api)
