"""SolidDoser PLC 通讯配置（汇川 AM600-CPU1608TN）。

本项目由原 FTIR（Easy521-0808TN @ 192.168.0.4）迁移而来。
上位机通过 Modbus TCP 访问 AM600 的 M/D 软元件，由 PLC 程序驱动 EtherCAT 轴与 Q 点输出。

点表见 Dependencies/汇川/AM600-CPU1608TN/SOLIDDOSER_MOTION_PLC_INTERFACE.md
"""
from __future__ import annotations

import os

PLC_MODEL = "AM600-CPU1608TN"

# 现场 AM600 默认 IP；可通过环境变量 SOLIDDOSER_PLC_HOST 覆盖
PLC_HOST = os.environ.get("SOLIDDOSER_PLC_HOST", "192.168.0.4")
PLC_PORT = int(os.environ.get("SOLIDDOSER_PLC_PORT", "502"))
MODBUS_SLAVE_ID = int(os.environ.get("SOLIDDOSER_PLC_SLAVE_ID", "1"))

# 兼容旧代码中 Common.Global.PLC_ADDRESS / PLC_PORT 的引用
PLC_ADDRESS = PLC_HOST
PLC_PORT_STR = str(PLC_PORT)
