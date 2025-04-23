#   __  __       ____       _         ____        _   _____
#  |  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_|___  \
#  | |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __| __) |
#  | |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_ / __/
#  |_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|_____|

"""
OnebotAPI
可以方便的调用Onebot的API
"""

import json
import traceback
import urllib.parse
import requests

from . import EventManager, ConfigManager
from ..common import save_exc_dump
from ..utils import Logger

logger = Logger.get_logger()
config = ConfigManager.GlobalConfig()


class CallAPIEvent(EventManager.Event):
    """
    调用API事件
    """
    def __init__(self, full_path, node, data):
        self.full_path: str = full_path
        self.node: str = node
        self.data: dict | None = data


class OnebotAPI:
    """
    OnebotAPI
    """
    def __init__(self, host: str = None, port: int = None,
                 original: bool = False):
        """
        Args:
            host: 调用的ip
            port: 调用的端口
            original: 是否返回全部json（默认只返回data内）
        """
        if host is None:
            host = config.api.host
        if port is None:
            port = config.api.port

        self.host = host
        self.port = port
        self.original = original

    def set_url(self, host: str, port: int):
        """
        设置url
        Args:
            host: 请求的host
            port: 请求的端口
        """
        self.host = host
        self.port = port

    def get(self, node, data: dict = None, original: bool = None):
        """
        调用api
        Args:
            node: 节点
            data: 数据
            original: 是否返回全部json（默认只返回data内）
        """

        if original is None:
            original = self.original

        if node == "":
            raise ValueError('The node cannot be empty.')

        host = self.host
        port = self.port

        if not host:
            raise ValueError('The host cannot be empty.')

        if (not isinstance(port, int)) or port > 65535 or port < 0:
            raise ValueError('The port cannot be empty.')

        if not (host.startswith("http://") or host.startswith("https://")):
            host = "http://" + host

        # 拼接url
        url = urllib.parse.urljoin(host + ":" + str(port), node)

        # 广播call_api事件
        event = CallAPIEvent(url, node, data)
        event.call_async()
        if traceback.extract_stack()[-1].filename == traceback.extract_stack()[-2].filename:
            logger.debug(f"调用 API: {node} data: {data} by: {traceback.extract_stack()[-3].filename}")
        else:
            logger.debug(f"调用 API: {node} data: {data} by: {traceback.extract_stack()[-2].filename}")
        headers = {
                    "Content-Type": "application/json"
        }
        if config.api.access_token:
            headers["Authorization"] = f"Bearer {config.api.access_token}"
        # 发起get请求
        creat_dump = True
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data if data is not None else {})
            )
            if response.status_code != 200 or (response.json()['status'] != 'ok' or response.json()['retcode'] != 0):
                creat_dump = False
                raise Exception(f"返回异常, 状态码: {response.status_code}, 返回内容: {response.text}")

            # 如果original为真，则返回原值和response
            if original:
                return response.json()
            else:
                return response.json()['data']
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump and creat_dump:
                dump_path = save_exc_dump(f"调用 API: {node} data: {data} 异常")
            else:
                dump_path = None
            logger.error(
                f"调用 API: {node} data: {data} 异常: {repr(e)}"
                f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                exc_info=True
            )
            raise e

    def send_private_msg(self, user_id: int, message: str | list[dict]):
        """
        发送私聊消息
        Args:
            user_id: 用户id
            message: 消息内容
        """
        data = {
            "user_id": user_id,
            "message": message
        }
        return self.get("/send_private_msg", data)

    def send_group_msg(self, group_id: int, message: str | list[dict]):
        """
        发送群消息
        Args:
            group_id: 群号
            message: 消息内容
        """
        data = {
            "group_id": group_id,
            "message": message
        }
        return self.get("/send_group_msg", data)

    def send_msg(self, user_id: int = -1, group_id: int = -1, message: str | list[dict] = ""):
        """
        发送消息
        Args:
            user_id: 用户id
            group_id: 群号
            message: 消息内容
        """
        if user_id != -1 and group_id != -1:
            raise ValueError('user_id and group_id cannot be both not -1.')
        if user_id == -1 and group_id == -1:
            raise ValueError('user_id and group_id cannot be both -1.')
        if user_id != -1:
            return self.send_private_msg(user_id, message)
        elif group_id != -1:
            return self.send_group_msg(group_id, message)
        else:
            raise ValueError('user_id and group_id cannot be both -1.')

    def delete_msg(self, message_id: int):
        """
        删除消息
        Args:
            message_id: 消息id
        """
        data = {
            "message_id": message_id
        }
        return self.get("/delete_msg", data)

    def get_msg(self, message_id: int):
        """
        获取消息
        Args:
            message_id: 消息id
        """
        data = {
            "message_id": message_id
        }
        return self.get("/get_msg", data)

    def get_forward_msg(self, id: int):
        """
        获取合并转发消息
        Args:
            id: 合并转发id
        """
        data = {
            "id": id
        }
        return self.get("/get_forward_msg", data)

    def send_like(self, user_id: int, times: int = 1):
        """
        发送点赞
        Args:
            user_id: 用户id
            times: 点赞次数
        """
        data = {
            "user_id": user_id,
            "times": times
        }
        return self.get("/send_like", data)

    def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False):
        """
        群组踢人
        Args:
            group_id: 群号
            user_id: 用户id
            reject_add_request: 拒绝加群请求
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "reject_add_request": reject_add_request
        }
        return self.get("/set_group_kick", data)

    def set_group_ban(self, group_id: int, user_id: int, duration: int = 30 * 60):
        """
        群组单人禁言
        Args:
            group_id: 群号
            user_id: 用户id
            duration: 禁言时长，单位秒，0 表示取消禁言
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "duration": duration
        }
        return self.get("/set_group_ban", data)

    def set_group_anonymous_ban(self, group_id: int, anonymous: dict, duration: int = 30 * 60):
        """
        群组匿名用户禁言
        Args:
            group_id: 群号
            anonymous: 匿名用户对象
            duration: 禁言时长，单位秒，无法取消禁言
        """
        data = {
            "group_id": group_id,
            "anonymous": anonymous,
            "duration": duration
        }
        return self.get("/set_group_anonymous_ban", data)

    def set_group_whole_ban(self, group_id: int, enable: bool = True):
        """
        群组全员禁言
        Args:
            group_id: 群号
            enable: 是否禁言
        """
        data = {
            "group_id": group_id,
            "enable": enable
        }
        return self.get("/set_group_whole_ban", data)

    def set_group_admin(self, group_id: int, user_id: int, enable: bool = True):
        """
        群组设置管理员
        Args:
            group_id: 群号
            user_id: 用户id
            enable: 是否设置管理员
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "enable": enable
        }
        return self.get("/set_group_admin", data)

    def set_group_card(self, group_id: int, user_id: int, card: str = ""):
        """
        设置群名片（群备注）
        Args:
            group_id: 群号
            user_id: 用户id
            card: 群名片内容
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "card": card
        }
        return self.get("/set_group_card", data)

    def set_group_name(self, group_id: int, group_name: str):
        """
        设置群名
        Args:
            group_id: 群号
            group_name: 群名
        """
        data = {
            "group_id": group_id,
            "group_name": group_name
        }
        return self.get("/set_group_name", data)

    def set_group_leave(self, group_id: int, is_dismiss: bool = False):
        """
        Args:
            group_id: 群号
            is_dismiss: 是否解散，如果登录号是群主，则仅在此项为True时能够解散
        """
        data = {
            "group_id": group_id,
            "is_dismiss": is_dismiss
        }
        return self.get("/set_group_leave", data)

    def set_group_special_title(self, group_id: int, user_id: int, special_title: str = "", duration: int = -1):
        """
        设置群组专属头衔
        Args:
            group_id: 群号
            user_id: 要设置的QQ号
            special_title: 专属头衔，不填或空字符串表示删除专属头衔
            duration: 专属头衔有效期，-1表示永久，其他值表示在此时间之前专属头衔会消失
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "special_title": special_title,
        }
        if duration != -1:
            data["duration"] = duration

        return self.get("/set_group_special_title", data)

    def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = ""):
        """
        设置好友添加请求
        Args:
            flag: 请求flag
            approve: 是否同意请求
            remark: 添加后的好友备注
        """
        data = {
            "flag": flag,
            "approve": approve,
            "remark": remark
        }
        return self.get("/set_friend_add_request", data)

    def set_group_add_request(self, flag: str, sub_type: str = "add", approve: bool = True, reason: str = ""):
        """
        设置群添加请求
        Args:
            flag: 请求flag
            sub_type: 添加请求类型，请参考api文档
            approve: 是否同意请求
            reason: 拒绝理由
        """
        data = {
            "flag": flag,
            "sub_type": sub_type,
            "approve": approve,
            "reason": reason
        }
        return self.get("/set_group_add_request", data)

    def get_login_info(self):
        """
        获取登录号信息
        """
        return self.get("/get_login_info")

    def get_stranger_info(self, user_id: int, no_cache: bool = False):
        """
        获取陌生人信息
        Args:
            user_id: 对方QQ号
            no_cache: 是否不使用缓存（使用缓存可能更新不及时，但响应更快）
        """
        data = {
            "user_id": user_id,
            "no_cache": no_cache
        }
        return self.get("/get_stranger_info", data)

    def get_friend_list(self):
        """
        获取好友列表
        """
        return self.get("/get_friend_list")

    def get_group_info(self, group_id: int, no_cache: bool = False):
        """
        获取群信息
        Args:
            group_id: 群号
            no_cache: 是否不使用缓存（使用缓存可能更新不及时，但响应更快）
        """
        data = {
            "group_id": group_id,
            "no_cache": no_cache
        }
        return self.get("/get_group_info", data)

    def get_group_list(self):
        """
        获取群列表
        """
        return self.get("/get_group_list")

    def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False):
        """
        获取群成员信息
        Args:
            group_id: 群号
            user_id: QQ号
            no_cache: 是否不使用缓存（使用缓存可能更新不及时，但响应更快）
        """
        data = {
            "group_id": group_id,
            "user_id": user_id,
            "no_cache": no_cache
        }
        return self.get("/get_group_member_info", data)

    def get_group_member_list(self, group_id: int):
        """
        获取群成员列表
        Args:
            group_id: 群号
        """
        data = {
            "group_id": group_id
        }
        return self.get("/get_group_member_list", data)

    def get_group_honor_info(self, group_id: int, type_: str = "all"):
        """
        获取群荣誉信息
        Args:
            group_id: 群号
            type_: 要获取的群荣誉类型，可传入 talkative performer legend strong_newbie emotion 以分别获取单个类型的群荣誉数据，或传入 all 获取所有数据
        """
        data = {
            "group_id": group_id,
            "type": type_
        }
        return self.get("/get_group_honor_info", data)

    def get_cookies(self):
        """
        获取Cookies
        """
        return self.get("/get_cookies")

    def get_csrf_token(self):
        """
        获取CSRF Token
        """
        return self.get("/get_csrf_token")

    def get_credentials(self):
        """
        获取Credentials
        """
        return self.get("/get_credentials")

    def get_record(self, file: str, out_format: str = "mp3", out_file: str = ""):
        """
        获取语音
        Args:
            file: 文件ID
            out_format: 输出格式，mp3或amr，默认mp3
            out_file: 输出文件名，默认使用文件ID
        """
        data = {
            "file": file,
            "out_format": out_format,
            "out_file": out_file
        }
        return self.get("/get_record", data)

    def get_image(self, file: str):
        """
        获取图片
        Args:
            file: 文件ID
        """
        data = {
            "file": file
        }
        return self.get("/get_image", data)

    def can_send_image(self):
        """
        检查是否可以发送图片
        """
        return self.get("/can_send_image")

    def can_send_record(self):
        """
        检查是否可以发送语音
        """
        return self.get("/can_send_record")

    def get_status(self):
        """
        获取运行状态
        """
        return self.get("/get_status")

    def get_version_info(self):
        """
        获取版本信息
        """
        return self.get("/get_version_info")

    def set_restart(self, delay: int = 0):
        """
        重启OneBot
        Args:
            delay: 延迟时间，单位秒，默认0
        """
        data = {
            "delay": delay
        }
        return self.get("/set_restart", data)

    def clean_cache(self):
        """
        清理缓存
        """
        return self.get("/clean_cache")


api = OnebotAPI()
