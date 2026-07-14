"""赛多利斯 Cubis II MCE524S-2CCN-U 天平配置（SBI，经 DW-RS20TM1 RS232 透传）。"""
from __future__ import annotations

BALANCE_MODEL = "MCE524S-2CCN-U"
BALANCE_USE_SIMULATION = False

# SBI 控制命令：Esc + 字符，可选 CR LF
CMD_PRINT = b"\x1bP\r\n"  # Esc P：打印/读当前显示重量
CMD_TARE = b"\x1bT\r\n"  # Esc T：去皮
CMD_ZERO = b"\x1bV\r\n"  # Esc V：清零
CMD_RESTART = b"\x1bS\r\n"  # Esc S：重启
