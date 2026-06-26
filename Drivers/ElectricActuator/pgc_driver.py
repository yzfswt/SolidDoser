"""MCEA-3G-01-030-C-W-F 电缸驱动（使能 / 行程初始化 / 回零 / 伸出推压 / 缩回）。"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from Drivers.ElectricActuator import pgc_config as cfg
from Drivers.ElectricActuator import pgc_protocol as proto
from Drivers.ElectricActuator.pgc_status import PgcDeviceStatus
from Drivers.SerialServer import zlan5212di_transport as transport

logger = logging.getLogger("soliddoser.pgc")

Result = Tuple[bool, str]

_driver: Optional["PgcDriver"] = None


class PgcDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._sim_status = PgcDeviceStatus()
        self._stroke_initialized = False
        # 本会话已成功完成的步骤，避免每次动作前重复 Modbus 读
        self._device_enabled = False
        # 使能且已完成行程初始化后可运动（不要求先回零）
        self._motion_ready = False

    def _clear_session_flags(self) -> None:
        self._device_enabled = False
        self._motion_ready = False
        self._stroke_initialized = False

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.PGC_USE_SIMULATION:
            return True
        if transport.sdk_available():
            return False
        logger.warning("ZLAN5212DI 串口服务器不可用，电缸使用仿真模式")
        return True

    def read_status(self) -> Tuple[PgcDeviceStatus, str]:
        if self._simulation:
            self._sim_status.stroke_initialized = self._stroke_initialized
            return self._sim_status, ""
        status, err = proto.read_device_status(transport.transact)
        status.stroke_initialized = self._stroke_initialized
        return status, err

    def _require_enabled(self) -> Result:
        if self._simulation:
            if not self._sim_status.enabled:
                return False, "请先点击「使能」。"
            return True, ""
        if self._device_enabled:
            return True, ""
        word, err = proto.read_status_word(transport.transact)
        if err:
            return False, f"读取状态失败：{err}"
        if word is None or not (word & proto.STAT_ENABLED):
            return False, "电缸未使能，请先点击「使能」。"
        self._device_enabled = True
        return True, ""

    def _require_ready_for_motion(self) -> Result:
        """伸出/缩回/回零等：须已使能且已完成行程初始化（不要求先回零）。"""
        ok, detail = self._require_enabled()
        if not ok:
            return False, detail
        if not self._stroke_initialized:
            return False, "电缸未完成初始化，请先点击「初始化」。"
        if self._motion_ready:
            return True, ""
        if not self._simulation:
            self._motion_ready = True
        return True, ""

    def enable(self) -> Result:
        if self._simulation:
            self._sim_status.enabled = True
            self._sim_status.homed = False
            self._sim_status.home_status = 0
            self._device_enabled = True
            self._motion_ready = False
            return True, "电缸已使能（仿真）。"

        ok, detail = proto.set_enable(transport.transact, True)
        if ok:
            self._device_enabled = True
            self._motion_ready = False
            return True, "电缸已使能（状态字 Bit10 已置位）。"
        return False, detail

    def disable(self) -> Result:
        if self._simulation:
            self._sim_status.enabled = False
            self._sim_status.homed = False
            self._sim_status.home_status = 0
            self._sim_status.stroke_initialized = False
            self._clear_session_flags()
            return True, "电缸已失能（仿真）。"

        ok, detail = proto.set_enable(transport.transact, False)
        if ok:
            self._clear_session_flags()
            return True, "电缸已失能。"
        return False, detail

    def stroke_init(self) -> Result:
        """行程初始化（0x0100=0xA5 全行程标定）：须先使能。"""
        ok, detail = self._require_enabled()
        if not ok:
            return False, detail

        if self._simulation:
            self._stroke_initialized = True
            self._sim_status.stroke_initialized = True
            self._sim_status.legacy_status = 1
            self._sim_status.homed = False
            self._sim_status.home_status = 0
            self._motion_ready = True
            return True, "行程初始化完成（仿真）。"

        ok, detail = proto.stroke_init_device(
            transport.transact, trust_session=self._device_enabled
        )
        if ok:
            self._stroke_initialized = True
            self._motion_ready = True
            return True, detail
        return False, detail

    def home(self) -> Result:
        """回零（0x1605 Bit1）：须先使能且已完成行程初始化（与伸出/缩回同级）。"""
        ok, detail = self._require_ready_for_motion()
        if not ok:
            return False, detail

        if self._simulation:
            self._sim_status.homed = True
            self._sim_status.homing = False
            self._sim_status.home_status = 1
            return True, "回零完成（仿真）。"

        ok, detail = proto.home_device(
            transport.transact, trust_session=self._device_enabled
        )
        if ok:
            return True, detail
        return False, detail

    def clear_alarm(self) -> Result:
        if self._simulation:
            self._sim_status.alarm = False
            return True, "报警已清除（仿真）。"

        ok, detail = proto.clear_alarm(transport.transact)
        if ok:
            return True, detail
        return False, detail

    def extend(
        self,
        thrust_percent: int,
        target_001mm: int,
        push_segment_001mm: int,
        speed_001mm_s: int,
        accel_percent: int,
    ) -> Result:
        ok, detail = self._require_ready_for_motion()
        if not ok:
            return False, detail
        if push_segment_001mm > 0 and not 1 <= thrust_percent <= 100:
            return False, "推压段>0 时推力须在 1–100 % 之间。"
        if self._simulation:
            mm = target_001mm / 100.0
            push_mm = push_segment_001mm / 100.0
            self._sim_status.position_mm = mm
            self._sim_status.run_status = 1
            self._sim_status.moving = False
            return True, (
                f"电缸已伸出（仿真，目标 {mm:g} mm，推压段 {push_mm:g} mm，"
                f"推力 {thrust_percent}%）。"
            )

        ok, detail = proto.extend_thrust(
            transport.transact,
            thrust_percent=thrust_percent,
            target_001mm=target_001mm,
            push_segment_001mm=push_segment_001mm,
            speed_001mm_s=speed_001mm_s,
            accel_percent=accel_percent,
        )
        if ok:
            mm = target_001mm / 100.0
            push_mm = push_segment_001mm / 100.0
            mode = "推压" if push_segment_001mm > 0 else "绝对定位"
            return True, (
                f"电缸已伸出（{mode}，目标 {mm:g} mm，推压段 {push_mm:g} mm，"
                f"推力 {thrust_percent}%，{detail}）。"
            )
        return False, detail

    def retract(
        self,
        target_001mm: int,
        speed_001mm_s: int,
        accel_percent: int,
    ) -> Result:
        ok, detail = self._require_ready_for_motion()
        if not ok:
            return False, detail
        if self._simulation:
            mm = target_001mm / 100.0
            self._sim_status.position_mm = mm
            self._sim_status.run_status = 1
            self._sim_status.moving = False
            return True, f"电缸已缩回（仿真，目标 {mm:g} mm）。"

        ok, detail = proto.retract_absolute(
            transport.transact,
            target_001mm=target_001mm,
            speed_001mm_s=speed_001mm_s,
            accel_percent=accel_percent,
        )
        if ok:
            mm = target_001mm / 100.0
            return True, f"电缸已缩回至 {mm:g} mm（{detail}）。"
        return False, detail


def get_pgc_driver() -> PgcDriver:
    global _driver
    if _driver is None:
        _driver = PgcDriver()
    return _driver


def apply_status_to_robot(robot, status: PgcDeviceStatus) -> None:
    robot.pgc_enabled = status.enabled
    robot.pgc_stroke_initialized = status.stroke_initialized
    robot.pgc_homed = status.homed
    robot.pgc_homing = status.homing
    robot.pgc_alarm = status.alarm
    robot.pgc_moving = status.moving
    robot.pgc_home_status = status.home_status
    robot.pgc_run_status = status.run_status
    robot.pgc_position_mm = status.position_mm
    robot.pgc_status_summary = status.summary()
