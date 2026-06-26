"""PGC-300-60-W-S 电爪驱动（初始化 / 回零 / 打开 / 力控夹持）。"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from Drivers.ElectricGripper import gripper_config as cfg
from Drivers.ElectricGripper import gripper_protocol as proto
from Drivers.ElectricGripper.gripper_status import GripperDeviceStatus
from Drivers.SerialServer import zlan5212di_transport as transport

logger = logging.getLogger("soliddoser.gripper")

Result = Tuple[bool, str]

_driver: Optional["GripperDriver"] = None


class GripperDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._sim_status = GripperDeviceStatus()

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.GRIPPER_USE_SIMULATION:
            return True
        if transport.sdk_available():
            return False
        logger.warning("ZLAN5212DI 串口服务器不可用，电爪使用仿真模式")
        return True

    def read_status(self) -> Tuple[GripperDeviceStatus, str]:
        if self._simulation:
            return self._sim_status, ""
        return proto.read_device_status(transport.transact)

    def init(self) -> Result:
        if self._simulation:
            self._sim_status.homed = True
            self._sim_status.homing = False
            self._sim_status.home_status = 1
            return True, "电爪初始化完成（仿真）。"

        try:
            ok, detail = proto.init_device(transport.transact)
        except (RuntimeError, OSError) as exc:
            return False, str(exc)
        if ok:
            return True, detail
        return False, detail

    def home(self) -> Result:
        if self._simulation:
            self._sim_status.homed = True
            self._sim_status.homing = False
            self._sim_status.home_status = 1
            return True, "电爪回零完成（仿真）。"

        try:
            ok, detail = proto.home_device(transport.transact)
        except (RuntimeError, OSError) as exc:
            return False, str(exc)
        if ok:
            return True, detail
        return False, detail

    def open_jaws(
        self,
        target_mm: float,
        speed_percent: int,
        accel_percent: int,
    ) -> Result:
        """打开：绝对位置至目标开口（默认全行程 60 mm）。"""
        target_permille = proto.mm_to_permille(target_mm)
        if self._simulation:
            self._sim_status.position_mm = target_mm
            self._sim_status.run_status = 1
            self._sim_status.moving = False
            return True, f"电爪已打开（仿真，目标 {target_mm:g} mm）。"

        ok, detail = proto.move_absolute(
            transport.transact,
            target_permille=target_permille,
            speed_percent=speed_percent,
            accel_percent=accel_percent,
        )
        if ok:
            return True, f"电爪已打开至 {target_mm:g} mm（{detail}）。"
        return False, detail

    def grip(
        self,
        force_percent: int,
        push_segment_mm: float,
        target_mm: float,
        speed_percent: int,
        accel_percent: int,
    ) -> Result:
        """关闭/夹持：力控推压，遇物体按设定力值停住。"""
        if not cfg.GRIPPER_MIN_FORCE_PERCENT <= force_percent <= 100:
            return False, f"夹持力须在 {cfg.GRIPPER_MIN_FORCE_PERCENT}–100 % 之间。"
        target_permille = proto.mm_to_permille(target_mm)
        push_permille = proto.mm_to_permille(push_segment_mm)
        if self._simulation:
            self._sim_status.run_status = 2
            self._sim_status.moving = False
            return True, f"电爪已夹持（仿真，力 {force_percent}%）。"

        ok, detail = proto.grip_push(
            transport.transact,
            force_percent=force_percent,
            target_permille=target_permille,
            push_segment_permille=push_permille,
            speed_percent=speed_percent,
            accel_percent=accel_percent,
        )
        if ok:
            return True, f"电爪已夹持（力 {force_percent}%，{detail}）。"
        return False, detail


def get_gripper_driver() -> GripperDriver:
    global _driver
    if _driver is None:
        _driver = GripperDriver()
    return _driver


def apply_status_to_robot(robot, status: GripperDeviceStatus) -> None:
    robot.gripper_homed = status.homed
    robot.gripper_homing = status.homing
    robot.gripper_moving = status.moving
    robot.gripper_home_status = status.home_status
    robot.gripper_run_status = status.run_status
    robot.gripper_position_mm = status.position_mm
    robot.gripper_status_summary = status.summary()
