"""SolidDoser 主运动轴运行时状态。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from Drivers.SolidDoserMotion import motion_config as cfg


@dataclass
class AxisRuntimeStatus:
    servo_enabled: bool = False
    homed: bool = False
    moving: bool = False
    alarm: bool = False
    target_position: float = 0.0
    actual_position: float = 0.0

    def summary(self, axis_label: str, unit: str) -> str:
        parts = [
            f"{axis_label}",
            f"使能:{'是' if self.servo_enabled else '否'}",
            f"回零:{'是' if self.homed else '否'}",
            f"运动:{'是' if self.moving else '否'}",
        ]
        if self.alarm:
            parts.append("报警")
        parts.append(f"位置:{self.actual_position:g}{unit}")
        return " | ".join(parts)


@dataclass
class MotionDeviceStatus:
    axes: Dict[str, AxisRuntimeStatus] = field(default_factory=dict)
    do_states: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.axes:
            self.axes = {axis.key: AxisRuntimeStatus() for axis in cfg.AXES}
        if not self.do_states:
            self.do_states = {item.key: False for item in cfg.DO_OUTPUTS}

    def axis(self, key: str) -> AxisRuntimeStatus:
        if key not in self.axes:
            self.axes[key] = AxisRuntimeStatus()
        return self.axes[key]

    def do_on(self, key: str) -> bool:
        return self.do_states.get(key, False)
