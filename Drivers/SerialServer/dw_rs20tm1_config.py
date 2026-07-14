"""达而稳 DW-RS20TM1 串口服务器配置（TCP 透传 RS232）。

现场：IP 192.168.0.5，RS232 接赛多利斯 MCE524S-2CCN-U。
TCP 端口、串口波特率等用 NetModuleConfig.exe 配置，须与天平 Device→RS-232 一致。
手册见 Dependencies/达而稳/DW-RS20TM1/。
"""
from __future__ import annotations

import os

SERIAL_SERVER_MODEL = "DW-RS20TM1"

SERIAL_SERVER_HOST = os.environ.get("SOLIDDOSER_SERIAL_SERVER_HOST", "192.168.0.5")
# 本地监听端口以 NetModuleConfig 实际配置为准；可用环境变量覆盖
SERIAL_SERVER_PORT = int(os.environ.get("SOLIDDOSER_SERIAL_SERVER_PORT", "10001"))

CONNECT_TIMEOUT_S = 3.0
IO_TIMEOUT_S = 5.0

# 串口侧建议与天平一致（在串口服务器中配置，非上位机 TCP 参数）
SERIAL_PARAMS_HINT = "9600 8N1（须与天平及 NetModuleConfig 一致）"
