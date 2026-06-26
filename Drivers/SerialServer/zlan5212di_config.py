"""ZLAN5212DI 串口服务器 RS485 透传配置（TCP 客户端 → 设备 TCP 服务端）。"""
from __future__ import annotations

import os

# 第 1 路 RS485（PORT1）；第 2 路见 ZLAN5212DI_PORT2
SERIAL_SERVER_HOST = os.environ.get("ZLAN5212DI_HOST", "192.168.0.5")

# PORT1 本地端口：出厂/现场配置为准（说明书示例 4196 或 5001）
SERIAL_SERVER_PORT = int(os.environ.get("ZLAN5212DI_PORT", "4196"))

# 串口侧参数须在 ZLVircom / Web 中与下位机一致（115200 8N1）
RS485_BAUD = 115200

# TCP 连接超时（秒）
CONNECT_TIMEOUT_S = 5.0

# socket recv 单次超时；transact 内循环轮询
SOCKET_RECV_TIMEOUT_S = 0.05

RS485_RECV_POLL_S = 0.005
RS485_TRANSACT_TIMEOUT_S = 0.25

SEND_RETRY_COUNT = 5
SEND_RETRY_DELAY_S = 0.05
