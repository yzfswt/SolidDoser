"""SolidDoser 主运动 Modbus TCP（AM600-CPU1608TN M/D 映射）。"""
from __future__ import annotations

import logging
import struct
import time
from typing import Callable, Optional, Tuple

from Drivers import plc_modbus_compat as mb
from Drivers.SolidDoserMotion import motion_config as cfg
from Drivers.SolidDoserMotion.motion_config import AxisMap, DoOutputMap
from Drivers.SolidDoserMotion.motion_status import AxisRuntimeStatus, MotionDeviceStatus

logger = logging.getLogger("soliddoser.motion")

Result = Tuple[bool, str]


def _float_to_registers(value: float) -> list[int]:
    raw = struct.pack("<f", float(value))
    return [regs & 0xFFFF for regs in struct.unpack("<HH", raw)]


def _registers_to_float(regs: list[int]) -> float:
    if len(regs) < 2:
        return 0.0
    raw = struct.pack("<HH", regs[0] & 0xFFFF, regs[1] & 0xFFFF)
    return float(struct.unpack("<f", raw)[0])


class SolidDoserMotionModbusClient:
    """上位机 Modbus TCP 主站，访问 AM600 的 M/D 软元件。"""

    def __init__(self) -> None:
        self._client = None
        self._connected = False
        self._motion_cancel_check: Optional[Callable[[], bool]] = None

    def set_motion_cancel_check(
        self, check: Optional[Callable[[], bool]]
    ) -> None:
        self._motion_cancel_check = check

    def _motion_cancelled(self) -> bool:
        if self._motion_cancel_check is None:
            return False
        try:
            return bool(self._motion_cancel_check())
        except Exception:
            return False

    def connect(self) -> Result:
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as exc:
            return False, f"缺少 pymodbus：{exc}"

        if self._client is not None:
            self.close()

        client = ModbusTcpClient(cfg.PLC_HOST, port=cfg.PLC_PORT)
        if not client.connect():
            return False, f"无法连接 PLC {cfg.PLC_HOST}:{cfg.PLC_PORT}"
        self._client = client
        self._connected = True
        return True, ""

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self._client is not None

    def _write_coil(self, address: int, value: bool) -> Result:
        if not self.connected:
            return False, "PLC 未连接"
        resp = mb.write_coil(
            self._client, address, value, device_id=cfg.MODBUS_SLAVE_ID
        )
        if resp.isError():
            return False, f"写 M{address} 失败"
        return True, ""

    def _read_coil(self, address: int) -> Tuple[Optional[bool], str]:
        if not self.connected:
            return None, "PLC 未连接"
        resp = mb.read_coils(
            self._client, address, count=1, device_id=cfg.MODBUS_SLAVE_ID
        )
        if resp.isError() or not resp.bits:
            return None, f"读 M{address} 失败"
        return bool(resp.bits[0]), ""

    def _write_d_real(self, d_address: int, value: float) -> Result:
        if not self.connected:
            return False, "PLC 未连接"
        regs = _float_to_registers(value)
        resp = mb.write_registers(
            self._client, d_address, regs, device_id=cfg.MODBUS_SLAVE_ID
        )
        if resp.isError():
            return False, f"写 D{d_address} 失败"
        return True, ""

    def _read_d_real(self, d_address: int) -> Tuple[Optional[float], str]:
        if not self.connected:
            return None, "PLC 未连接"
        resp = mb.read_holding_registers(
            self._client, d_address, count=2, device_id=cfg.MODBUS_SLAVE_ID
        )
        if resp.isError() or not resp.registers or len(resp.registers) < 2:
            return None, f"读 D{d_address} 失败"
        return _registers_to_float(resp.registers[:2]), ""

    def _pulse_m_until(
        self,
        cmd_m: int,
        done_m: int,
        *,
        timeout_s: float,
        poll_interval_s: float,
    ) -> Result:
        ok, detail = self._write_coil(cmd_m, False)
        if not ok:
            return False, detail
        time.sleep(0.05)
        ok, detail = self._write_coil(cmd_m, True)
        if not ok:
            return False, detail

        deadline = time.monotonic() + timeout_s
        try:
            while time.monotonic() < deadline:
                if self._motion_cancelled():
                    return False, "已停止"
                done, err = self._read_coil(done_m)
                if err:
                    return False, err
                if done:
                    return True, "完成"
                time.sleep(poll_interval_s)
            return False, "PLC 动作超时"
        finally:
            self._write_coil(cmd_m, False)

    def read_axis_status(self, axis: AxisMap) -> Tuple[AxisRuntimeStatus, str]:
        status = AxisRuntimeStatus()
        errors: list[str] = []

        pos, err = self._read_d_real(axis.d_actual)
        if err:
            errors.append(err)
        elif pos is not None:
            status.actual_position = pos

        target, err = self._read_d_real(axis.d_target)
        if not err and target is not None:
            status.target_position = target

        for attr, m_addr in (
            ("homed", axis.m_status_homed),
            ("moving", axis.m_status_moving),
            ("alarm", axis.m_status_alarm),
        ):
            val, err = self._read_coil(m_addr)
            if err:
                errors.append(err)
            elif val is not None:
                setattr(status, attr, val)

        power_ok, err = self._read_coil(axis.m_status_power_ok)
        if err:
            errors.append(err)
        elif power_ok is not None:
            status.servo_enabled = power_ok

        if errors:
            return status, "；".join(errors)
        return status, ""

    def read_all_status(self) -> Tuple[MotionDeviceStatus, str]:
        device = MotionDeviceStatus()
        errors: list[str] = []
        for axis in cfg.AXES:
            axis_status, err = self.read_axis_status(axis)
            device.axes[axis.key] = axis_status
            if err:
                errors.append(f"{axis.label}:{err}")
        for do_item in cfg.DO_OUTPUTS:
            state, err = self._read_coil(do_item.m_coil)
            if err:
                errors.append(f"{do_item.label}:{err}")
            elif state is not None:
                device.do_states[do_item.key] = state
        if errors:
            return device, "；".join(errors)
        return device, ""

    def servo_on(self, axis: AxisMap) -> Result:
        return self._pulse_m_until(
            axis.m_cmd_power,
            axis.m_status_power_ok,
            timeout_s=cfg.POWER_ON_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
        )

    def go_home(self, axis: AxisMap) -> Result:
        return self._pulse_m_until(
            axis.m_cmd_home,
            axis.m_status_home_done,
            timeout_s=cfg.HOME_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
        )

    def move_absolute(
        self, axis: AxisMap, target: float, velocity: float
    ) -> Result:
        ok, detail = self._write_d_real(axis.d_target, target)
        if not ok:
            return False, detail
        ok, detail = self._write_d_real(axis.d_velocity, velocity)
        if not ok:
            return False, detail
        return self._pulse_m_until(
            axis.m_cmd_move,
            axis.m_status_move_done,
            timeout_s=cfg.COMMAND_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
        )

    def stop(self, axis: AxisMap) -> Result:
        ok, detail = self._write_coil(axis.m_cmd_stop, True)
        if not ok:
            return False, detail
        time.sleep(0.1)
        self._write_coil(axis.m_cmd_stop, False)
        return True, "已发送停止指令"

    def set_do_output(self, do_item, on: bool) -> Result:
        ok, detail = self._write_coil(do_item.m_coil, on)
        if not ok:
            return False, detail
        state = "开启" if on else "关闭"
        return True, f"{do_item.label}（{do_item.q_name}）已{state}"
