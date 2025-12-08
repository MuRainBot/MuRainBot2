"""
状态管理器
注意，数据存储于内存中，重启丢失，需要持久化保存的数据请勿放在里面
"""
from typing import Any, TypedDict

from murainbot.core import PluginManager

states: dict[str, Any] = {}


class PluginMetaDict(TypedDict):
    """
    插件元数据字典
    """
    plugin_data: PluginManager.PluginInfo


class OtherPluginDataDict(TypedDict):
    """
    其他插件数据字典
    """
    plugin_name: str
    meta: PluginMetaDict


class StateDict(TypedDict):
    """
    状态数据字典
    """
    state_id: str
    data: dict
    other_plugin_data: list[OtherPluginDataDict]


def get_state(state_id: str, plugin_data: dict = None) -> StateDict:
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
            "other_plugin_data": [
                {
                    "data": {
                        k1: v1,
                        k2: v2
                    },
                    "meta": {
                        "plugin_data": plugin1_data
                    }
                },
                {
                    "data": {
                        k1: v1,
                        k2: v2
                    },
                    "meta": {
                        "plugin_data": plugin2_data
                    }
                }
            ]
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
        "other_plugin_data": [
            v for k, v in states[state_id].items() if k != plugin_data["path"]
        ]
    }
