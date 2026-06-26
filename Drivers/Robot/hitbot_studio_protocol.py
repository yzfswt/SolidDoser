"""HitbotStudio 客户端 / 变量服务器报文解析与组包。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class GlobalVarsMessage:
    header: str = ""
    robot_id: int = 0
    kind: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    variable_order: List[Tuple[str, str]] = field(default_factory=list)
    raw: str = ""


def _split_fields(payload: str) -> List[str]:
    return [p.strip() for p in payload.split(",") if p.strip() != ""]


def parse_message(data: str) -> Optional[GlobalVarsMessage]:
    """解析客户端 globalvars 报文（末尾 ; 或 \\r\\n）。"""
    text = data.strip().replace("\r\n", "").replace("\n", "")
    if not text:
        return None
    if ";" in text:
        text = text.split(";", 1)[0]
    parts = _split_fields(text)
    if len(parts) < 3:
        return None
    msg = GlobalVarsMessage(
        header=parts[0],
        robot_id=int(parts[1]) if parts[1].isdigit() else 0,
        kind=parts[2],
        raw=data.strip(),
    )
    for token in parts[3:]:
        if "#" not in token:
            continue
        name, value = token.split("#", 1)
        name = name.strip()
        value = value.strip()
        msg.variables[name] = value
        msg.variable_order.append((name, value))
    return msg


def build_globalvars_response(
    header: str,
    robot_id: int,
    values: Dict[str, int | str],
    *,
    variable_order: Optional[List[Tuple[str, str]]] = None,
    terminator: str = "",
) -> str:
    """组包 globalvars 响应。

    Studio 客户端说明：请求以 ``;`` 结尾，响应 **不要** 分号。
    """
    body = [header, str(robot_id), "globalvars"]
    if variable_order:
        for name, _old in variable_order:
            if name in values:
                body.append(f"{name}#{values[name]}")
        for name, val in values.items():
            if not any(n == name for n, _ in variable_order):
                body.append(f"{name}#{val}")
    else:
        for key, value in values.items():
            body.append(f"{key}#{value}")
    text = ",".join(body)
    if terminator == ";\r\n":
        return text + ";\r\n"
    if terminator == ";":
        return text + ";"
    if terminator == "\r\n":
        return text + "\r\n"
    return text + terminator


def build_set_var_response(values: Dict[str, int | str]) -> str:
    """变量服务器协议（初始化里「启用变量服务器」）回复格式。"""
    pairs = [f"{name}#{values[name]}" for name in values]
    command = "set_var," + ",".join(pairs) + "\r\n"
    return f"{len(command)},{command}"


def parse_int_var(
    msg: GlobalVarsMessage,
    name: str,
    default: int = 0,
    aliases: tuple[str, ...] = (),
) -> int:
    for key in (name, *aliases):
        raw = msg.variables.get(key)
        if raw is None or raw == "":
            continue
        try:
            return int(float(raw))
        except ValueError:
            continue
    return default
