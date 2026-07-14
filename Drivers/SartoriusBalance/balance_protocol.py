"""赛多利斯 SBI 协议解析（16/22 字符重量行）。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# 例: "+  153.0234 g" / "N +  153.0234 g" / "+     253 pcs"
_WEIGHT_RE = re.compile(
    r"(?P<id>[A-Za-z0-9%]{0,6})\s*"
    r"(?P<sign>[+\- ])\s*"
    r"(?P<value>[0-9.]+)\s*"
    r"(?P<unit>[A-Za-z%]+)?\s*$"
)


@dataclass(frozen=True)
class BalanceReading:
    raw: str
    value: Optional[float]
    unit: str
    id_code: str
    display: str


def parse_sbi_line(raw: bytes | str) -> Tuple[Optional[BalanceReading], str]:
    if isinstance(raw, bytes):
        text = raw.decode("ascii", errors="replace")
    else:
        text = raw
    line = text.replace("\r", "").replace("\n", "").strip()
    if not line:
        return None, "天平返回空行"

    upper = line.upper()
    if "STAT" in upper and ("H" in upper or "L" in upper or "--" in line):
        return (
            BalanceReading(raw=line, value=None, unit="", id_code="Stat", display=line),
            "",
        )
    if "ERR" in upper or re.search(r"\bE\s*\d+", upper):
        return None, f"天平错误：{line}"

    match = _WEIGHT_RE.search(line)
    if not match:
        return (
            BalanceReading(raw=line, value=None, unit="", id_code="", display=line),
            "",
        )

    sign = match.group("sign") or "+"
    try:
        value = float(match.group("value"))
    except ValueError:
        return None, f"无法解析重量：{line}"
    if sign.strip() == "-":
        value = -value
    unit = (match.group("unit") or "").strip()
    id_code = (match.group("id") or "").strip()
    display = f"{value:g} {unit}".strip() if unit else f"{value:g}"
    return (
        BalanceReading(
            raw=line,
            value=value,
            unit=unit,
            id_code=id_code,
            display=display,
        ),
        "",
    )
