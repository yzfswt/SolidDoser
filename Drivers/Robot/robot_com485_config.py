"""机器人 RS485 透传公共配置（HitbotInterface com485）。"""
from __future__ import annotations

import os
from pathlib import Path

from Drivers.Robot import robot_config as robot_cfg

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 按顺序查找 HitbotInterface.py；环境变量 HITBOT_SDK_DIR 优先。
_SDK_CANDIDATES = (
    Path(os.environ["HITBOT_SDK_DIR"])
    if os.environ.get("HITBOT_SDK_DIR")
    else None,
    _REPO_ROOT / "Dependencies" / "Z-Arm 2442B" / "python",
    Path(r"D:\HitBot\HitBotStudio\HITBOT\python"),
    Path(r"C:\Program Files\HitbotStudio\SDK"),
)


def _resolve_hitbot_sdk_dir() -> Path:
    for candidate in _SDK_CANDIDATES:
        if candidate is None:
            continue
        if (candidate / "HitbotInterface.py").is_file() and (
            candidate / "small_scara_interface.dll"
        ).is_file():
            return candidate
    return _REPO_ROOT / "Dependencies" / "Z-Arm 2442B" / "python"


HITBOT_SDK_DIR = str(_resolve_hitbot_sdk_dir())

ROBOT_ID = robot_cfg.ROBOT_ID
ROBOT_CONTROLLER_IP = robot_cfg.ROBOT_CONTROLLER_IP
RS485_BAUD = 115200

# 等待 robot_is_connect 返回 1 的最长时间（秒）
ROBOT_CONNECT_TIMEOUT_S = 30.0

# 与慧灵 demo 一致：initial(generation, z_trail)，Z-Arm 2442B 常用 (1, 210)
ROBOT_GENERATION = 1
ROBOT_Z_TRAIL_MM = 210.0

# Modbus 应答轮询间隔（秒）；115200 波特率下通常数毫秒内可收到完整帧
RS485_RECV_POLL_S = 0.005

# 单次 transact 等待应答上限（原 2s 会导致无应答时界面卡顿数秒）
RS485_TRANSACT_TIMEOUT_S = 0.25

# com485_send 返回 -2/-3 为 485 忙；电爪/电缸初始化时适当多试几次
RS485_SEND_RETRY_COUNT = 10
RS485_SEND_RETRY_DELAY_S = 0.1
