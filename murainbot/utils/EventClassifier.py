"""
事件分发器
"""

from typing import TypedDict, NotRequired, Literal

from ..core import EventManager, ListenerServer
from . import QQRichText, QQDataCacher, Logger

logger = Logger.get_logger()


class Event(EventManager.Event):
    """
    事件类
    """

    def __init__(self, event_data):
        self.event_data: dict = event_data
        self.time: int = self["time"]
        self.self_id: int = self["self_id"]
        self.post_type: str = self["post_type"]

    def __getitem__(self, item):
        if item not in self.event_data:
            raise KeyError(f"{item} not in {self.event_data}")
        return self.event_data.get(item)

    def get(self, key, default=None):
        """
        获取事件数据
        Args:
            key: 键
            default: 默认值
        Returns:
            None
        """
        return self.event_data.get(key, default)

    def __contains__(self, other):
        return other in self.event_data

    def __repr__(self):
        return str(self.event_data)

    def logger(self):
        """
        发送事件日志
        """
        return False


class EventData(TypedDict):
    """
    事件数据
    """
    cls: Event
    post_type: str
    rules: dict


events: list[EventData] = []


def register_event(post_type: str, **other_rules):
    """
    注册事件
    Args:
        post_type: 事件类型
        other_rules: 其他规则
    Returns:
        None
    """

    def decorator(cls):
        """
        Args:
            @param cls:
        Returns:
            None
        """
        data: EventData = {
            "cls": cls,
            "post_type": post_type,
            "rules": other_rules
        }
        events.append(data)
        return cls

    return decorator


class SenderDict(TypedDict, total=False):
    """
    发送者数据
    """
    user_id: NotRequired[int]
    nickname: NotRequired[str]
    sex: NotRequired[Literal["male", "female", "unknown"]]
    age: NotRequired[int]


class PrivateDict(TypedDict, total=False):
    """
    私聊发送者数据
    """
    user_id: NotRequired[int]
    nickname: NotRequired[str]
    sex: NotRequired[Literal["male", "female", "unknown"]]
    age: NotRequired[int]


class GroupSenderDict(TypedDict, total=False):
    """
    群聊发送者数据
    """
    user_id: NotRequired[int]
    nickname: NotRequired[str]
    card: NotRequired[str]
    sex: NotRequired[Literal["male", "female", "unknown"]]
    age: NotRequired[int]
    level: NotRequired[int]
    role: NotRequired[Literal["owner", "admin", "member"]]
    title: NotRequired[str]


# 注册事件类
@register_event("message")
class MessageEvent(Event):
    """
    消息事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.message_type = self["message_type"]
        self.user_id: int = int(self["user_id"])
        self.sub_type: str = self["sub_type"]
        self.message: QQRichText.QQRichText = QQRichText.QQRichText(self["message"])
        self.raw_message: str = self["raw_message"]
        self.message_id: int = int(self["message_id"])
        self.sender: SenderDict = self["sender"]

    @property
    def is_group(self) -> bool:
        """
        判断是否为群聊消息
        """
        return self.message_type == "group"

    @property
    def is_private(self) -> bool:
        """
        判断是否为私聊消息
        """
        return self.message_type == "private"


@register_event("message", message_type="private")
class PrivateMessageEvent(MessageEvent):
    """
    私聊消息事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.sender: PrivateDict = self["sender"]

    @property
    def is_from_friend(self) -> bool:
        """
        判断是否为好友消息
        """
        return self.sub_type == "friend"

    @property
    def is_from_group_temp(self) -> bool:
        """
        判断是否为群临时会话
        """
        return self.sub_type == "group"

    def logger(self):
        if self.sub_type == "friend":
            logger.info(
                f"收到来自好友 "
                f"{QQDataCacher.get_user_info(
                    self.user_id,
                    is_friend=True,
                    **{k: v for k, v in self.sender.items() if k not in ['user_id']}
                ).nickname}"
                f"({self.user_id}) "
                f"的消息: "
                f"{self.message.render()}"
                f"({self.message_id})"
            )
            return None

        elif self.sub_type == "group":
            logger.info(
                f"收到来自群 "
                f"{QQDataCacher.get_group_info(self.get('group_id')).group_name}"
                f"({self.get('group_id')})"
                f" 内成员 "
                f"{QQDataCacher.get_group_member_info(
                    self.get('group_id'), self.user_id,
                    **{k: v for k, v in self.sender.items() if k not in ['group_id', 'user_id']}
                ).get_nickname()}"
                f"({self.user_id}) "
                f"的群临时会话消息: "
                f"{self.message.render()}"
                f"({self.message_id})"
            )
            return None

        elif self.sub_type == "other":
            logger.info(
                f"收到来自 "
                f"{QQDataCacher.get_user_info(
                    self.user_id,
                    **{k: v for k, v in self.sender.items() if k not in ['user_id']}
                ).nickname}"
                f"({self.user_id}) "
                f"的消息: "
                f"{self.message.render()}"
                f"({self.message_id})"
            )
            return None

        else:
            return super().logger()


@register_event("message", message_type="group")
class GroupMessageEvent(MessageEvent):
    """
    群聊消息事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.sender: GroupSenderDict = self["sender"]

    @property
    def is_normal(self) -> bool:
        """
        判断是否为普通消息
        """
        return self.sub_type == "normal"

    @property
    def is_anonymous(self) -> bool:
        """
        判断是否为匿名消息
        """
        return self.sub_type == "anonymous"

    @property
    def is_from_owner(self) -> bool:
        """
        判断消息是否由群主发送
        """
        return self.sender.get("role") == "owner"

    @property
    def is_from_admin(self) -> bool:
        """
        判断消息是否由管理员发送
        """
        return self.sender.get("role") == "admin"

    def is_at_me(self) -> bool:
        """
        判断消息是否@了机器人
        """
        # 此处假设 self.message.segments 是一个包含消息段的列表
        # 且 @ 消息段的格式为 {'type': 'at', 'data': {'qq': '被@的QQ号'}}
        for segment in self.message.segments:
            if segment.get("type") == "at" and segment.get("data", {}).get("qq") == str(self.self_id):
                return True
        return False

    def logger(self):
        if self.sub_type == "normal":
            logger.info(
                f"收到来自群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id})"
                f" 内成员 "
                f"{QQDataCacher.get_group_member_info(
                    self.group_id, self.user_id,
                    **{k: v for k, v in self.sender.items()
                       if k not in ['group_id', 'user_id']}).get_nickname()}"
                f"({self.user_id}) "
                f"的消息: "
                f"{self.message.render(group_id=self.group_id)}"
                f"({self.message_id})"
            )
            return None

        elif self.sub_type == "anonymous":
            anonymous_data = self.get('anonymous', {})
            anonymous_str = f"{QQDataCacher.get_user_info(anonymous_data['id']).nickname}" \
                if anonymous_data else "匿名用户"
            anonymous_detail = f"({anonymous_data['id']}; flag: {anonymous_data['flag']})" if anonymous_data else ""
            logger.info(
                f"收到来自群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id})"
                f" 内 {anonymous_str}{anonymous_detail} "
                f"的匿名消息: "
                f"{self.message.render(group_id=self.group_id)}"
                f"({self.message_id})"
            )
            return None

        elif self.sub_type == "notice":
            logger.info(
                f"收到来自群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id}) "
                f"内的系统消息: "
                f"{self.message.render(group_id=self.group_id)}"
                f"({self.message_id})"
            )
            return None

        else:
            return super().logger()


@register_event("notice")
class NoticeEvent(Event):
    """
    通知事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.notice_type: str = self["notice_type"]


class FileDict(TypedDict, total=False):
    """
    文件数据
    """
    id: str
    name: str
    size: int
    busid: int


@register_event("notice", notice_type="group_upload")
class GroupUploadEvent(NoticeEvent):
    """
    群文件上传事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.file: FileDict = self["file"]

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内成员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()} "
            f"({self.user_id}) "
            f"上传了文件: "
            f"{self.file['name']}"
            f"({self.file['id']})"
        )


@register_event("notice", notice_type="group_admin")
class GroupAdminEvent(NoticeEvent):
    """
    群管理员变动事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.sub_type: str = self["sub_type"]

    @property
    def is_set(self) -> bool:
        """
        判断是否为设置管理员
        """
        return self.sub_type == "set"

    @property
    def is_unset(self) -> bool:
        """
        判断是否为取消管理员
        """
        return self.sub_type == "unset"


@register_event("notice", notice_type="group_admin", sub_type="set")
class GroupSetAdminEvent(GroupAdminEvent):
    """
    群管理员被设置事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 成员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"被设置为管理员"
        )


@register_event("notice", notice_type="group_admin", sub_type="unset")
class GroupUnsetAdminEvent(GroupAdminEvent):
    """
    群管理员被取消事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 成员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"被取消管理员"
        )


@register_event("notice", notice_type="group_decrease")
class GroupDecreaseEvent(NoticeEvent):
    """
    群成员减少事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.operator_id = int(self["operator_id"])
        self.sub_type: str = self["sub_type"]

    @property
    def is_leave(self) -> bool:
        """
        判断是否为主动退群
        """
        return self.sub_type == "leave"

    @property
    def is_kick(self) -> bool:
        """
        判断是否为被踢
        """
        return self.sub_type == "kick"

    @property
    def is_self_kicked(self) -> bool:
        """
        判断是否是机器人自己被踢
        """
        return self.sub_type == "kick_me"


@register_event("notice", notice_type="group_decrease", sub_type="leave")
class GroupDecreaseLeaveEvent(GroupDecreaseEvent):
    """
    群成员离开事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内成员 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"退出了群聊"
        )


@register_event("notice", notice_type="group_decrease", sub_type="kick")
class GroupDecreaseKickEvent(GroupDecreaseEvent):
    """
    群成员被踢事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内成员 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"被管理员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"踢出了群聊"
        )


@register_event("notice", notice_type="group_decrease", sub_type="kick_me")
class GroupDecreaseKickMeEvent(GroupDecreaseEvent):
    """
    机器人自己被移出事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"将机器人踢出了群聊"
        )


@register_event("notice", notice_type="group_increase")
class GroupIncreaseEvent(NoticeEvent):
    """
    群成员增加事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.operator_id: int = int(self["operator_id"])
        self.sub_type: str = self["sub_type"]

    @property
    def was_approved(self) -> bool:
        """
        判断是否为管理员同意入群
        """
        return self.sub_type == "approve"

    @property
    def was_invited(self) -> bool:
        """
        判断是否为被邀请入群
        """
        return self.sub_type == "invite"


@register_event("notice", notice_type="group_increase", sub_type="approve")
class GroupIncreaseApproveEvent(GroupIncreaseEvent):
    """
    群成员同意入群事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内管理员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"将 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"批准入群"
        )


@register_event("notice", notice_type="group_increase", sub_type="invite")
class GroupIncreaseInviteEvent(GroupIncreaseEvent):
    """
    群成员被邀请入群事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内成员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.user_id}) "
            f"将 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.operator_id}) "
            f"邀请入群"
        )


@register_event("notice", notice_type="group_ban")
class GroupBanEvent(NoticeEvent):
    """
    群禁言事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.operator_id: int = int(self["operator_id"])
        self.sub_type: str = self["sub_type"]
        self.duration: int = int(self["duration"])

    @property
    def is_ban(self) -> bool:
        """
        判断是否为禁言
        """
        return self.sub_type == "ban"

    @property
    def is_unban(self) -> bool:
        """
        判断是否为解除禁言
        """
        return self.sub_type == "lift_ban"

    @property
    def is_whole_group_ban(self) -> bool:
        """
        判断是否为全员禁言/解禁 (user_id为0时)
        """
        return self.user_id == 0


@register_event("notice", notice_type="group_ban", sub_type="ban")
class GroupBanSetEvent(GroupBanEvent):
    """
    群禁言被设置事件
    """

    def logger(self):
        member_str = "全体成员" if self.is_whole_group_ban else \
            f"成员 {QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}({self.user_id})"

        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 {member_str} "
            f"被管理员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"禁言了: "
            f"{self.duration}s"
        )


@register_event("notice", notice_type="group_ban", sub_type="lift_ban")
class GroupBanLiftEvent(GroupBanEvent):
    """
    群禁言被解除事件
    """

    def logger(self):
        member_str = "全体成员" if self.is_whole_group_ban else \
            f"成员 {QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}({self.user_id})"

        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 {member_str} "
            f"被管理员 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"解除了禁言"
        )


@register_event("notice", notice_type="friend_add")
class FriendAddEvent(NoticeEvent):
    """
    好友添加事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.user_id: int = int(self["user_id"])

    def logger(self):
        logger.info(
            f"好友 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"添加了机器人的好友"
        )


@register_event("notice", notice_type="group_recall")
class GroupRecallEvent(NoticeEvent):
    """
    群消息撤回事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.operator_id: int = int(self["operator_id"])
        self.message_id: int = int(self["message_id"])

    @property
    def is_recalled_by_operator(self) -> bool:
        """
        判断是否被管理员撤回 (操作者不是消息发送者本人)
        """
        return self.user_id != self.operator_id

    def logger(self):
        if not self.is_recalled_by_operator:
            logger.info(
                f"群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id}) "
                f"内成员 "
                f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
                f"({self.user_id}) "
                f"撤回了消息: "
                f"{self.message_id}"
            )
        else:
            logger.info(
                f"群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id}) "
                f"内成员 "
                f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
                f"({self.user_id}) "
                f"被管理员 "
                f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
                f"({self.operator_id}) "
                f"撤回了消息: "
                f"{self.message_id}"
            )


@register_event("notice", notice_type="friend_recall")
class FriendRecallEvent(NoticeEvent):
    """
    好友消息撤回事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.user_id: int = int(self["user_id"])
        self.message_id: int = int(self["message_id"])

    def logger(self):
        logger.info(
            f"好友 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"撤回了消息: "
            f"{self.message_id}"
        )


@register_event("notice", notice_type="notify", sub_type="poke")
class GroupPokeEvent(NoticeEvent):
    """
    群戳一戳事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.target_id: int = int(self["target_id"])

    @property
    def is_poked_me(self) -> bool:
        """
        判断是否是机器人被戳
        """
        return self.target_id == self.self_id

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"  # user_id is the poker
            f"({self.user_id}) "
            f"戳了戳 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.target_id).get_nickname()}"  # target_id is pokered
            f"({self.target_id})"
        )


@register_event("notice", notice_type="notify", sub_type="lucky_king")
class GroupLuckyKingEvent(NoticeEvent):
    """
    群红包运气王事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.target_id: int = int(self["target_id"])

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"  # user_id is lucky king
            f"({self.user_id}) "
            f"成为了 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.target_id).get_nickname()}"  # target_id is sender
            f"({self.target_id}) "
            f"发送的红包的运气王"
        )


@register_event("notice", notice_type="notify", sub_type="honor")
class GroupHonorEvent(NoticeEvent):
    """
    群荣誉变更事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])
        self.honor_type: str = self["honor_type"]

    def logger(self):
        if self.honor_type not in ["talkative", "performer", "emotion"]:
            logger.info(
                f"群 "
                f"{QQDataCacher.get_group_info(self.group_id).group_name}"
                f"({self.group_id}) "
                f"内 "
                f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
                f"({self.user_id}) "
                f"获得了未知荣誉: "
                f"{self.honor_type}"
            )
        else:
            super().logger()


@register_event("notice", notice_type="notify", sub_type="honor", honor_type="talkative")
class GroupTalkativeHonorEvent(GroupHonorEvent):
    """
    群龙王变更事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"获得了群龙王称号"
        )


@register_event("notice", notice_type="notify", sub_type="honor", honor_type="performer")
class GroupPerformerHonorEvent(GroupHonorEvent):
    """
    群群聊之火变更事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"获得了群聊炽焰称号"
        )


@register_event("notice", notice_type="notify", sub_type="honor", honor_type="emotion")
class GroupEmotionHonorEvent(GroupHonorEvent):
    """
    群表快乐源泉变更事件
    """

    def logger(self):
        logger.info(
            f"群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id}) "
            f"获得了快乐源泉称号"
        )


@register_event("request")
class RequestEvent(Event):
    """
    请求事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.request_type: str = self["request_type"]
        self.comment: str = self["comment"]
        self.flag: str = self["flag"]


@register_event("request", request_type="friend")
class FriendRequestEvent(RequestEvent):
    """
    加好友请求事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.user_id: int = int(self["user_id"])

    def logger(self):
        logger.info(
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id})"
            f"请求添加机器人为好友\n"
            f"验证信息: {self.comment}\n"
            f"flag: {self.flag}"
        )


@register_event("request", request_type="group")
class GroupRequestEvent(RequestEvent):
    """
    加群请求事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.sub_type: str = self["sub_type"]
        self.group_id: int = int(self["group_id"])
        self.user_id: int = int(self["user_id"])

    @property
    def is_add_request(self) -> bool:
        """
        判断是否为加群请求
        """
        return self.sub_type == "add"

    @property
    def is_invite_request(self) -> bool:
        """
        判断是否为邀请机器人入群请求
        """
        return self.sub_type == "invite"


@register_event("request", request_type="group", sub_type="add")
class GroupAddRequestEvent(GroupRequestEvent):
    """
    加群请求事件 - 添加
    """

    def logger(self):
        logger.info(
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()}"
            f"({self.user_id})"
            f"请求加入群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id})\n"
            f"验证信息: {self.comment}\n"
            f"flag: {self.flag}"
        )


@register_event("request", request_type="group", sub_type="invite")
class GroupInviteRequestEvent(GroupRequestEvent):
    """
    加群请求事件 - 邀请
    """

    def logger(self):
        logger.info(
            f"{QQDataCacher.get_group_member_info(self.group_id, self.user_id).get_nickname()}"
            f"({self.user_id})"
            f"邀请机器人加入群 "
            f"{QQDataCacher.get_group_info(self.group_id).group_name}"
        )


@register_event("meta_event")
class MetaEvent(Event):
    """
    元事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.meta_event_type: str = self["meta_event_type"]


@register_event("meta_event", meta_event_type="lifecycle")
class LifecycleMetaEvent(MetaEvent):
    """
    元事件 - 生命周期
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.sub_type: str = self["sub_type"]

    @property
    def is_enable(self) -> bool:
        """
        判断是否为 OneBot 启用
        """
        return self.sub_type == "enable"

    @property
    def is_disable(self) -> bool:
        """
        判断是否为 OneBot 禁用
        """
        return self.sub_type == "disable"

    @property
    def is_connect(self) -> bool:
        """
        判断是否为 OneBot 连接成功
        """
        return self.sub_type == "connect"

    def logger(self):
        logger.info(
            f"收到元事件: " + {
                "enable": "OneBot 启用",
                "disable": "OneBot 禁用",
                "connect": "OneBot 连接成功"
            }.get(self.sub_type, f"未知的生命周期事件: {self.sub_type}")
        )


@register_event("meta_event", meta_event_type="lifecycle", sub_type="enable")
class EnableMetaEvent(LifecycleMetaEvent):
    """
    元事件 - 生命周期 - OneBot 启用
    """

    def logger(self):
        logger.info("收到元事件: OneBot 启用")


@register_event("meta_event", meta_event_type="lifecycle", sub_type="disable")
class DisableMetaEvent(LifecycleMetaEvent):
    """
    元事件 - 生命周期 - OneBot 禁用
    """

    def logger(self):
        logger.info("收到元事件: OneBot 禁用")


@register_event("meta_event", meta_event_type="lifecycle", sub_type="connect")
class ConnectMetaEvent(LifecycleMetaEvent):
    """
    元事件 - 生命周期 - OneBot 连接成功
    """

    def logger(self):
        logger.info("收到元事件: OneBot 连接成功")


@register_event("meta_event", meta_event_type="heartbeat")
class HeartbeatMetaEvent(MetaEvent):
    """
    元事件 - 心跳
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.status: dict = self["status"]
        self.interval: int = int(self["interval"])

    def logger(self):
        logger.debug(f"收到心跳包")


@EventManager.event_listener(ListenerServer.EscalationEvent)
def on_escalation(event_data):
    """
    事件分发器
    Args:
        event_data: 事件数据
    Returns:
        None
    """
    event_data = event_data.event_data
    event = Event(event_data)
    event_call_list = [event]
    matched_event = False
    for event_cls_data in events:
        if (
                event_data["post_type"] == event_cls_data['post_type'] and
                all(k in event_data and event_data[k] == v for k, v in event_cls_data['rules'].items())
        ):
            event = event_cls_data['cls'](event_data)
            if not matched_event:
                if event.logger() is not False:
                    matched_event = True
            event_call_list.append(event)

    if not matched_event:
        logger.warning(f"未知的上报事件: {event_data}")

    # 广播事件
    for event in event_call_list:
        event.call()
