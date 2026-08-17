"""宇泰 UT-6801A 串口服务器配置（TCP Server 透传 RS232）。

现场：IP 192.168.0.5（出厂默认 192.168.1.125，需在 Web 改为现场网段），
RS232（DB9）接赛多利斯 MCE524S-2CCN-U。
工作模式选 DataSocket → TCP Server；本地监听端口、串口波特率等在 Web 配置，
须与天平 Device→RS-232 一致。手册见 Dependencies/宇泰/UT-6801A/。
"""
from __future__ import annotations

import os

SERIAL_SERVER_MODEL = "UT-6801A"

SERIAL_SERVER_HOST = os.environ.get("SOLIDDOSER_SERIAL_SERVER_HOST", "192.168.0.5")
# TCP Server 本地监听端口，出厂默认 10000；可用环境变量覆盖
SERIAL_SERVER_PORT = int(os.environ.get("SOLIDDOSER_SERIAL_SERVER_PORT", "10000"))

CONNECT_TIMEOUT_S = 3.0
IO_TIMEOUT_S = 5.0

# 串口侧建议与天平一致（在 UT-6801A Web「串口设置」中配置，非上位机 TCP 参数）
SERIAL_PARAMS_HINT = "9600 8N1（须与天平及 UT-6801A Web 串口设置一致）"
