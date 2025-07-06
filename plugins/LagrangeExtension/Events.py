"""
Lagrange的一些拓展事件
"""
from typing import TypedDict

from murainbot.utils import EventClassifier, Logger, QQDataCacher

logger = Logger.get_logger()


@EventClassifier.register_event("notice", notice_type="bot_online")
class BotOnLineEvent(EventClassifier.NoticeEvent):
    def __init__(self, event_data):
        super().__init__(event_data)
        self.reason: str = event_data["reason"]

    def logger(self):
        logger.info(f"机器人上线: {self.reason}")


@EventClassifier.register_event("notice", notice_type="bot_offline")
class BotOffLineEvent(EventClassifier.NoticeEvent):
    def __init__(self, event_data):
        super().__init__(event_data)
        self.tag: str = event_data["tag"]
        self.message: str = event_data["message"]

    def logger(self):
        logger.warning(f"机器人离线: {self.tag} {self.message}")


@EventClassifier.register_event("notice", notice_type="group_name_change")
class GroupNameChangeEvent(EventClassifier.NoticeEvent):
    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.name: str = self["name"]

    def logger(self):
        logger.info(f"群 {self.group_id} 的名称改变为: {self.name}")


@EventClassifier.register_event("notice", notice_type="essence")
class GroupEssenceEvent(EventClassifier.NoticeEvent):
    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.sender_id: int = int(self["sender_id"])
        self.operator_id: int = int(self["operator_id"])
        self.message_id: int = int(self["message_id"])
        self.sub_type: str = self["sub_type"]


@EventClassifier.register_event("notice", notice_type="essence", sub_type="add")
class GroupAddEssenceEvent(GroupEssenceEvent):
    def logger(self):
        logger.info(
            f"群 {QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.sender_id).get_nickname()}"
            f"({self.sender_id}) "
            f"的消息 {self.message_id} 被 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"设置为精华消息"
        )


@EventClassifier.register_event("notice", notice_type="essence", sub_type="delete")
class GroupDeleteEssenceEvent(GroupEssenceEvent):
    def logger(self):
        logger.info(
            f"群 {QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.sender_id).get_nickname()}"
            f"({self.sender_id}) "
            f"的消息 {self.message_id} 被 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"取消了精华消息"
        )


@EventClassifier.register_event("notice", notice_type="reaction")
class GroupReactionEvent(EventClassifier.NoticeEvent):
    def __init__(self, event_data):
        super().__init__(event_data)
        self.group_id: int = int(self["group_id"])
        self.message_id: int = int(self["message_id"])
        self.operator_id: int = int(self["operator_id"])
        self.sub_type: str = self["sub_type"]
        self.count: int = self["count"]
        self.code: int = self["code"]


@EventClassifier.register_event("notice", notice_type="reaction", sub_type="add")
class GroupAddReactionEvent(GroupReactionEvent):
    def logger(self):
        logger.info(
            f"群 {QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"给消息 {self.message_id} 添加了表情 {self.code} (共计{self.count}个)"
        )


@EventClassifier.register_event("notice", notice_type="reaction", sub_type="remove")
class GroupDeleteReactionEvent(GroupReactionEvent):
    def logger(self):
        logger.info(
            f"群 {QQDataCacher.get_group_info(self.group_id).group_name}"
            f"({self.group_id}) "
            f"内 "
            f"{QQDataCacher.get_group_member_info(self.group_id, self.operator_id).get_nickname()}"
            f"({self.operator_id}) "
            f"给消息 {self.message_id} 删除了表情 {self.code} (还有{self.count}个)"
        )


class FileDict(TypedDict, total=False):
    """
    文件数据
    """
    id: str
    name: str
    size: int
    url: str
    hash: int


@EventClassifier.register_event("notice", notice_type="offline_file")
class PrivateFileEvent(EventClassifier.NoticeEvent):
    """
    私聊文件发送事件
    """

    def __init__(self, event_data):
        super().__init__(event_data)
        self.user_id: int = int(self["user_id"])
        self.file: FileDict = self["file"]

    def logger(self):
        logger.info(
            f"用户 "
            f"{QQDataCacher.get_user_info(self.user_id).get_nickname()} "
            f"({self.user_id}) "
            f"上传了文件: "
            f"{self.file['name']}"
            f"({self.file['id']})\n"
            f"URL: {self.file['url']}"
        )
