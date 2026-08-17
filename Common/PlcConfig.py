"""SolidDoser PLC 通讯配置（汇川 AM600-CPU1608TN）。

上位机通过 Modbus TCP 访问 AM600 的 M/D 软元件，由 PLC 程序驱动 EtherCAT 轴与 Q 点输出。
"""
from __future__ import annotations

import os

PLC_MODEL = "AM600-CPU1608TN"

# 现场 AM600 默认 IP；可通过环境变量 SOLIDDOSER_PLC_HOST 覆盖
PLC_HOST = os.environ.get("SOLIDDOSER_PLC_HOST", "192.168.0.4")
PLC_PORT = int(os.environ.get("SOLIDDOSER_PLC_PORT", "502"))
MODBUS_SLAVE_ID = int(os.environ.get("SOLIDDOSER_PLC_SLAVE_ID", "1"))
