"""
状态管理器
注意，数据存储于内存中，重启丢失，需要持久化保存的数据请勿放在里面
"""
from typing import Any

from murainbot.core import PluginManager

states: dict[str, Any] = {}


def get_state(state_id: str, plugin_data: dict = None):
    """
    获取状态数据
    Args:
        state_id: 状态ID
        plugin_data: 插件数据

    Returns:
        状态数据，结构类似
        {
            "state_id": state_id,
            "data": {
                k1: v1,
                k2: v2
            },
            "other_plugin_data": {
                plugin1_path: {
                    "data": {
                        k1: v1,
                        k2: v2
                    },
                    "meta": {
                        "plugin_data": plugin_data
                    }
                },
                plugin2_path: {
                    "data": {
                        k1: v1,
                        k2: v2
                    },
                    "meta": {
                        "plugin_data": plugin_data
                    }
                }
            }
        }
    """
    if plugin_data is None:
        plugin_data = PluginManager.get_caller_plugin_data()

    plugin_path = plugin_data["path"]

    if state_id not in states:
        states[state_id] = {}

    if plugin_path not in states[state_id]:
        states[state_id][plugin_path] = {
            "data": {},
            "meta": {
                "plugin_data": plugin_data
            }
        }

    return {
        "state_id": state_id,
        "data": states[state_id][plugin_data["path"]]["data"],
        "other_plugin_data": {
            k: v for k, v in states[state_id].items() if k != plugin_data["path"]
        }
    }
