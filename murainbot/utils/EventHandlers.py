"""
事件处理器
"""
import copy
from typing import Literal, Callable, Any, Type

from murainbot.common import save_exc_dump, inject_dependencies
from murainbot.core import EventManager, ConfigManager, PluginManager
from murainbot.utils import EventClassifier, Logger, QQRichText, StateManager

logger = Logger.get_logger()


class Rule:
    """
    Rule基类，请勿直接使用
    """

    def match(self, event_data: EventClassifier.Event) -> bool | tuple[bool, dict[str, Any]]:
        """
        匹配事件
        Args:
            event_data: 事件数据
        Returns:
            是否匹配到事件
            或
            是否匹配到事件，对原始函数进行的依赖注入的参数
        """
        pass

    def __and__(self, other: "Rule"):
        if not isinstance(other, Rule):
            raise TypeError("other must be a Rule")
        return AllRule(self, other)

    def __or__(self, other: "Rule"):
        if not isinstance(other, Rule):
            raise TypeError("other must be a Rule")
        return AnyRule(self, other)


class AnyRule(Rule):
    """
    输入n个rule，若匹配其中任意一个则返回True
    """

    def __init__(self, *rules: Rule):
        self.rules = rules

    def match(self, event_data: EventClassifier.Event):
        rules_kwargs = {}
        flag = False
        for rule in self.rules:
            res = rule.match(event_data)
            if isinstance(res, tuple):
                res, rule_kwargs = res
                rules_kwargs.update(rule_kwargs)
            if res:
                flag = True
                break
        if flag:
            return True, rules_kwargs
        return False


class AllRule(Rule):
    """
    输入n个rule，若匹配所有则返回True
    """

    def __init__(self, *rules: Rule):
        self.rules = rules

    def match(self, event_data: EventClassifier.Event):
        rules_kwargs = {}
        flag = False
        for rule in self.rules:
            res = rule.match(event_data)
            if isinstance(res, tuple):
                res, rule_kwargs = res
                rules_kwargs.update(rule_kwargs)
            if not res:
                flag = True
                break
        if flag:
            return False
        return True, rules_kwargs


class KeyValueRule(Rule):
    """
    键值规则
    检测event data中的某个键的值是否满足要求
    """

    def __init__(self, key, value, model: Literal["eq", "ne", "in", "not in", "func"],
                 func: Callable[[Any, Any], bool] = None):
        """
        Args:
            key: 键
            value: 值
            model: 匹配模式(可选: eq, ne, in, not in, func)
            func: 函数（仅在 model 为 func 时有效，输入为 (event_data.get(key), value)，返回 bool）
        """
        self.key = key
        self.value = value
        self.model = model
        if model == "func" and func is None:
            raise ValueError("if model is func, func must be a callable")
        self.func = func

    def match(self, event_data: EventClassifier.Event):
        try:
            match self.model:
                case "eq":
                    return event_data.get(self.key) == self.value
                case "ne":
                    return event_data.get(self.key) != self.value
                case "in":
                    return self.value in event_data.get(self.key)
                case "not in":
                    return self.value not in event_data.get(self.key)
                case "func":
                    return self.func(event_data.get(self.key), self.value)
            return None
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"执行匹配事件器时出错 {event_data}")
            else:
                dump_path = None
            logger.error(f"执行匹配事件器时出错 {event_data}: {repr(e)}"
                         f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                         exc_info=True)
            return False


class FuncRule(Rule):
    """
    函数规则
    检测event data是否满足函数
    """

    def __init__(self, func: Callable[[Any], bool]):
        """
        Args:
            func: 用于检测函数（输入为 event_data， 返回 bool）
        """
        self.func = func

    def match(self, event_data: EventClassifier.Event):
        try:
            return self.func(event_data)
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"执行匹配事件器时出错 {event_data}")
            else:
                dump_path = None

            logger.error(f"执行匹配事件器时出错 {event_data}: {repr(e)}"
                         f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                         exc_info=True
                         )
            return False


class CommandRule(Rule):
    """
    命令规则
    用于匹配命令

    默认匹配：命令起始符 + 命令 和 命令起始符 + 别名。
    若消息前带有 @bot 时，可直接匹配 命令本身 和 别名，无需命令起始符。

    会自动移除消息中的 @bot 和命令起始符，同时会自动将 别名 替换为 命令本身，以简化插件处理逻辑。
    """

    def __init__(
            self,
            command: str,
            aliases: set[str] = None,
            command_start: list[str] = None,
            reply: bool = False,
            no_args: bool = False,
    ):
        """
        Args:
            command: 命令
            aliases: 命令别名
            command_start: 命令起始符（不填写默认为配置文件中的command_start）
            reply: 是否可包含回复（默认否）
            no_args: 是否不需要命令参数（即消息只能完全匹配命令，不包含其他的内容）
        """
        if aliases is None:
            aliases = set()
        if command_start is None:
            command_start = ConfigManager.GlobalConfig().command.command_start
        if any(_ in command and _ for _ in ['[', ']'] + command_start):
            raise ValueError("command cannot contain [ or ]")
        if command in aliases:
            raise ValueError("command cannot be an alias")

        self.command = command
        self.aliases = aliases
        self.command_start = command_start
        self.reply = reply
        self.no_args = no_args

    def match(self, event_data: EventClassifier.MessageEvent):
        # 检查是否是消息事件
        if not isinstance(event_data, EventClassifier.MessageEvent):
            logger.warning(f"event {event_data} is not a MessageEvent, cannot match command")
            return False

        # 复制一份消息段
        segments = copy.deepcopy(event_data.message.rich_array)

        # 初始化是否@了机器人以及回复消息段的变量
        is_at = False
        reply_segment = None

        # 检查消息是否以回复形式开始
        if (
                self.reply and
                len(segments) > 0 and
                isinstance(segments[0], QQRichText.Reply)
        ):
            reply_segment = segments[0]
            segments = segments[1:]

        # 检查消息是否以@机器人开始
        if (
                len(segments) > 0 and
                isinstance(segments[0], QQRichText.At) and
                str(segments[0].data.get("qq")) == str(event_data.self_id)
        ):
            segments = segments[1:]
            is_at = True

        string_message = str(QQRichText.QQRichText(*segments).strip())

        # 生成所有可能的命令前缀组合，包括命令起始符和别名
        commands = [_ + self.command for _ in self.command_start]
        if is_at:
            # 如果消息前面有at，则不需要命令起始符
            commands += [self.command] + [alias for alias in self.aliases]

        # 添加所有别名的命令前缀组合
        commands += [_ + alias for alias in self.aliases for _ in self.command_start]

        if self.no_args:
            # 检查消息是否以任何预设命令前缀开始
            if any(string_message == _ for _ in commands):
                # 移除命令前缀
                for start in self.command_start:
                    if string_message.startswith(start):
                        string_message = string_message[len(start):]
                        break
                # 替换别名为主命令
                for alias in self.aliases:
                    if string_message == alias:
                        string_message = self.command + string_message[len(alias):]
                        break
            else:
                return False

        else:
            # 检查消息是否以任何预设命令前缀开始
            if any(string_message.startswith(_) for _ in commands):
                # 移除命令前缀
                for start in self.command_start:
                    if string_message.startswith(start):
                        string_message = string_message[len(start):]
                        break
                # 替换别名为主命令
                for alias in self.aliases:
                    if string_message.startswith(alias):
                        string_message = self.command + string_message[len(alias):]
                        break
            else:
                return False

        # 更新消息对象
        message = QQRichText.QQRichText(string_message)

        # 将回复消息段添加到消息段列表中(如果有)
        if reply_segment is not None:
            res_message = QQRichText.QQRichText(reply_segment, message)
        else:
            res_message = message

        event_data.message = res_message
        event_data.raw_message = string_message
        return True, {"command_message": message}


def _to_me(event_data: EventClassifier.MessageEvent):
    """
    判断是否是@自己或是私聊
    Args:
        event_data: 事件数据
    Returns:
        是否是@自己或是私聊
    """
    if not isinstance(event_data, EventClassifier.MessageEvent):
        logger.warning(f"event {event_data} is not a MessageEvent, cannot match to_me")
        return False
    if event_data.is_private:
        return True
    if event_data.is_group:
        for rich in event_data.message.rich_array:
            if (isinstance(rich, QQRichText.At) and str(rich.data.get("qq")) ==
                    str(ConfigManager.GlobalConfig().account.user_id)):
                return True
    return False


to_me = FuncRule(_to_me)


class Matcher:
    """
    事件匹配器
    """

    def __init__(self, plugin_data, rules: list[Rule] = None):
        rules = rules if rules else []
        if any(not isinstance(rule, Rule) for rule in rules):
            raise TypeError("rules must be a list of Rule")
        self.rules = rules
        self.plugin_data = plugin_data
        self.handlers = []

    def register_handler(self, priority: int = 0, rules: list[Rule] = None, *args, **kwargs):
        """
        注册事件处理器
        如果注册的处理器返回True，则事件传播将被阻断
        Args:
            priority: 事件优先级
            rules: 匹配规则
        """
        if rules is None:
            rules = []
        if any(not isinstance(rule, Rule) for rule in rules):
            raise TypeError("rules must be a list of Rule")

        def wrapper(func):
            self.handlers.append((priority, rules, func, args, kwargs))
            return func

        return wrapper

    def check_match(self, event_data: EventClassifier.Event) -> tuple[bool, dict | None]:
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
            logger.error(f"匹配事件处理器时出错: {repr(e)}", exc_info=True)
            return False, None
        return True, rules_kwargs

    def match(self, event_data: EventClassifier.Event, rules_kwargs: dict):
        """
        匹配事件处理器
        Args:
            event_data: 事件数据
            rules_kwargs: 规则返回的注入参数
        """
        for priority, rules, handler, args, kwargs in sorted(self.handlers, key=lambda x: x[0], reverse=True):
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
                        handler_kwargs["group_state"] = StateManager.get_state(f"g{event_data.group_id}", self.plugin_data)

                handler_kwargs.update(rules_kwargs)
                handler_kwargs = inject_dependencies(handler, handler_kwargs)

                result = handler(event_data, *args, **handler_kwargs)

                if result is True:
                    logger.debug(f"处理器 {handler.__name__} 阻断了事件 {event_data} 的传播")
                    return  # 阻断同一 Matcher 内的传播
            except Exception as e:
                if ConfigManager.GlobalConfig().debug.save_dump:
                    dump_path = save_exc_dump(f"执行匹配事件或执行处理器时出错 {event_data}")
                else:
                    dump_path = None
                logger.error(
                    f"执行匹配事件或执行处理器时出错 {event_data}: {repr(e)}"
                    f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                    exc_info=True
                )


events_matchers: dict[str, dict[Type[EventClassifier.Event], list[tuple[int, Matcher]]]] = {}


def _on_event(event_data, path):
    for priority, matcher in sorted(events_matchers[path][event_data.__class__], key=lambda x: x[0], reverse=True):
        matcher_event_data = event_data.__class__(event_data.event_data)
        is_match, rules_kwargs = matcher.check_match(matcher_event_data)
        if is_match:
            matcher.match(matcher_event_data, rules_kwargs)


def on_event(event: Type[EventClassifier.Event], priority: int = 0, rules: list[Rule] = None):
    """
    注册事件处理器
    Args:
        event: 事件类型
        priority: 事件优先级
        rules: 匹配规则
    Returns:
        事件处理器
    """
    if rules is None:
        rules = []
    if any(not isinstance(rule, Rule) for rule in rules):
        raise TypeError("rules must be a list of Rule")
    if not issubclass(event, EventClassifier.Event):
        raise TypeError("event must be an instance of EventClassifier.Event")
    plugin_data = PluginManager.get_caller_plugin_data()
    path = plugin_data["path"]
    if path not in events_matchers:
        events_matchers[path] = {}
    if event not in events_matchers[path]:
        events_matchers[path][event] = []
        EventManager.event_listener(event, path=path)(_on_event)
    events_matcher = Matcher(plugin_data, rules)
    events_matchers[path][event].append((priority, events_matcher))
    return events_matcher
