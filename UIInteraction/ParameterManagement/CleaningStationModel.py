"""清洁工位状态（调试界面与 Modbus 驱动同步）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CleaningStationState:
    # 合盖工位（上位机软件定义；发令前将对应值写入 PLC D220）
    rotation_open_position: float = 0.0
    rotation_close_position: float = 90.0
    rotation_velocity: float = 30.0

    # 合盖电机状态（鸣志步进，EtherCAT）
    rotation_servo_enabled: bool = False
    rotation_homed: bool = False
    rotation_at_open: bool = False
    rotation_at_close: bool = False
    rotation_moving: bool = False
    rotation_alarm: bool = False
    rotation_status_summary: str = "未读取"
    rotation_actual_position: float = 0.0

    # 升降工位（上位机软件定义；发令前将对应值写入 PLC D210）
    lift_up_position: float = 0.0
    lift_down_position: float = 80.0
    lift_velocity: float = 50.0

    # 升降电机状态（大寰电缸，EtherCAT）
    lift_servo_enabled: bool = False
    lift_homed: bool = False
    lift_at_up: bool = False
    lift_at_down: bool = False
    lift_moving: bool = False
    lift_alarm: bool = False
    lift_status_summary: str = "未读取"
    lift_actual_position: float = 0.0

    # 泵阀（PLC Y0～Y4，经 M 映射）
    pump_y0_on: bool = False
    pump_y1_on: bool = False
    pump_y2_on: bool = False
    pump_y3_on: bool = False
    pump_y4_on: bool = False

    last_action: str = ""
    last_message: str = ""
    last_success: bool = True

    def pump_summary(self) -> str:
        labels = [
            ("气泵1/Y0", self.pump_y0_on),
            ("气泵2/Y1", self.pump_y1_on),
            ("液泵1/Y2", self.pump_y2_on),
            ("液泵2/Y3", self.pump_y3_on),
            ("废液泵/Y4", self.pump_y4_on),
        ]
        parts = [f"{name}:{'开' if on else '关'}" for name, on in labels]
        return " | ".join(parts)
