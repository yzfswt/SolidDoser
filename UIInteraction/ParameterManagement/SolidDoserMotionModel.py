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
    # 分度盘逻辑工位 0～7；回零后归 0，±45° 按工位步进，不依赖实际角度小数
    indexing_station: int = 0
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
        self.indexing_station = cfg.normalize_indexing_station(self.indexing_station)

    def axis(self, key: str) -> AxisMotionState:
        if key not in self.axes:
            spec = cfg.AXIS_BY_KEY[key]
            self.axes[key] = AxisMotionState(velocity=spec.vel_default)
        return self.axes[key]

    def set_indexing_station(self, station: int) -> None:
        self.indexing_station = cfg.normalize_indexing_station(station)

    def overview_summary(self) -> str:
        parts = []
        for axis in cfg.AXES:
            st = self.axis(axis.key)
            mode = "仿真" if self.simulation_mode else "联机"
            extra = ""
            if axis.key == cfg.INDEXING_AXIS_KEY:
                extra = f" 工位{self.indexing_station}"
            parts.append(f"{axis.label}({mode}): {st.status_summary}{extra}")
        return "；".join(parts)
