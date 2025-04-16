"""
QQ数据缓存
"""
import time
import threading

from ..core import OnebotAPI, ConfigManager
from . import Logger

NotFetched = type("NotFetched", (), {"__getattr__": lambda _, __: NotFetched,
                                     "__repr__": lambda _: "NotFetched",
                                     "__bool__": lambda _: False})
api = OnebotAPI.api
logger = Logger.get_logger()

if ConfigManager.GlobalConfig().qq_data_cache.enable:
    expire_time = ConfigManager.GlobalConfig().qq_data_cache.expire_time
else:
    expire_time = 0


class QQDataItem:
    """
    QQ数据缓存类
    """

    def __init__(self):
        self._data = NotFetched  # 数据
        self.last_update = time.time()  # 最后刷新时间
        self.last_use = -1  # 最后被使用时间（数据被使用）

    def refresh_cache(self):
        """
        刷新缓存
        Returns:
            None
        """
        self.last_update = time.time()


class UserData(QQDataItem):
    """
    QQ用户数据缓存类
    """

    def __init__(
            self,
            user_id: int,
            nickname: str = NotFetched,
            sex: str = NotFetched,
            age: int = NotFetched,
            is_friend: bool = NotFetched,
            remark: str | None = NotFetched  # 此值仅在是好友的时候会存在
    ):
        super().__init__()
        self._user_id = user_id
        self._data = {
            "user_id": user_id,
            "nickname": nickname,
            "sex": sex,
            "age": age,
            "is_friend": is_friend,
            "remark": remark
        }

    def refresh_cache(self):
        """
        刷新缓存
        Returns:
            None
        """
        if int(self._user_id) <= 0:
            logger.warn(f"获取用户{self._user_id}缓存信息失败: user_id小于等于0")
            return
        try:
            data = api.get_stranger_info(self._user_id)
            for k in data:
                self._data[k] = data[k]
            self._data["is_friend"] = NotFetched
            self._data["remark"] = NotFetched
        except Exception as e:
            logger.warn(f"获取用户{self._user_id}缓存信息失败: {repr(e)}")
            return

    def __getattr__(self, item):
        if item == "_data" or item == "data":
            return self._data

        if item in ["remark", "is_friend"] and self._data.get(item) != NotFetched:
            try:
                res = api.get_friend_list()
                for friend in res:
                    if friend["user_id"] == self._user_id:
                        self._data["remark"] = friend["remark"]
                        self._data["is_friend"] = True
                        break
                else:
                    self._data["is_friend"] = False
                    self._data["remark"] = None
            except Exception as e:
                logger.warn(f"获取用户{self._user_id}是否为好友失败: {repr(e)}")
                return None

        if self._data.get(item) == NotFetched or time.time() - self.last_update > expire_time:
            self.refresh_cache()

        if self._data.get(item) == NotFetched:
            return None

        if item in self._data:
            self.last_use = time.time()

        return self._data.get(item)

    def get_nickname(self) -> str:
        """
        获取昵称（如果有备注名优先返回备注名）
        Returns:
            昵称
        """
        return self.remark or self.nickname

    def __repr__(self):
        return f"UserData(user_id={self._user_id})"


class GroupMemberData(QQDataItem):
    """
    QQ群成员数据缓存类
    """

    def __init__(
            self,
            group_id: int,
            user_id: int,
            nickname: str = NotFetched,
            card: str = NotFetched,
            sex: str = NotFetched,
            age: int = NotFetched,
            area: str = NotFetched,
            join_time: int = NotFetched,
            last_sent_time: int = NotFetched,
            level: str = NotFetched,
            role: str = NotFetched,
            unfriendly: bool = NotFetched,
            title: str = NotFetched,
            title_expire_time: int = NotFetched,
            card_changeable: bool = NotFetched,
    ):
        super().__init__()
        self._group_id = group_id
        self._user_id = user_id
        self._data = {
            "group_id": group_id,
            "user_id": user_id,
            "nickname": nickname,
            "card": card,
            "sex": sex,
            "age": age,
            "area": area,
            "join_time": join_time,
            "last_sent_time": last_sent_time,
            "level": level,
            "role": role,
            "unfriendly": unfriendly,
            "title": title,
            "title_expire_time": title_expire_time,
            "card_changeable": card_changeable,
        }

    def refresh_cache(self):
        """
        刷新缓存
        Returns:
            None
        """
        if int(self._group_id) <= 0 or int(self._user_id) <= 0:
            logger.warn(f"获取群{self._group_id}中成员{self._user_id}缓存信息失败: group_id或user_id小于等于0")
            return
        try:
            data = api.get_group_member_info(self._group_id, self._user_id, no_cache=True)
            for k in data:
                self._data[k] = data[k]
        except Exception as e:
            logger.warn(f"获取群{self._group_id}中成员{self._user_id}缓存信息失败: {repr(e)}")
            user_data = get_user_info(self._user_id)
            self._data["nickname"] = user_data.nickname if user_data.nickname else NotFetched
            self._data["sex"] = user_data.sex if user_data.sex else NotFetched
            self._data["age"] = user_data.age if user_data.age else NotFetched
        super().refresh_cache()

    def __getattr__(self, item):
        if item == "_data" or item == "data":
            return self._data

        if self._data.get(item) == NotFetched or time.time() - self.last_update > expire_time:
            self.refresh_cache()

        if self._data.get(item) == NotFetched:
            return None

        if item in self._data:
            self.last_use = time.time()

        return self._data.get(item)

    def __repr__(self):
        return f"GroupMemberData(group_id={self._group_id}, user_id={self._user_id})"

    def get_nickname(self):
        """
        获取群名片（如果有群名片优先返回群名片）
        Returns:
            群名片
        """
        return self.card or self.nickname


class GroupData(QQDataItem):
    """
    QQ群数据缓存类
    """

    def __init__(
            self,
            group_id: int,
            group_name: str = NotFetched,
            member_count: int = NotFetched,
            max_member_count: int = NotFetched
    ):
        super().__init__()
        self._group_id = group_id
        self._data = {
            "group_id": group_id,
            "group_name": group_name,
            "member_count": member_count,
            "max_member_count": max_member_count,
            "group_member_list": NotFetched
        }

    def refresh_cache(self):
        """
        刷新缓存
        Returns:
            None
        """
        if int(self._group_id) <= 0:
            logger.warn(f"获取群{self._group_id}缓存信息失败: group_id小于等于0")
            return
        try:
            data = api.get_group_info(group_id=self._group_id, no_cache=True)
            for k in data:
                self._data[k] = data[k]
            self._data["group_member_list"] = NotFetched
        except Exception as e:
            logger.warn(f"获取群{self._group_id}缓存信息失败: {repr(e)}")
            return
        super().refresh_cache()

    def __getattr__(self, item):
        if item == "_data" or item == "data":
            return self._data

        if item == "group_member_list" and self._data.get(item) == NotFetched:
            try:
                res = api.get_group_member_list(self._group_id)
                member_list = [GroupMemberData(**{k: (v if v is not None else NotFetched)
                                                  for k, v in member.items()})
                               for member in res]
                self._data[item] = member_list
            except Exception as e:
                logger.warn(f"获取群{self._group_id}成员列表信息失败: {repr(e)}")
                return

        if self._data.get(item) == NotFetched or time.time() - self.last_update > expire_time:
            self.refresh_cache()

        if self._data.get(item) == NotFetched:
            return None

        if item in self._data:
            self.last_use = time.time()

        return self._data.get(item)

    def __repr__(self):
        return f"GroupData(group_id={self._group_id})"


group_info = {}
group_member_info = {}
user_info = {}

group_info_lock = threading.Lock()
group_member_info_lock = threading.Lock()
user_info_lock = threading.Lock()

max_cache_size = ConfigManager.GlobalConfig().qq_data_cache.max_cache_size
expire_time = expire_time


def get_user_info(user_id: int, *args, **kwargs) -> UserData:
    """
    获取用户信息
    Args:
        user_id: 用户ID
    Returns:
        None
    """
    with user_info_lock:
        if user_id not in user_info:
            data = UserData(user_id, *args, **kwargs)
            user_info[user_id] = data

        data = user_info[user_id]
        return data


def get_group_info(group_id: int, *args, **kwargs) -> GroupData:
    """
    获取群信息
    Args:
        group_id: 群号
    Returns:
        None
    """
    with group_info_lock:
        if group_id not in group_info:
            data = GroupData(group_id, *args, **kwargs)
            group_info[group_id] = data

        data = group_info[group_id]
        return data


def get_group_member_info(group_id: int, user_id: int, *args, **kwargs) -> GroupMemberData:
    """
    获取群成员信息
    Args:
        group_id: 群号
        user_id: 用户ID
    Returns:
        None
    """
    with group_member_info_lock:
        if group_id not in group_member_info:
            group_member_info[group_id] = {}

        if user_id not in group_member_info[group_id]:
            data = GroupMemberData(group_id, user_id, *args, **kwargs)
            group_member_info[group_id][user_id] = data

        data = group_member_info[group_id][user_id]
        return data


def garbage_collection():
    """
    垃圾回收
    Returns:
        None
    """
    counter = 0

    with group_member_info_lock:
        for k in list(group_member_info.keys()):
            group_member_items = list(zip(group_member_info[k].keys(), group_member_info[k].values()))
            max_last_use_time = max([item[1].last_use for item in group_member_items])

            if max_last_use_time < time.time() - expire_time * 2:
                del group_member_info[k]
                counter += 1
                continue

            group_member_items.sort(key=lambda x: x[1].last_use)
            if len(group_member_items) > max_cache_size * (2 / 3):
                for user_id, _ in group_member_items[:int(max_cache_size * (1 / 3))]:
                    del group_member_info[k][user_id]
                    counter += 1
            del group_member_items, max_last_use_time

    with group_info_lock:
        group_items = list(zip(group_info.keys(), group_info.values()))
        group_items.sort(key=lambda x: x[1].last_use)
        if len(group_items) > max_cache_size * (2 / 3):
            for group_id, _ in group_items[:int(max_cache_size * (1 / 3))]:
                del group_info[group_id]
                counter += 1
        del group_items

    with user_info_lock:
        user_items = list(zip(user_info.keys(), user_info.values()))
        user_items.sort(key=lambda x: x[1].last_use)
        if len(user_items) > max_cache_size * (2 / 3):
            for user_id, _ in user_items[:int(max_cache_size * (1 / 3))]:
                del user_info[user_id]
                counter += 1
        del user_items

    return counter


def scheduled_garbage_collection():
    """
    定时垃圾回收
    Returns:
        None
    """
    t = 0
    while True:
        time.sleep(60)
        t += 1
        if (
                t > 4 or (
                t > 1 and (
                len(group_info) > max_cache_size or
                len(user_info) > max_cache_size or
                len(group_member_info) > max_cache_size
        )
        )
        ):
            t = 0
            logger.debug("QQ数据缓存清理开始...")
            try:
                counter = garbage_collection()
                logger.debug(f"QQ数据缓存清理完成，共清理了 {counter} 项信息。")
            except Exception as e:
                logger.warn(f"QQ数据缓存清理时出现异常: {repr(e)}")


# 启动垃圾回收线程
threading.Thread(target=scheduled_garbage_collection, daemon=True).start()
