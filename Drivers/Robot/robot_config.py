"""Z-Arm 2442B + HitbotStudio 调度模式配置（模式 1：F99 主流程 + 子流程）。

cmd 编号规则（与 Studio F99 条件一致）：
  1–2   移液枪装取
  3–5   枪头 / 物料
  移液枪操作（初始化/取液/排液/退枪头）由 SolidDoser 直连，不经 Studio
  11–14 电缸（11 取 / 12 放 / 13 用 / 14 洗）
  21–23 电爪（21 取 / 22 放 / 23 用）
  31–33 ATR（31 取 / 32 放 / 33 洗）
"""
from __future__ import annotations

ROBOT_CONTROLLER_IP = "192.168.0.77"
ROBOT_ID = 77

USE_STUDIO_DISPATCH = True

STUDIO_TCP_HOST = "0.0.0.0"
STUDIO_TCP_PORT = 6000
STUDIO_CLIENT_HEADER = ""

STUDIO_RESPONSE_MODE = "globalvars_no_semi"
STUDIO_COMMAND_TIMEOUT_S = 180.0

VAR_CMD = "cmd"
VAR_STATUS = "status"
VAR_PARAM1 = "param1"
VAR_ERR_CODE = "err_code"

WIRE_VAR_CMD = "int-cmd"
WIRE_VAR_STATUS = "int-status"
WIRE_VAR_PARAM1 = "int-param1"
WIRE_VAR_ERR_CODE = "int-err_code"

STATUS_IDLE = 0
STATUS_RUNNING = 1
STATUS_OK = 2
STATUS_FAIL = 3


class RobotCmd:
    NONE = 0

    PICK_PIPETTE = 1
    PLACE_PIPETTE = 2

    PICK_TIP = 3
    PLACE_TIP = 4
    PICK_MATERIAL = 5

    PICK_ELECTRIC_ACTUATOR = 11
    PLACE_ELECTRIC_ACTUATOR = 12
    USE_ELECTRIC_ACTUATOR = 13
    CLEAN_ELECTRIC_ACTUATOR = 14

    PICK_GRIPPER = 21
    PLACE_GRIPPER = 22
    USE_GRIPPER = 23

    PICK_ATR = 31
    PLACE_ATR = 32
    CLEAN_ATR = 33

    GO_SAFE = 99


ACTION_TO_CMD: dict[str, int] = {
    "pick_pipette": RobotCmd.PICK_PIPETTE,
    "place_pipette": RobotCmd.PLACE_PIPETTE,
    "pick_tip": RobotCmd.PICK_TIP,
    "place_tip": RobotCmd.PLACE_TIP,
    "pick_material": RobotCmd.PICK_MATERIAL,
    "pick_electric_actuator": RobotCmd.PICK_ELECTRIC_ACTUATOR,
    "place_electric_actuator": RobotCmd.PLACE_ELECTRIC_ACTUATOR,
    "use_electric_actuator": RobotCmd.USE_ELECTRIC_ACTUATOR,
    "clean_electric_actuator": RobotCmd.CLEAN_ELECTRIC_ACTUATOR,
    "pick_gripper": RobotCmd.PICK_GRIPPER,
    "place_gripper": RobotCmd.PLACE_GRIPPER,
    "use_gripper": RobotCmd.USE_GRIPPER,
    "pick_atr": RobotCmd.PICK_ATR,
    "place_atr": RobotCmd.PLACE_ATR,
    "clean_atr": RobotCmd.CLEAN_ATR,
}

STUDIO_SKIP_ACTIONS = frozenset({
    "robot_stop",
    "axis5_servo_on",
    "axis5_go_home",
    "axis5_move_to_target",
    "axis5_stop",
    "axis5_refresh_status",
    "pipette_init",
    "pipette_aspirate",
    "pipette_dispense",
    "pipette_eject_tip",
    "electric_actuator_extend",
    "electric_actuator_retract",
    "electric_actuator_stroke_init",
    "electric_actuator_home",
    "electric_actuator_enable",
    "electric_actuator_disable",
    "electric_actuator_clear_alarm",
    "electric_actuator_refresh_status",
    "gripper_init",
    "gripper_home",
    "gripper_extend",
    "gripper_retract",
    "gripper_refresh_status",
})
