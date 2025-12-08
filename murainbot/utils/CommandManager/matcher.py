"""
命令管理器的命令匹配器
"""
import dataclasses
from typing import Generator, Any, Callable

from murainbot.common import inject_dependencies, exc_logger
from murainbot.core import EventManager, PluginManager
from murainbot.utils import EventClassifier, QQRichText, Actions, EventHandlers, StateManager
from murainbot.utils.CommandManager import BaseArg, parsing_command_def, CommandManager, logger, NotMatchCommandError, \
    CommandMatchError

__all__ = [
    "CommandMatcher",
    "WaitCommand",
    "CommandEvent",
    "on_command"
]

from murainbot.utils.SessionManager import WaitAction, TriggerEvent


@EventClassifier.register_event("message")
class CommandEvent(EventClassifier.MessageEvent):
    def send(self, message: QQRichText.QQRichText | str):
        """
        向消息来源的人/群发送消息
        Args:
            message: 消息内容

        Returns:
            消息返回结果
        """
        if isinstance(message, str):
            message = QQRichText.QQRichText(QQRichText.Text(message))
        return Actions.SendMsg(
            message=message,
            **{"group_id": self["group_id"]}
            if self.is_group else
            {"user_id": self.user_id}
        ).call()

    def reply(self, message: QQRichText.QQRichText | str):
        """
        向消息来源的人/群发送回复消息（会自动在消息前加上reply消息段）
        Args:
            message: 消息内容

        Returns:
            消息返回结果
        """
        if isinstance(message, str):
            message = QQRichText.QQRichText(QQRichText.Text(message))
        return Actions.SendMsg(
            message=QQRichText.QQRichText(
                QQRichText.Reply(self.message_id),
                message
            ),
            **{"group_id": self["group_id"]}
            if self.is_group else
            {"user_id": self.user_id}
        ).call()


def _command_matcher_error_handler(event_data: CommandEvent, exc: Exception):
    """
    命令匹配错误处理
    Args:
        event_data: 发生错误的事件
        exc: 异常

    Returns:
        None
    """
    try:
        raise exc
    except NotMatchCommandError as e:
        logger.error(f"未匹配到命令: {repr(e)}", exc_info=True)
        event_data.reply(f"未匹配到命令: {e}")
    except CommandMatchError as e:
        logger.info(f"命令匹配错误: {repr(e)}", exc_info=True)
        event_data.reply(f"命令匹配错误，请检查命令是否正确: {e}")
    except Exception as e:
        exc_logger(e, f"在事件 {event_data.event_data} 中进行命令处理发生未知错误")
        event_data.reply(f"命令处理发生未知错误: {repr(e)}")


@dataclasses.dataclass
class WaitCommand(WaitAction):
    """
    等待命令
    """
    wait_command_def: BaseArg | str | None = None
    user_id: int | None = -1  # -1则为当前这个事件的用户，None则为任意用户，如果是群聊则仅限该群
    wait_trigger: Callable[["CommandMatcher.TriggerEvent"], ...] = dataclasses.field(init=False)
    ignore_error: bool = True
    error_handler: Callable[[CommandEvent, Exception], ...] = dataclasses.field(default=_command_matcher_error_handler)
    rules: list[EventHandlers.Rule] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.wait_command_def, str):
            # 自动将字符串解析为对象
            self.wait_command_def = parsing_command_def(self.wait_command_def)
        if self.wait_command_def is not None:
            wait_command = CommandManager().register_command(self.wait_command_def)
        else:
            wait_command = None
        self.wait_trigger = _wait_command_trigger(wait_command, self)


def _wait_command_trigger(wait_command: CommandManager | None, wait_action: WaitCommand):
    """
    创建等待命令触发器
    Args:
        wait_command: 命令管理器
        wait_action: 等待操作

    Returns:
        触发器
    """

    def trigger(trigger_event: TriggerEvent):
        def on_evnet(event_data: CommandEvent):
            if not wait_action.wait_handler:
                raise RuntimeError("等待处理器未设置")
            handler = wait_action.wait_handler
            if hasattr(handler.raw_event_data, "is_group"):
                if handler.raw_event_data.is_group and event_data.get("group_id") != handler.raw_event_data["group_id"]:
                    return
            if hasattr(handler.raw_event_data, "user_id") or wait_action.user_id != -1:
                wait_user_id = handler.raw_event_data.user_id if wait_action.user_id == -1 else wait_action.user_id
            else:
                raise RuntimeError("WaitCommand: 等待处理器的事件不包含user_id属性")
            if wait_user_id is None or wait_user_id == event_data.user_id:
                kwargs = {}
                for rule in wait_action.rules:
                    res = rule.match(event_data)
                    if isinstance(res, tuple):
                        res, rule_kwargs = res
                        kwargs.update(rule_kwargs)
                    if not res:
                        return
                if isinstance(wait_command, CommandManager):
                    try:
                        command_kwargs, _, _ = wait_command.run_command(event_data.message)
                    except Exception as e:
                        if not wait_action.ignore_error:
                            try:
                                wait_action.error_handler(event_data, e)
                            except Exception as e:
                                logger.exception(f"在捕获命令时出现错误，同时执行错误处理程序时也出错: {repr(e)}")
                                raise e
                        return
                    kwargs.update(command_kwargs)

                trigger_event.set_data((event_data, kwargs))
                EventManager.unregister_listener(CommandEvent, on_evnet)
                trigger_event.call()

        EventManager.event_listener(CommandEvent)(on_evnet)

    return trigger


class CommandMatcher(EventHandlers.Matcher):
    """
    命令匹配器
    """

    def __init__(
            self, plugin_data, rules: list[EventHandlers.Rule] = None,
            command_matcher_error_handler: Callable[[CommandEvent, Exception], None] = None
    ):
        super().__init__(plugin_data, rules)
        self.command_manager = CommandManager()
        if command_matcher_error_handler is None:
            command_matcher_error_handler = _command_matcher_error_handler
        self.command_matcher_error_handler = command_matcher_error_handler

    def register_command(self, command: BaseArg | str,
                         priority: int = 0, rules: list[EventHandlers.Rule] = None, *args, **kwargs):
        """
        注册命令
        Args:
            command: 命令
            priority: 优先级
            rules: 规则列表
        """
        if isinstance(command, str):
            command = parsing_command_def(command)
        self.command_manager.register_command(command)
        if rules is None:
            rules = []
        if any(not isinstance(rule, EventHandlers.Rule) for rule in rules):
            raise TypeError("rules must be a list of Rule")

        def wrapper(
                func: Callable[[CommandEvent, ...], bool | Any] | Generator[CommandEvent, WaitAction | WaitCommand, Any]
        ):
            self.handlers.append((priority, rules, func, args, kwargs, command))
            return func

        return wrapper

    def check_match(self, event_data: CommandEvent) -> tuple[bool, dict | None]:
        """
        检查事件是否匹配该匹配器
        Args:
            event_data: 事件数据

        Returns:
            是否匹配, 规则返回的依赖注入参数
        """
        rules_kwargs = {}
        try:
            for rule in self.rules:
                res = rule.match(event_data)
                if isinstance(res, tuple):
                    res, rule_kwargs = res
                    rules_kwargs.update(rule_kwargs)
                if not res:
                    return False, None
        except Exception as e:
            exc_logger(e,
                       f"在事件 {event_data.event_data} 中匹配事件处理器时出错")
            return False, None
        return True, rules_kwargs

    def match(self, event_data: CommandEvent, rules_kwargs: dict):
        """
        匹配事件处理器
        Args:
            event_data: 事件数据
            rules_kwargs: 规则返回的注入参数
        """
        if self.command_manager.command_list:
            try:
                kwargs, command_def, last_command_def = self.command_manager.run_command(
                    rules_kwargs["command_message"]
                )
            except Exception as e:
                try:
                    self.command_matcher_error_handler(event_data, e)
                except Exception as e:
                    logger.exception(f"在捕获命令时出现错误，同时执行错误处理程序时也出错: {repr(e)}")
                    raise e
                return None
            rules_kwargs.update({
                "command_def": command_def,
                "last_command_def": last_command_def,
                **kwargs
            })
        else:
            command_def = None

        for handler in sorted(self.handlers, key=lambda x: x[0], reverse=True):
            if len(handler) == 5:
                priority, rules, handler, args, kwargs = handler
                handler_command_def = None
            else:
                priority, rules, handler, args, kwargs, handler_command_def = handler

            if command_def and handler_command_def != command_def and handler_command_def:
                continue

            try:
                handler_kwargs = kwargs.copy()  # 复制静态 kwargs
                rules_kwargs = rules_kwargs.copy()
                flag = False
                for rule in rules:
                    res = rule.match(event_data)
                    if isinstance(res, tuple):
                        res, rule_kwargs = res
                        rules_kwargs.update(rule_kwargs)
                    if not res:
                        flag = True
                        break
                if flag:
                    continue

                # 检测依赖注入
                if isinstance(event_data, EventClassifier.MessageEvent):
                    if event_data.is_private:
                        state_id = f"u{event_data.user_id}"
                    elif event_data.is_group:
                        state_id = f"g{event_data["group_id"]}_u{event_data.user_id}"
                    else:
                        state_id = None
                    if state_id:
                        handler_kwargs["state"] = StateManager.get_state(state_id, self.plugin_data)
                    handler_kwargs["user_state"] = StateManager.get_state(f"u{event_data.user_id}", self.plugin_data)
                    if isinstance(event_data, EventClassifier.GroupMessageEvent):
                        handler_kwargs["group_state"] = StateManager.get_state(f"g{event_data.group_id}",
                                                                               self.plugin_data)

                handler_kwargs.update(rules_kwargs)
                handler_kwargs = inject_dependencies(handler, handler_kwargs)

                result = handler(event_data, *args, **handler_kwargs)

                if result is True:
                    logger.debug(f"处理器 {handler.__module__}.{handler.__name__} 阻断了事件 {event_data} 的传播")
                    return None  # 阻断同一 Matcher 内的传播
            except Exception as e:
                exc_logger(e,
                           f"执行匹配事件或执行处理器 {handler.__module__}.{handler.__name__} 时出错 {event_data}")
        return None


# command_manager = CommandManager()
matchers: list[tuple[int, EventHandlers.Matcher]] = []


def _on_event(event_data):
    for priority, matcher in sorted(matchers, key=lambda x: x[0], reverse=True):
        matcher_event_data = event_data.__class__(event_data.event_data)
        is_match, rules_kwargs = matcher.check_match(matcher_event_data)
        if is_match:
            matcher.match(matcher_event_data, rules_kwargs)
            return


EventManager.event_listener(CommandEvent)(_on_event)


def on_command(command: str,
               aliases: set[str] = None,
               command_start: list[str] = None,
               reply: bool = False,
               no_args: bool = False,
               priority: int = 0,
               rules: list[EventHandlers.Rule] = None):
    """
    注册命令处理器
    Args:
        command: 命令
        aliases: 命令别名
        command_start: 命令起始符（不填写默认为配置文件中的command_start）
        reply: 是否可包含回复（默认否）
        no_args: 是否不需要命令参数（即消息只能完全匹配命令，不包含其他的内容）
        priority: 优先级
        rules: 匹配规则

    Returns:
        命令处理器
    """
    if rules is None:
        rules = []
    rules += [EventHandlers.CommandRule(command, aliases, command_start, reply, no_args)]
    if any(not isinstance(rule, EventHandlers.Rule) for rule in rules):
        raise TypeError("rules must be a list of Rule")
    plugin_data = PluginManager.get_caller_plugin_data()
    events_matcher = CommandMatcher(plugin_data, rules)
    matchers.append((priority, events_matcher))
    return events_matcher
