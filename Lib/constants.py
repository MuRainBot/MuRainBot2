"""
常量
"""
import os

WORK_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(WORK_PATH, "data")
LOGS_PATH = os.path.join(WORK_PATH, "logs")
PLUGINS_PATH = os.path.join(WORK_PATH, "plugins")
CONFIG_PATH = os.path.join(WORK_PATH, "config.yml")
PLUGIN_CONFIGS_PATH = os.path.join(WORK_PATH, "plugin_configs")
CACHE_PATH = os.path.join(DATA_PATH, "cache")
DUMPS_PATH = os.path.join(DATA_PATH, "exc_dumps")

if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

if not os.path.exists(PLUGIN_CONFIGS_PATH):
    os.makedirs(PLUGIN_CONFIGS_PATH)

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

if not os.path.exists(LOGS_PATH):
    os.makedirs(LOGS_PATH)
