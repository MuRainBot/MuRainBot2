"""
命令管理器的各种参数
"""
import ast
from typing import Union, Any

from murainbot.utils.CommandManager import BaseArg, parsing_command_def, logger
from murainbot.utils import QQRichText

__all__ = [
    "Literal",
    "OptionalArg",
    "SkipOptionalArg",
    "IntArg",
    "TextArg",
    "GreedySegments",
    "GreedyTextArg",
    "AnySegmentArg",
    "ImageSegmentArg",
    "AtSegmentArg",
    "EnumArg",
]


class Literal(BaseArg):
    def __init__(self, arg_name: str, aliases: set[str] = None, next_arg_list=None):
        super().__init__(arg_name, next_arg_list)
        if aliases is None:
            aliases = set()
        self.aliases = aliases
        self.command_list = {self.arg_name, *self.aliases}

    def get_config(self) -> dict:
        """
        获取当前实例的配置
        """
        config = {}
        if self.aliases:
            config["aliases"] = self.aliases
        return config

    def matcher(self, remaining_cmd: QQRichText.QQRichText) -> bool:
        if remaining_cmd.strip().rich_array[0].type == "text":
            return any(remaining_cmd.strip().rich_array[0].data.get("text").startswith(_) for _ in self.command_list)
        return False

    def handler(self, remaining_cmd: QQRichText.QQRichText) -> tuple[dict[str, Any], QQRichText.QQRichText | None]:
        text_to_match = remaining_cmd.strip().rich_array[0].data.get("text", "")

        sorted_commands = sorted(self.command_list, key=len, reverse=True)

        matched_command = None
        for command in sorted_commands:
            if text_to_match.startswith(command):
                matched_command = command
                break

        if matched_command is None:
            raise ValueError(f"命令不匹配当前任意参数: {', '.join(self.command_list)}")

        return {}, QQRichText.QQRichText(
            QQRichText.Text(text_to_match.split(matched_command, 1)[-1]),
            *remaining_cmd.rich_array[1:])


class OptionalArg(BaseArg):
    """
    一个包装器，用来标记一个参数是可选的。
    """

    def __init__(self, arg: BaseArg, default: Union[str, bytes, int, float, tuple, list, dict, set, bool, None] = None):
        if not isinstance(default, (str, bytes, int, float, tuple, list, dict, set, bool, type(None))):
            raise TypeError("Default value must be a basic type.(strings, bytes, numbers, tuples, lists, dicts, "
                            "sets, booleans, and None.)")
        if not isinstance(arg, BaseArg):
            raise TypeError("Argument must be an instance of BaseArg.")
        # 名字继承自被包装的参数
        super().__init__(arg.arg_name)
        self.wrapped_arg = arg
        self.default = default
        # 可选参数也可能有自己的子节点
        self.next_arg_list = self.wrapped_arg.next_arg_list

    def node_str(self):
        return f"Optional({self.wrapped_arg.node_str()}, default={self.default!r})"

    def __str__(self):
        return (f"[{self.wrapped_arg.arg_name}: {self.wrapped_arg.__class__.__module__}."
                f"{self.wrapped_arg.__class__.__name__}={self.default!r}{self.wrapped_arg.config_str(", ")}]")

    def handler(self, remaining_cmd: QQRichText.QQRichText) -> tuple[dict[str, Any], QQRichText.QQRichText | None]:
        return self.wrapped_arg.handler(remaining_cmd)


class SkipOptionalArg(BaseArg):
    def __init__(self, arg: BaseArg, default: Union[str, bytes, int, float, tuple, list, dict, set, bool, None] = None):
        if not isinstance(default, (str, bytes, int, float, tuple, list, dict, set, bool, type(None))):
            raise TypeError("Default value must be a basic type.(strings, bytes, numbers, tuples, lists, dicts, "
                            "sets, booleans, and None.)")
        if not isinstance(arg, BaseArg):
            raise TypeError("Argument must be an instance of BaseArg.")
        # 名字继承自被包装的参数
        super().__init__(arg.arg_name)
        self.wrapped_arg = arg
        self.default = default
        # 可选参数也可能有自己的子节点
        self.next_arg_list = self.wrapped_arg.next_arg_list

    def get_config(self):
        return {"arg": str(self.wrapped_arg), "default": self.default}

    @classmethod
    def get_instance_from_config(cls, arg_name, config: dict[str, str]) -> "BaseArg":
        config = {
            k: ast.literal_eval(v)
            for k, v in config.items()
        }
        # print(config["arg"])
        config["arg"] = parsing_command_def(config["arg"])
        return cls(**config)

    def node_str(self):
        return f"SkipOptional({self.wrapped_arg.node_str()}, default={self.default!r})"

    def handler(self, remaining_cmd: QQRichText.QQRichText) -> tuple[dict[str, Any], QQRichText.QQRichText | None]:
        try:
            return self.wrapped_arg.handler(remaining_cmd)
        except Exception as e:
            logger.debug(f"SkipOptionalArg内的参数处理出错，自动跳过: {repr(e)}", exc_info=True)
            return {self.wrapped_arg.arg_name: self.default}, remaining_cmd


class IntArg(BaseArg):
    def _handler(self, match_parameters):
        if match_parameters.type == "text":
            try:
                return {self.arg_name: int(match_parameters.data.get("text"))}
            except ValueError:
                raise ValueError(f"参数 {self.arg_name} 的值必须是整数，却得到: {match_parameters}")
        else:
            raise ValueError(f"参数 {self.arg_name} 的类型必须是文本")


class TextArg(BaseArg):
    def _handler(self, match_parameters):
        if match_parameters.type == "text":
            return {self.arg_name: match_parameters.data.get("text")}
        else:
            raise ValueError(f"参数 {self.arg_name} 的类型必须是文本")


class GreedySegments(BaseArg):
    def handler(self, remaining_cmd):
        return {self.arg_name: remaining_cmd}, None


class GreedyTextArg(BaseArg):
    def handler(self, remaining_cmd):
        if remaining_cmd.type == "text":
            return ({self.arg_name: remaining_cmd.data.get("text")},
                    QQRichText.QQRichText(*remaining_cmd.rich_array[1:]))
        else:
            raise ValueError(f"参数 {self.arg_name} 的类型必须是文本")


class AnySegmentArg(BaseArg):
    def _handler(self, match_parameters: QQRichText.Segment) -> dict[str, Any]:
        return {self.arg_name: match_parameters}


class ImageSegmentArg(BaseArg):
    def _handler(self, match_parameters: QQRichText.Segment) -> dict[str, Any]:
        if match_parameters.type == "image":
            return {self.arg_name: match_parameters}
        else:
            raise ValueError(f"参数 {self.arg_name} 的类型必须是图片")


class AtSegmentArg(BaseArg):
    def _handler(self, match_parameters: QQRichText.Segment) -> dict[str, Any]:
        if match_parameters.type == "at":
            return {self.arg_name: match_parameters}
        else:
            raise ValueError(f"参数 {self.arg_name} 的类型必须是@")


class EnumArg(BaseArg):
    def __init__(self, arg_name, enum_list: list[BaseArg], next_arg_list=None):
        super().__init__(arg_name, next_arg_list)
        self.enum_list = enum_list

    def get_config(self):
        return {"enum_list": [str(enum) for enum in self.enum_list]}

    @classmethod
    def get_instance_from_config(cls, arg_name, config: dict[str, str]) -> "BaseArg":
        config = {
            k: ast.literal_eval(v)
            for k, v in config.items()
        }
        config["enum_list"] = [
            parsing_command_def(enum)
            for enum in config["enum_list"]
        ]
        return cls(arg_name, **config)

    def handler(self, remaining_cmd) -> tuple[dict[str, Any], QQRichText.QQRichText | None]:
        for arg in self.enum_list:
            if arg.matcher(remaining_cmd):
                try:
                    kwargs, remaining_cmd = arg.handler(remaining_cmd)
                    kwargs[self.arg_name] = arg
                    return kwargs, remaining_cmd
                except Exception as e:
                    logger.debug(f"枚举参数匹配错误: {repr(e)}", exc_info=True)
        else:
            raise ValueError(f"不匹配任何参数: {", ".join(str(arg) for arg in self.enum_list)}", self)
