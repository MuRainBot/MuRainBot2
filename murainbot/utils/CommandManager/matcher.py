"""
命令管理器的命令匹配器
"""
import dataclasses
import inspect
import time
from typing import Generator, Any, Callable

from murainbot.utils import EventClassifier, QQRichText, Actions, EventHandlers, TimerManager, StateManager

from murainbot.utils.CommandManager import BaseArg, parsing_command_def, CommandManager, logger, NotMatchCommandError, \
    CommandMatchError
from murainbot.common import save_exc_dump, inject_dependencies

from murainbot.core import EventManager, ConfigManager, PluginManager
from murainbot.core.ThreadPool import async_task

__all__ = [
    "CommandMatcher",
    "WaitHandler",
    "WaitCommand",
    "WaitAction",
    "WaitTimeoutError",
    "CommandEvent",
    "on_command"
]


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


class WaitTimeoutError(Exception):
    """
    等待超时异常
    """


@dataclasses.dataclass
class WaitHandler:
    """
    等待中的处理器的数据
    """
    generator: Generator["WaitAction", tuple[EventManager.Event | None, Any], Any]
    raw_event_data: CommandEvent
    raw_handler: Callable[[...], ...]
    wait_timeout: int | None = 60


@dataclasses.dataclass
class WaitAction:
    """
    等待操作
    """
    wait_trigger: Callable[["CommandMatcher.TriggerEvent"], ...]
    timeout: int | None = 60
    matcher: "CommandMatcher" = dataclasses.field(init=False)
    wait_handler: WaitHandler = dataclasses.field(init=False)

    def set_data(self, matcher: "CommandMatcher", wait_handler: WaitHandler):
        """
        设置数据，由框架调用，**无需插件开发者手动调用**
        Args:
            matcher: 匹配器
            wait_handler: 等待处理器
        """
        self.matcher = matcher
        self.wait_handler = wait_handler


@dataclasses.dataclass
class WaitCommand(WaitAction):
    """
    等待命令
    """
    wait_command_def: BaseArg | str | None = None
    user_id: int | None = -1  # -1则为当前这个事件的用户，None则为任意用户，如果是群聊则仅限该群
    wait_trigger: Callable[["CommandMatcher.TriggerEvent"], ...] = dataclasses.field(init=False)

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

    def trigger(trigger_event: CommandMatcher.TriggerEvent):
        def on_evnet(event_data: CommandEvent):
            if not wait_action.wait_handler:
                raise RuntimeError("等待处理器未设置")
            handler = wait_action.wait_handler
            wait_user_id = handler.raw_event_data.user_id if wait_action.user_id == -1 else wait_action.user_id
            if handler.raw_event_data.is_group and event_data.get("group_id") != handler.raw_event_data["group_id"]:
                return
            if wait_user_id is None or wait_user_id == event_data.user_id:
                if isinstance(wait_command, CommandManager):
                    try:
                        kwargs, _, _ = wait_command.run_command(event_data.message)
                    except Exception:
                        return
                    trigger_event.set_data((event_data, kwargs))
                EventManager.unregister_listener(CommandEvent, on_evnet)
                trigger_event.call()

        EventManager.event_listener(CommandEvent)(on_evnet)

    return trigger


def throw_timeout_error(matcher: "CommandMatcher", handler: WaitHandler):
    """
    抛出超时错误
    Args:
        matcher: 等待的处理器所属的匹配器
        handler: 等待的处理器

    Returns:
        None
    """
    for waiting_handler in matcher.waiting_handlers:
        if waiting_handler is handler:
            try:
                waiting_handler.generator.throw(WaitTimeoutError("等待超时"))
            except StopIteration:
                pass
            try:
                matcher.waiting_handlers.remove(waiting_handler)
            except ValueError:
                pass
            return


class CommandMatcher(EventHandlers.Matcher):
    """
    命令匹配器
    """

    class TriggerEvent(EventManager.Event):
        def __init__(self, wait_handler: WaitHandler):
            self.wait_handler = wait_handler
            self.data = None

        def set_data(self, data):
            """
            设置返回数据
            Args:
                data: 返回数据
            """
            self.data = data

    def __init__(self, plugin_data, rules: list[EventHandlers.Rule] = None):
        super().__init__(plugin_data, rules)
        self.command_manager = CommandManager()
        self.waiting_handlers: list[WaitHandler] = []

    def _on_trigger_event(self, wait_handler: WaitHandler):
        @async_task
        def _on_event(event: CommandMatcher.TriggerEvent):
            nonlocal wait_handler
            if event.wait_handler is not wait_handler:
                return None
            # if event.new_event_data:
            # 神奇妙妙修改局部变量小魔法(弃用，这东西还是有点过于魔法了，还是正常点好了)
            # try:
            #     frame = wait_handler.generator.gi_frame
            #     if frame is None:
            #         logger.warning(f"在尝试修改事件处理器时事件数据时发生错误: 帧已不存在", stack_info=True)
            #     else:
            #         f_locals = frame.f_locals
            #
            #         if 'event_data' in f_locals:
            #             f_locals['event_data'] = event.new_event_data
            #
            #             ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object(frame), ctypes.c_int(0))
            # except Exception as e:
            #     logger.error(f"在尝试修改事件处理器时事件数据时发生错误: {repr(e)}", exc_info=True)

            # print(wait_handler, event.wait_handler, self.waiting_handlers)
            try:
                wait_action = wait_handler.generator.send(event.data)
            except StopIteration:
                return True
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(
                        f"执行等待处理器 {wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} 发生错误")
                else:
                    dump_path = None
                logger.error(
                    f"执行等待处理器 {wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} 发生错误: {repr(e)}"
                    f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                    exc_info=True
                )
                return True
            finally:
                self.waiting_handlers.remove(wait_handler)
                EventManager.unregister_listener(self.TriggerEvent, _on_event)

            if not isinstance(wait_action, WaitAction):
                wait_handler.generator.throw(TypeError("wait_action must be a WaitAction"))
                return True

            wait_handler = WaitHandler(
                generator=wait_handler.generator,
                raw_event_data=wait_handler.raw_event_data,
                raw_handler=wait_handler.raw_handler,
                wait_timeout=wait_action.timeout
            )
            wait_action.set_data(self, wait_handler)
            self.waiting_handlers.append(wait_handler)
            if wait_handler.wait_timeout is not None:
                TimerManager.delay(
                    wait_handler.wait_timeout,
                    throw_timeout_error,
                    matcher=self,
                    handler=wait_handler
                )
            targeter_event = self.TriggerEvent(wait_handler)
            EventManager.event_listener(self.TriggerEvent)(self._on_trigger_event(wait_handler))
            t = time.perf_counter()
            wait_action.wait_trigger(targeter_event)
            if time.perf_counter() - t > 0.5:
                logger.warning(f"在执行处理器"
                               f" {wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} "
                               f"时，其返回的等待处理器触发器"
                               f"{wait_action.wait_trigger.__module__}.{wait_action.wait_trigger.__name__}"
                               f"初始化时间过长，"
                               f"耗时: {round((time.perf_counter() - t) * 1000, 2)}ms，"
                               f"等待处理器运行请仅进行初始化，不要在其中执行耗时操作，如果的确有需求请使用"
                               f"@async_task装饰器，让其运行在线程池的其他线程中")
            return True

        return _on_event

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
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"在事件 {event_data.event_data} 中匹配事件处理器时出错")
            else:
                dump_path = None
            logger.error(
                f"在事件 {event_data.event_data} 中匹配事件处理器时出错: {repr(e)}"
                f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                exc_info=True
            )
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
                    rules_kwargs["command_message"])
            except NotMatchCommandError as e:
                logger.error(f"未匹配到命令: {repr(e)}", exc_info=True)
                event_data.reply(f"未匹配到命令: {e}")
                return None
            except CommandMatchError as e:
                logger.info(f"命令匹配错误: {repr(e)}", exc_info=True)
                event_data.reply(f"命令匹配错误，请检查命令是否正确: {e}")
                return None
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(f"在事件 {event_data.event_data} 中进行命令处理发生未知错误")
                else:
                    dump_path = None
                logger.error(
                    f"在事件 {event_data.event_data} 中进行命令处理发生未知错误: {repr(e)}"
                    f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                    exc_info=True
                )
                event_data.reply(f"命令处理发生未知错误: {repr(e)}")
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

                # 检查是否是生成器
                if inspect.isgeneratorfunction(handler):
                    generator = handler(event_data, *args, **handler_kwargs)
                    try:
                        wait_action = generator.send(None)
                    except StopIteration as e:
                        if e.value is True:
                            return None
                        else:
                            wait_action = None

                    if wait_action is not None:
                        if not isinstance(wait_action, WaitAction):
                            generator.throw(TypeError("wait_action must be a WaitAction"))
                            return True

                        wait_handler = WaitHandler(
                            generator=generator,
                            raw_event_data=event_data,
                            raw_handler=handler,
                            wait_timeout=wait_action.timeout
                        )
                        wait_action.set_data(self, wait_handler)
                        self.waiting_handlers.append(wait_handler)
                        if wait_handler.wait_timeout is not None:
                            TimerManager.delay(
                                wait_handler.wait_timeout,
                                throw_timeout_error,
                                matcher=self,
                                handler=wait_handler
                            )
                        targeter_event = self.TriggerEvent(wait_handler)
                        EventManager.event_listener(self.TriggerEvent)(self._on_trigger_event(wait_handler))
                        t = time.perf_counter()
                        wait_action.wait_trigger(targeter_event)
                        if time.perf_counter() - t > 0.5:
                            logger.warning(f"在执行处理器"
                                           f" {wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} "
                                           f"时，其返回的等待处理器触发器"
                                           f"{wait_action.wait_trigger.__module__}.{wait_action.wait_trigger.__name__}"
                                           f"初始化时间过长，"
                                           f"耗时: {round((time.perf_counter() - t) * 1000, 2)}ms，"
                                           f"等待处理器运行请仅进行初始化，不要在其中执行耗时操作，如果的确有需求请使用"
                                           f"@async_task装饰器，让其运行在线程池的其他线程中")
                    result = False
                else:
                    result = handler(event_data, *args, **handler_kwargs)

                if result is True:
                    logger.debug(f"处理器 {handler.__module__}.{handler.__name__} 阻断了事件 {event_data} 的传播")
                    return None  # 阻断同一 Matcher 内的传播
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(f"执行匹配事件或执行处理器 {handler.__module__}.{handler.__name__} "
                                              f"时出错 {event_data}")
                else:
                    dump_path = None
                logger.error(
                    f"执行匹配事件或执行处理器 {handler.__module__}.{handler.__name__} 时出错 {event_data}: {repr(e)}"
                    f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                    exc_info=True
                )
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
