"""基恩士 SR-X100WP 扫码枪通讯配置（TCP ASCII）。"""
from __future__ import annotations

import os

SCANNER_MODEL = "SR-X100WP"

# 默认 IP 请按现场扫码枪网络修改，或通过环境变量覆盖
SCANNER_HOST = os.environ.get("SOLIDDOSER_SCANNER_HOST", "192.168.0.3")
SCANNER_PORT = int(os.environ.get("SOLIDDOSER_SCANNER_PORT", "9004"))

CONNECT_TIMEOUT_S = 3.0
READ_TIMEOUT_S = 5.0
# 读码结果返回后，LOFF 等收尾命令的短超时
FOLLOWUP_TIMEOUT_S = 0.2
# 默认去掉 SR-X 附加数据（如 694...:00:100%:23 → 694...）
STRIP_ADDITIONAL_DATA = os.environ.get("SOLIDDOSER_SCANNER_STRIP_ADDITIONAL", "1") != "0"
SCANNER_USE_SIMULATION = False

# Keyence SR 系列常用 ASCII 命令（以 \r 结尾）
CMD_TRIGGER_ONCE = "LON"
CMD_STOP_CONTINUOUS = "LOFF"
