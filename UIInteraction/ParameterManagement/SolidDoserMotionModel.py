"""SolidDoser 主运动轴状态（调试界面与 Modbus 驱动同步）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from Drivers.SolidDoserMotion import motion_config as cfg


@dataclass
class AxisMotionState:
    target_position: float = 0.0
    velocity: float = 50.0
    servo_enabled: bool = False
    homed: bool = False
    moving: bool = False
    alarm: bool = False
    actual_position: float = 0.0
    status_summary: str = "未读取"


@dataclass
class SolidDoserMotionState:
    axes: Dict[str, AxisMotionState] = field(default_factory=dict)
    do_states: Dict[str, bool] = field(default_factory=dict)
    plc_connected: bool = False
    simulation_mode: bool = False
    last_action: str = ""
    last_message: str = ""
    last_success: bool = True

    def __post_init__(self) -> None:
        if not self.axes:
            self.axes = {
                axis.key: AxisMotionState(velocity=axis.vel_default)
                for axis in cfg.AXES
            }
        if not self.do_states:
            self.do_states = {item.key: False for item in cfg.DO_OUTPUTS}

    def axis(self, key: str) -> AxisMotionState:
        if key not in self.axes:
            spec = cfg.AXIS_BY_KEY[key]
            self.axes[key] = AxisMotionState(velocity=spec.vel_default)
        return self.axes[key]

    def overview_summary(self) -> str:
        parts = []
        for axis in cfg.AXES:
            st = self.axis(axis.key)
            mode = "仿真" if self.simulation_mode else "联机"
            parts.append(f"{axis.label}({mode}): {st.status_summary}")
        return "；".join(parts)
