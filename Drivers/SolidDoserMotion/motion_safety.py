"""运动安全互锁。"""
from __future__ import annotations

from typing import Tuple

from Drivers.SolidDoserMotion import motion_config as cfg
from Drivers.SolidDoserMotion.motion_status import MotionDeviceStatus

Result = Tuple[bool, str]


def _lift_at_or_below_origin(actual: float, origin: float) -> bool:
    """升降不高于命名原点（含原点容差）时视为安全高度。"""
    return actual <= origin + cfg.POSITION_MATCH_TOLERANCE


def update_indexing_rotation_allowed(motion_state) -> None:
    """根据升降轴状态刷新「分度允许旋转」标志位。"""
    lift = motion_state.axis(cfg.LIFT_AXIS_KEY)
    origin = cfg.lift_position_mm("origin")
    motion_state.indexing_rotation_allowed = (
        lift.servo_enabled
        and lift.datum_ok
        and _lift_at_or_below_origin(lift.actual_position, origin)
    )


def check_indexing_rotation_allowed(status: MotionDeviceStatus) -> Result:
    """检查是否允许分度电机旋转。返回 (True, "") 或 (False, 原因)。"""
    lift = status.axis(cfg.LIFT_AXIS_KEY)
    axis = cfg.AXIS_BY_KEY[cfg.LIFT_AXIS_KEY]
    origin = cfg.lift_position_mm("origin")
    if not lift.servo_enabled:
        return (
            False,
            f"{axis.label}未使能，分度电机禁止旋转（避免与升降机构碰撞）。",
        )
    if not lift.datum_ok:
        return (
            False,
            f"{axis.label}未回基准点，分度电机禁止旋转（避免与升降机构碰撞）。",
        )
    if not _lift_at_or_below_origin(lift.actual_position, origin):
        return (
            False,
            f"{axis.label}高于原点位置（当前 {lift.actual_position:g}{axis.unit}，"
            f"须 ≤ {origin:g}{axis.unit}），分度电机禁止旋转（避免与升降机构碰撞）。",
        )
    return True, ""
