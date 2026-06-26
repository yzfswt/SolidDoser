"""第五轴驱动：经 Modbus TCP 控制汇川 Easy521 PLC。"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

from Drivers.Axis5 import axis5_config as cfg
from Drivers.Axis5.axis5_protocol import Axis5ModbusClient
from Drivers.Axis5.axis5_status import Axis5DeviceStatus

logger = logging.getLogger("soliddoser.axis5")

Result = Tuple[bool, str]

_driver: Optional["Axis5Driver"] = None


class Axis5Driver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._client = Axis5ModbusClient()
        self._sim_status = Axis5DeviceStatus()

    def set_motion_cancel_check(
        self, check: Optional[Callable[[], bool]]
    ) -> None:
        self._client.set_motion_cancel_check(check)

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.AXIS5_USE_SIMULATION:
            return True
        client = Axis5ModbusClient()
        ok, _ = client.connect()
        if ok:
            client.close()
            return False
        logger.warning("无法连接汇川 PLC，第五轴使用仿真模式")
        return True

    def _ensure_connected(self) -> Result:
        if self._simulation:
            return True, ""
        if self._client.connected:
            return True, ""
        return self._client.connect()

    def read_status(self) -> Tuple[Axis5DeviceStatus, str]:
        if self._simulation:
            return self._sim_status, ""

        ok, detail = self._ensure_connected()
        if not ok:
            return self._sim_status, detail
        return self._client.read_status()

    def servo_on(self) -> Result:
        if self._simulation:
            self._sim_status.servo_enabled = True
            return True, "第五轴已使能（仿真）。"

        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        ok, detail = self._client.servo_on()
        if ok:
            return True, "第五轴已使能。"
        return False, detail

    def go_home(self) -> Result:
        if self._simulation:
            if not self._sim_status.servo_enabled:
                return False, "第五轴未使能，请先点击「使能」。"
            self._sim_status.homed = True
            self._sim_status.moving = False
            self._sim_status.position_mm = 0.0
            return True, "第五轴已回零（仿真，0 mm）。"

        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        status, err = self._client.read_status()
        if err:
            logger.warning("读取使能状态失败：%s", err)
        if not status.servo_enabled:
            return False, "第五轴未使能，请先点击「使能」。"
        ok, detail = self._client.go_home()
        if not ok:
            return False, detail
        status, _ = self._client.read_status()
        return True, f"第五轴已回零（{detail}，当前 {status.position_mm:g} mm）。"

    def move_absolute(self, target_mm: float, velocity_mm_s: float) -> Result:
        target_mm = max(cfg.AXIS5_MIN_MM, min(cfg.AXIS5_MAX_MM, target_mm))
        if self._simulation:
            self._sim_status.position_mm = target_mm
            self._sim_status.target_mm = target_mm
            self._sim_status.moving = False
            if not self._sim_status.servo_enabled:
                return False, "第五轴未使能，请先点击「使能」。"
            if not self._sim_status.homed:
                return False, "第五轴尚未回零，请先点击「回零」。"
            return True, f"第五轴已移动至 {target_mm:g} mm（仿真）。"

        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail

        status, err = self._client.read_status()
        if err:
            logger.warning("读取回零状态失败：%s", err)
        if not status.servo_enabled:
            return False, "第五轴未使能，请先点击「使能」。"
        if not status.homed:
            return False, "第五轴尚未回零，请先点击「回零」。"

        ok, detail = self._client.move_absolute(target_mm, velocity_mm_s)
        if not ok:
            return False, detail
        return True, f"第五轴已移动至 {target_mm:g} mm（{detail}）。"

    def stop(self) -> Result:
        if self._simulation:
            self._sim_status.moving = False
            return True, "第五轴已停止（仿真）。"

        ok, detail = self._ensure_connected()
        if not ok:
            return False, detail
        return self._client.stop()


def get_axis5_driver() -> Axis5Driver:
    global _driver
    if _driver is None:
        _driver = Axis5Driver()
    return _driver


def apply_status_to_robot(robot, status: Axis5DeviceStatus) -> None:
    robot.axis5_servo_enabled = status.servo_enabled
    robot.axis5_homed = status.homed
    robot.axis5_moving = status.moving
    robot.axis5_alarm = status.alarm
    robot.axis5_current_mm = status.position_mm
    robot.axis5_target_mm = status.target_mm
    robot.axis5_status_summary = status.summary()
