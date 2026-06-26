"""机器人状态（调试阶段记录逻辑状态，后续对接真实控制器）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HeldTool(str, Enum):
    NONE = "none"
    PIPETTE = "pipette"
    ELECTRIC_ACTUATOR = "electric_actuator"  # 电缸（电动推杆），非气动气缸 cylinder
    GRIPPER = "gripper"


class AtrLocation(str, Enum):
    IN_SPECTROMETER = "in_spectrometer"
    ON_ROBOT = "on_robot"
    AT_WASH = "at_wash"
    UNKNOWN = "unknown"


@dataclass
class RobotState:
    held_tool: HeldTool = HeldTool.NONE
    pipette_has_tip: bool = False
    pipette_volume_ul: int = 100
    # MCEA 电缸（Modbus ID=2，单位见调试界面）
    pgc_extend_thrust_percent: int = 50
    pgc_extend_target_mm: float = 30.0
    pgc_extend_push_segment_mm: float = 0.0
    pgc_retract_target_mm: float = 0.0
    pgc_enabled: bool = False
    pgc_stroke_initialized: bool = False
    pgc_homed: bool = False
    pgc_homing: bool = False
    pgc_alarm: bool = False
    pgc_moving: bool = False
    pgc_home_status: int = 0
    pgc_run_status: int = 0
    pgc_position_mm: float = 0.0
    pgc_status_summary: str = "未读取"
    # PGC-300-60-W-S 电爪（Modbus ID=1，0x0100 协议）
    gripper_force_percent: int = 30
    gripper_extend_target_mm: float = 60.0
    gripper_extend_push_segment_mm: float = 60.0
    gripper_retract_target_mm: float = 0.0
    gripper_homed: bool = False
    gripper_homing: bool = False
    gripper_moving: bool = False
    gripper_home_status: int = 0
    gripper_run_status: int = 0
    gripper_position_mm: float = 0.0
    gripper_status_summary: str = "未读取"
    atr_location: AtrLocation = AtrLocation.IN_SPECTROMETER
    # 第五轴：汇川 Easy521 + SV630 滑台（Modbus TCP / EtherCAT）
    axis5_servo_enabled: bool = False
    axis5_target_mm: float = 0.0
    axis5_current_mm: float = 0.0
    axis5_velocity_mm_s: float = 50.0
    axis5_homed: bool = False
    axis5_moving: bool = False
    axis5_alarm: bool = False
    axis5_status_summary: str = "未读取"
    last_action: str = ""
    last_message: str = ""
    last_success: bool = True

    def tool_label(self) -> str:
        labels = {
            HeldTool.NONE: "无",
            HeldTool.PIPETTE: "移液枪",
            HeldTool.ELECTRIC_ACTUATOR: "电缸",
            HeldTool.GRIPPER: "电爪",
        }
        return labels.get(self.held_tool, "未知")
