"""
操作
"""

from murainbot.common import save_exc_dump
from murainbot.core import OnebotAPI, ThreadPool, ConfigManager
from murainbot.utils import QQRichText, Logger, QQDataCacher

logger = Logger.get_logger()

from typing import Generic, TypeVar, Union, Callable

api = OnebotAPI.OnebotAPI()

T = TypeVar("T")  # 成功类型
E = TypeVar("E")  # 错误类型


class Result(Generic[T, E]):
    """
    结果类
    """

    def __init__(self, value: Union[T, E], is_ok: bool):
        self._value = value
        self._is_ok = is_ok

    @property
    def is_ok(self) -> bool:
        """
        判断是否成功
        Returns:
            是否成功
        """
        return self._is_ok

    @property
    def is_err(self) -> bool:
        """
        判断是否失败
        Returns:
            是否失败
        """
        return not self._is_ok

    def unwrap(self) -> T:
        """
        获取结果（如果成功，否则触发异常）
        Returns:
            结果
        """
        if self.is_ok:
            return self._value
        raise Exception(f"Called unwrap on an Err value: {self._value}")

    def unwrap_err(self) -> E:
        """
        获取错误（如果失败，否则触发异常）
        Returns:
            错误
        """
        if self.is_err:
            return self._value
        raise Exception(f"Called unwrap_err on an Ok value: {self._value}")

    def expect(self, message: str) -> T:
        """
        获取结果（如果失败，否则触发异常）
        Args:
            message: 错误信息
        Returns:
            结果
        """
        if self.is_ok:
            return self._value
        raise Exception(message)


UnCalled = type("UnCalled", (), {})


class Action:
    """
    Action基类，无实际用途，勿调用
    """
    call_func = None

    def __init__(self, *args, callback: Callable[[Result], ...] = None, **kwargs):
        self._result: UnCalled | Result = UnCalled
        self._async = None
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def set_callback(self, callback: Callable[[Result], ...]):
        """
        设置回调函数，如果Action已被调用则立即执行回调函数
        Returns:
            Action
        """
        self.callback = callback
        if self._result is not UnCalled:
            try:
                self.callback(self._result)
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(f"执行回调函数异常")
                else:
                    dump_path = None
                logger.warning(f"执行回调函数异常: {repr(e)}\n"
                               f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                               exc_info=True)
        return self

    def call(self):
        """
        调用Action
        Returns:
            Action
        """
        try:
            result = Result(self.call_func(*self.args, **self.kwargs), True)
        except Exception as e:
            result = Result(e, False)
        self._result = result
        try:
            if self._result.is_ok:
                self.logger(result.unwrap(), *self.args, **self.kwargs)
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"调用日志记录函数异常")
            else:
                dump_path = None
            logger.warning(f"调用日志记录函数异常: {repr(e)}"
                           f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                           exc_info=True)
        if self.callback is not None:
            try:
                self.callback(self._result)
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(f"执行回调函数异常")
                else:
                    dump_path = None
                logger.warning(f"回调函数异常: {repr(e)}"
                               f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                               exc_info=True)
        return self

    def logger(self, *args, **kwargs):
        """
        当Action调用成功时调用此方法记录log
        Args:
            result: self.call_func返回的结果
            *args: 传给self.call_func的参数
            **kwargs: 传给self.call_func的参数
        """
        pass

    def get_result(self) -> Result:
        """
        获取结果
        Returns:
            结果
        """
        if self._async is not None:
            self._async.result()
            self._async = None
        if self._result is UnCalled:
            raise Exception("Action not called")
        return self._result

    def call_get_result(self):
        """
        同步调用Action并获取结果
        Returns:
            结果
        """
        self.call()
        return self.get_result()

    def call_async(self):
        """
        异步调用Action
        Returns:
            Action
        """

        @ThreadPool.async_task
        def _call_async():
            return self.call()

        self._async = _call_async()
        return self

    def wait_async(self):
        """
        等待异步调用
        Returns:
            Action
        """
        if self._async is None:
            raise Exception("Action not called")
        self._async.result()
        return self


class SendPrivateMsg(Action):
    """
    发送私聊消息
    """

    call_func = api.send_private_msg

    def __init__(self, user_id: int, message: str | list[dict] | QQRichText.QQRichText,
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            user_id (int): 对方 QQ 号
            message (str | list[dict] | QQRichText.QQRichText): 要发送的内容
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        if isinstance(message, QQRichText.QQRichText):
            message = message.get_array()
        super().__init__(user_id=user_id, message=message, callback=callback)

    def logger(self, result, user_id: int, message: str | list[dict] | QQRichText.QQRichText):
        logger.info(f"向 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) "
                    f"发送消息 {message}({result['message_id']})")


class SendGroupMsg(Action):
    """
    发送群聊消息
    """

    call_func = api.send_group_msg

    def __init__(self, group_id: int, message: str | list[dict] | QQRichText.QQRichText,
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            message (str | list[dict] | QQRichText.QQRichText): 要发送的内容
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        if isinstance(message, QQRichText.QQRichText):
            message = message.get_array()
        super().__init__(group_id=group_id, message=message, callback=callback)

    def logger(self, result, group_id: int, message: str | list[dict] | QQRichText.QQRichText):
        logger.info(f"向群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"发送消息 {QQRichText.QQRichText(message)}({result['message_id']})")


class SendMsg(Action):
    """
    发送消息
    """

    call_func = api.send_msg

    def __init__(self, user_id: int = -1, group_id: int = -1, message: str | list[dict] | QQRichText.QQRichText = "",
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            user_id (int, optional): 对方 QQ 号（消息类型为 `private` 时需要）. Defaults to -1.
            group_id (int, optional): 群号（消息类型为 `group` 时需要）. Defaults to -1.
            message (str | list[dict] | QQRichText.QQRichText, optional): 要发送的内容. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        if isinstance(message, QQRichText.QQRichText):
            message = message.get_array()

        if user_id != -1 and group_id != -1:
            raise ValueError('user_id and group_id cannot be both not -1.')
        if user_id == -1 and group_id == -1:
            raise ValueError('user_id and group_id cannot be both -1.')

        super().__init__(user_id=user_id, group_id=group_id, message=message, callback=callback)

    def logger(self, result, user_id: int, group_id: int, message: str | list[dict] | QQRichText.QQRichText):
        if user_id != -1:
            logger.info(f"向 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) "
                        f"发送消息 {QQRichText.QQRichText(message)}({result['message_id']})")
        else:
            logger.info(f"向群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                        f"发送消息 {QQRichText.QQRichText(message)}({result['message_id']})")


class DeleteMsg(Action):
    """
    撤回消息
    """

    call_func = api.delete_msg

    def __init__(self, message_id: int, callback: Callable[[Result], ...] = None):
        """
        Args:
            message_id (int): 消息 ID
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(message_id=message_id, callback=callback)

    def logger(self, result, message_id: int):
        logger.info(f"撤回消息 {message_id}")


class GetMsg(Action):
    """
    获取消息
    """

    call_func = api.get_msg

    def __init__(self, message_id: int, callback: Callable[[Result], ...] = None):
        """
        Args:
            message_id (int): 消息 ID
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(message_id=message_id, callback=callback)

    def logger(self, result, message_id: int):
        logger.debug(f"获取消息 {message_id}")


class GetForwardMsg(Action):
    """
    获取合并转发消息
    """

    call_func = api.get_forward_msg

    def __init__(self, id: int, callback: Callable[[Result], ...] = None):
        """
        Args:
            id (int): 合并转发 ID
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(id=id, callback=callback)

    def logger(self, result, id: int):
        logger.debug(f"获取合并转发消息 {id}")


class SendLike(Action):
    """
    发送好友赞
    """

    call_func = api.send_like

    def __init__(self, user_id: int, times: int = 1, callback: Callable[[Result], ...] = None):
        """
        Args:
            user_id (int): 对方 QQ 号
            times (int, optional): 赞的次数，每个好友每天最多 10 次. Defaults to 1.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(user_id=user_id, times=times, callback=callback)

    def logger(self, result, user_id: int, times: int):
        logger.info(f"发送好友赞 {user_id} {times} 次")


class SetGroupKick(Action):
    """
    群组踢人
    """

    call_func = api.set_group_kick

    def __init__(self, group_id: int, user_id: int, reject_add_request: bool = False,
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): 要踢的 QQ 号
            reject_add_request (bool, optional): 拒绝此人的加群请求. Defaults to False.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, reject_add_request=reject_add_request, callback=callback)

    def logger(self, result, group_id: int, user_id: int, reject_add_request: bool):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) 踢出群聊"
                    f"{'并拒绝此人加群请求' if reject_add_request else ''}")


class SetGroupBan(Action):
    """
    群组单人禁言
    """

    call_func = api.set_group_ban

    def __init__(self, group_id: int, user_id: int, duration: int = 30 * 60, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): 要禁言的 QQ 号
            duration (int, optional): 禁言时长，单位秒，0 表示取消禁言. Defaults to 30 * 60.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, duration=duration, callback=callback)

    def logger(self, result, group_id: int, user_id: int, duration: int):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) 禁言 {duration} 秒")


class SetGroupAnonymousBan(Action):
    """
    群组匿名用户禁言
    """

    call_func = api.set_group_anonymous_ban

    def __init__(self, group_id: int, anonymous: dict = None, anonymous_flag: str = None, duration: int = 30 * 60,
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            anonymous (dict, optional): 要禁言的匿名用户对象（群消息上报的 `anonymous` 字段）. Defaults to None.
            anonymous_flag (str, optional): 要禁言的匿名用户的 flag（需从群消息上报的数据中获得）. Defaults to None.
            duration (int, optional): 禁言时长，单位秒，无法取消匿名用户禁言. Defaults to 30 * 60.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, anonymous=anonymous, anonymous_flag=anonymous_flag, duration=duration,
                         callback=callback, **{'flag': anonymous_flag} if anonymous_flag else {})

    def logger(self, result, group_id: int, anonymous: dict, anonymous_flag: str, duration: int):
        anonymous_str = f"{QQDataCacher.get_user_info(anonymous['id']).nickname}" if anonymous else "匿名用户"
        anonymous_detail = f"({anonymous['id']}; flag: {anonymous_flag})" if anonymous else ""
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {anonymous_str} {anonymous_detail} 禁言 {duration} 秒")


class SetGroupWholeBan(Action):
    """
    群组全员禁言
    """

    call_func = api.set_group_whole_ban

    def __init__(self, group_id: int, enable: bool = True, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            enable (bool, optional): 是否禁言. Defaults to True.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, enable=enable, callback=callback)

    def logger(self, result, group_id: int, enable: bool):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"{'开启' if enable else '关闭'}全员禁言")


class SetGroupAdmin(Action):
    """
    设置群管理员
    """

    call_func = api.set_group_admin

    def __init__(self, group_id: int, user_id: int, enable: bool = True, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): 要设置管理员的 QQ 号
            enable (bool, optional): true 为设置，false 为取消. Defaults to True.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, enable=enable, callback=callback)

    def logger(self, result, group_id: int, user_id: int, enable: bool):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) "
                    f"{'设为' if enable else '取消设为'}管理员")


class SetGroupCard(Action):
    """
    设置群名片（群备注）
    """

    call_func = api.set_group_card

    def __init__(self, group_id: int, user_id: int, card: str = "", callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): 要设置的 QQ 号
            card (str, optional): 群名片内容，不填或空字符串表示删除群名片. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, card=card, callback=callback)

    def logger(self, result, group_id: int, user_id: int, card: str):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) "
                    f"{'设置群名片为' if card else '删除群名片'} {card}")


class SetGroupLeave(Action):
    """
    退出群组
    """

    call_func = api.set_group_leave

    def __init__(self, group_id: int, is_dismiss: bool = False, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            is_dismiss (bool, optional): 是否解散，如果登录号是群主，则仅在此项为 true 时能够解散. Defaults to False.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, is_dismiss=is_dismiss, callback=callback)

    def logger(self, result, group_id: int, is_dismiss: bool):
        logger.info(f"退出群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"{'并解散' if is_dismiss else ''}")


class SetGroupSpecialTitle(Action):
    """
    设置群组专属头衔
    """

    call_func = api.set_group_special_title

    def __init__(self, group_id: int, user_id: int, special_title: str = "", duration: int = -1,
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): 要设置的 QQ 号
            special_title (str, optional): 专属头衔，不填或空字符串表示删除专属头衔. Defaults to "".
            duration (int, optional): 专属头衔有效期，单位秒，-1 表示永久. Defaults to -1.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, special_title=special_title, duration=duration,
                         callback=callback)

    def logger(self, result, group_id: int, user_id: int, special_title: str, duration: int):
        logger.info(f"将群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) "
                    f"内成员 {QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) "
                    f"{'设置专属头衔为' if special_title else '删除专属头衔'} {special_title} "
                    )


class SetFriendAddRequest(Action):
    """
    处理加好友请求
    """

    call_func = api.set_friend_add_request

    def __init__(self, flag: str, approve: bool = True, remark: str = "", callback: Callable[[Result], ...] = None):
        """
        Args:
            flag (str): 加好友请求的 flag（需从上报的数据中获得）
            approve (bool, optional): 是否同意请求. Defaults to True.
            remark (str, optional): 添加后的好友备注（仅在同意时有效）. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(flag=flag, approve=approve, remark=remark, callback=callback)

    def logger(self, result, flag: str, approve: bool, remark: str):
        logger.info(f"处理加好友请求 {'同意' if approve else '拒绝'} "
                    f"{'并设置备注为' if remark else ''} {remark}")


class SetGroupAddRequest(Action):
    """
    处理加群请求/邀请
    """

    call_func = api.set_group_add_request

    def __init__(self, flag: str, sub_type: str = "add", approve: bool = True, reason: str = "",
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            flag (str): 加群请求的 flag（需从上报的数据中获得）
            sub_type (str, optional): `add` 或 `invite`，请求类型（需要和上报消息中的 `sub_type` 字段相符）. Defaults to "add".
            approve (bool, optional): 是否同意请求／邀请. Defaults to True.
            reason (str, optional): 拒绝理由（仅在拒绝时有效）. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(flag=flag, sub_type=sub_type, approve=approve, reason=reason, callback=callback)

    def logger(self, result, flag: str, sub_type: str, approve: bool, reason: str):
        logger.info(f"处理加群请求/邀请 {'同意' if approve else '拒绝'} "
                    f"{'并设置理由为' if reason else ''} {reason}")


class GetLoginInfo(Action):
    """
    获取登录号信息
    """

    call_func = api.get_login_info

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取登录号信息")


class GetStrangerInfo(Action):
    """
    获取陌生人信息
    """

    call_func = api.get_stranger_info

    def __init__(self, user_id: int, no_cache: bool = False, callback: Callable[[Result], ...] = None):
        """
        Args:
            user_id (int): QQ 号
            no_cache (bool, optional): 是否不使用缓存（使用缓存可能更新不及时，但响应更快）. Defaults to False.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(user_id=user_id, no_cache=no_cache, callback=callback)

    def logger(self, result, user_id: int, no_cache: bool):
        logger.debug(f"获取陌生人 {user_id} 信息")


class GetFriendList(Action):
    """
    获取好友列表
    """

    call_func = api.get_friend_list

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取好友列表")


class GetGroupInfo(Action):
    """
    获取群信息
    """

    call_func = api.get_group_info

    def __init__(self, group_id: int, no_cache: bool = False, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            no_cache (bool, optional): 是否不使用缓存（使用缓存可能更新不及时，但响应更快）. Defaults to False.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, no_cache=no_cache, callback=callback)

    def logger(self, result, group_id: int, no_cache: bool):
        logger.debug(f"获取群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) 信息")


class GetGroupList(Action):
    """
    获取群列表
    """

    call_func = api.get_group_list

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取群列表")


class GetGroupMemberInfo(Action):
    """
    获取群成员信息
    """

    call_func = api.get_group_member_info

    def __init__(self, group_id: int, user_id: int, no_cache: bool = False, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            user_id (int): QQ 号
            no_cache (bool, optional): 是否不使用缓存（使用缓存可能更新不及时，但响应更快）. Defaults to False.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, user_id=user_id, no_cache=no_cache, callback=callback)

    def logger(self, result, group_id: int, user_id: int, no_cache: bool):
        logger.debug(
            f"获取群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) 成员 "
            f"{QQDataCacher.get_user_info(user_id).get_nickname()}({user_id}) 信息")


class GetGroupMemberList(Action):
    """
    获取群成员列表
    """

    call_func = api.get_group_member_list

    def __init__(self, group_id: int, callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, callback=callback)

    def logger(self, result, group_id: int):
        logger.debug(f"获取群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) 成员列表")


class GetGroupHonorInfo(Action):
    """
    获取群荣誉信息
    """

    call_func = api.get_group_honor_info

    def __init__(self, group_id: int, type_: str = "all", callback: Callable[[Result], ...] = None):
        """
        Args:
            group_id (int): 群号
            type_ (str, optional): 要获取的群荣誉类型，可传入 `talkative` `performer` `legend` `strong_newbie` `emotion`
            以分别获取单个类型的群荣誉数据，或传入 `all` 获取所有数据. Defaults to "all".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(group_id=group_id, type_=type_, callback=callback)

    def logger(self, result, group_id: int, type_: str):
        logger.debug(f"获取群 {QQDataCacher.get_group_info(group_id).group_name}({group_id}) 荣誉信息, 类型: {type_}")


class GetCookies(Action):
    """
    获取 Cookies
    """

    call_func = api.get_cookies

    def __init__(self, domain: str = "", callback: Callable[[Result], ...] = None):
        """
        Args:
            domain (str, optional): 需要获取 cookies 的域名. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(domain=domain, callback=callback)

    def logger(self, result, domain: str):
        logger.debug(f"获取 Cookies, domain: {domain}")


class GetCsrfToken(Action):
    """
    获取 CSRF Token
    """

    call_func = api.get_csrf_token

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取 CSRF Token")


class GetCredentials(Action):
    """
    获取 QQ 相关接口凭证
    """

    call_func = api.get_credentials

    def __init__(self, domain: str = "", callback: Callable[[Result], ...] = None):
        """
        Args:
            domain (str, optional): 需要获取 cookies 的域名. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(domain=domain, callback=callback)

    def logger(self, result, domain: str):
        logger.debug(f"获取 QQ 相关接口凭证, domain: {domain}")


class GetRecord(Action):
    """
    获取语音
    """

    call_func = api.get_record

    def __init__(self, file: str, out_format: str = "mp3", out_file: str = "",
                 callback: Callable[[Result], ...] = None):
        """
        Args:
            file (str): 收到的语音文件名（消息段的 `file` 参数），如 `0B38145AA44505000B38145AA4450500.silk`
            out_format (str, optional): 要转换到的格式，目前支持
            `mp3`、`amr`、`wma`、`m4a`、`spx`、`ogg`、`wav`、`flac`. Defaults to "mp3".
            out_file (str, optional): unused parameter. Defaults to "".
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(file=file, out_format=out_format, out_file=out_file, callback=callback)

    def logger(self, result, file: str, out_format: str, out_file: str):
        logger.debug(f"获取语音文件: {file}, 转换格式: {out_format}")


class GetImage(Action):
    """
    获取图片
    """

    call_func = api.get_image

    def __init__(self, file: str, callback: Callable[[Result], ...] = None):
        """
        Args:
            file (str): 收到的图片文件名（消息段的 `file` 参数），如 `6B4DE3DFD1BD271E3297859D41C530F5.jpg`
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(file=file, callback=callback)

    def logger(self, result, file: str):
        logger.debug(f"获取图片文件: {file}")


class CanSendImage(Action):
    """
    检查是否可以发送图片
    """

    call_func = api.can_send_image

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"检查是否可以发送图片")


class CanSendRecord(Action):
    """
    检查是否可以发送语音
    """

    call_func = api.can_send_record

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"检查是否可以发送语音")


class GetStatus(Action):
    """
    获取运行状态
    """

    call_func = api.get_status

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取Onebot运行状态")


class GetVersionInfo(Action):
    """
    获取版本信息
    """

    call_func = api.get_version_info

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"获取Onebot版本信息")


class SetRestart(Action):
    """
    重启
    """

    call_func = api.set_restart

    def __init__(self, delay: int = 0, callback: Callable[[Result], ...] = None):
        """
        Args:
            delay (int, optional): 要延迟的毫秒数. Defaults to 0.
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(delay=delay, callback=callback)

    def logger(self, result, delay: int):
        logger.info(f"重启Onebot实现端, 延迟: {delay}ms")


class CleanCache(Action):
    """
    清理缓存
    """

    call_func = api.clean_cache

    def __init__(self, callback: Callable[[Result], ...] = None):
        """
        Args:
            callback (Callable[[Result], ...], optional): 回调函数. Defaults to None.
        """
        super().__init__(callback=callback)

    def logger(self, result):
        logger.debug(f"清理Onebot实现端缓存")


"""
使用示例：

if __name__ == "__main__":
    ThreadPool.init()

    action = SendPrivateMsg(user_id=123456789, message="Hello World").call()
    res = action.get_result()

    # 下面二者等价
    res = SendPrivateMsg(user_id=123456789, message="Hello World").call().get_result()
    res = SendPrivateMsg(user_id=123456789, message="Hello World").call_get_result()

    action = SendPrivateMsg(user_id=123456789, message="Hello World").call_async()
    res = action.get_result()

    if res.is_ok:
        print(res.unwrap())
    else:
        print(res.unwrap_err())
"""
