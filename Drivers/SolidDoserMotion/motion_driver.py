"""SolidDoser 主运动驱动：经 Modbus TCP 控制汇川 AM600-CPU1608TN。"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

from Drivers.SolidDoserMotion import motion_config as cfg
from Drivers.SolidDoserMotion.motion_config import AxisMap, DoOutputMap
from Drivers.SolidDoserMotion.motion_protocol import SolidDoserMotionModbusClient
from Drivers.SolidDoserMotion.motion_status import MotionDeviceStatus

logger = logging.getLogger("soliddoser.motion")

Result = Tuple[bool, str]

_driver: Optional["SolidDoserMotionDriver"] = None


class SolidDoserMotionDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._client = SolidDoserMotionModbusClient()
        self._sim_status = MotionDeviceStatus()

    def set_motion_cancel_check(
        self, check: Optional[Callable[[], bool]]
    ) -> None:
        self._client.set_motion_cancel_check(check)

    @property
    def simulation(self) -> bool:
        return self._simulation

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.MOTION_USE_SIMULATION:
            return True
        client = SolidDoserMotionModbusClient()
        ok, _ = client.connect()
        if ok:
            client.close()
            return False
        logger.warning(
            "无法连接 AM600 PLC (%s:%s)，主运动轴使用仿真模式",
            cfg.PLC_HOST,
            cfg.PLC_PORT,
        )
        return True

    def _axis(self, axis_key: str) -> AxisMap:
        if axis_key not in cfg.AXIS_BY_KEY:
            raise KeyError(f"未知轴: {axis_key}")
        return cfg.AXIS_BY_KEY[axis_key]

    def _ensure_connected(self) -> Result:
        if self._simulation:
            return True, ""
        if self._client.connected:
            return True, ""
        return self._client.connect()

    def read_status(self) -> Tuple[MotionDeviceStatus, str]:
        if self._simulation:
            return self._sim_status, ""
        ok, detail = self._ensure_connected()
        if not ok:
            return self._sim_status, detail
        return self._client.read_all_status()

    def servo_on(self, axis_key: str) -> Result:
        axis = self._axis(axis_key)
        if self._simulation:
            self._sim_status.axis(axis_key).servo_enabled = True
            return True, f"{axis.label} 已使能（仿真）。"
        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        ok, detail = self._client.servo_on(axis)
        if ok:
            return True, f"{axis.label} 已使能。"
        return False, detail

    def go_home(self, axis_key: str) -> Result:
        axis = self._axis(axis_key)
        if self._simulation:
            st = self._sim_status.axis(axis_key)
            if not st.servo_enabled:
                return False, f"{axis.label} 未使能，请先使能。"
            st.homed = True
            st.moving = False
            st.actual_position = 0.0
            st.target_position = 0.0
            return True, f"{axis.label} 已回零（仿真，0 {axis.unit}）。"
        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        status, _ = self._client.read_axis_status(axis)
        if not status.servo_enabled:
            return False, f"{axis.label} 未使能，请先使能。"
        ok, detail = self._client.go_home(axis)
        if not ok:
            return False, detail
        status, _ = self._client.read_axis_status(axis)
        return True, (
            f"{axis.label} 已回零（{detail}，当前 {status.actual_position:g} {axis.unit}）。"
        )

    def move_absolute(
        self, axis_key: str, target: float, velocity: float
    ) -> Result:
        axis = self._axis(axis_key)
        target = max(axis.pos_min, min(axis.pos_max, target))
        if self._simulation:
            st = self._sim_status.axis(axis_key)
            if not st.servo_enabled:
                return False, f"{axis.label} 未使能，请先使能。"
            if not st.homed:
                return False, f"{axis.label} 尚未回零，请先回零。"
            st.target_position = target
            st.actual_position = target
            st.moving = False
            return True, f"{axis.label} 已移动至 {target:g} {axis.unit}（仿真）。"
        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        status, _ = self._client.read_axis_status(axis)
        if not status.servo_enabled:
            return False, f"{axis.label} 未使能，请先使能。"
        if not status.homed:
            return False, f"{axis.label} 尚未回零，请先回零。"
        ok, detail = self._client.move_absolute(axis, target, velocity)
        if not ok:
            return False, detail
        return True, f"{axis.label} 已移动至 {target:g} {axis.unit}（{detail}）。"

    def stop(self, axis_key: str) -> Result:
        axis = self._axis(axis_key)
        if self._simulation:
            self._sim_status.axis(axis_key).moving = False
            return True, f"{axis.label} 已停止（仿真）。"
        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        ok, detail = self._client.stop(axis)
        if ok:
            return True, f"{axis.label} {detail}"
        return False, detail

    def _do(self, do_key: str) -> DoOutputMap:
        if do_key not in cfg.DO_BY_KEY:
            raise KeyError(f"未知 DO: {do_key}")
        return cfg.DO_BY_KEY[do_key]

    def set_do_output(self, do_key: str, on: bool) -> Result:
        do_item = self._do(do_key)
        if self._simulation:
            self._sim_status.do_states[do_key] = on
            state = "开启" if on else "关闭"
            return True, f"{do_item.label}（{do_item.q_name}）已{state}（仿真）。"
        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        ok, detail = self._client.set_do_output(do_item, on)
        if ok:
            self._sim_status.do_states[do_key] = on
        return ok, detail


def get_motion_driver() -> SolidDoserMotionDriver:
    global _driver
    if _driver is None:
        _driver = SolidDoserMotionDriver()
    return _driver


def apply_status_to_state(state, status: MotionDeviceStatus) -> None:
    for axis in cfg.AXES:
        axis_status = status.axis(axis.key)
        axis_state = state.axis(axis.key)
        axis_state.servo_enabled = axis_status.servo_enabled
        axis_state.homed = axis_status.homed
        axis_state.moving = axis_status.moving
        axis_state.alarm = axis_status.alarm
        axis_state.actual_position = axis_status.actual_position
        axis_state.target_position = axis_status.target_position
        axis_state.status_summary = axis_status.summary(axis.label, axis.unit)

    state.plc_connected = not get_motion_driver().simulation
    state.simulation_mode = get_motion_driver().simulation
    for do_item in cfg.DO_OUTPUTS:
        state.do_states[do_item.key] = status.do_on(do_item.key)
