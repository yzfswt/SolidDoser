"""SolidDoser 主运动 Modbus TCP（AM600-CPU1608TN M/D 映射）。"""
from __future__ import annotations

import logging
import struct
import threading
import time
from typing import Callable, Dict, Optional, Tuple

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
        self._io_lock = threading.RLock()
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

        with self._io_lock:
            if self._client is not None:
                self.close()

            client = ModbusTcpClient(cfg.PLC_HOST, port=cfg.PLC_PORT)
            if not client.connect():
                return False, f"无法连接 PLC {cfg.PLC_HOST}:{cfg.PLC_PORT}"
            self._client = client
            self._connected = True
            return True, ""

    def close(self) -> None:
        with self._io_lock:
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

    def read_di_states(self) -> Tuple[Dict[str, bool], str]:
        """一次功能码 02 读取全部试剂瓶 X 点。"""
        with self._io_lock:
            if not self.connected:
                return {}, "PLC 未连接"
            addrs = [item.x_address for item in cfg.DI_INPUTS]
            start = min(addrs)
            count = max(addrs) - start + 1
            resp = mb.read_discrete_inputs(
                self._client, start, count=count, device_id=cfg.MODBUS_SLAVE_ID
            )
            if resp.isError() or not resp.bits:
                return {}, "读 DI 失败"
            bits = list(resp.bits)
            states: Dict[str, bool] = {}
            for item in cfg.DI_INPUTS:
                idx = item.x_address - start
                if idx < 0 or idx >= len(bits):
                    return states, f"{item.label}:读 {item.x_name} 失败"
                states[item.key] = bool(bits[idx])
            return states, ""

    def _write_d_real(self, d_address: int, value: float) -> Result:
        with self._io_lock:
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
        with self._io_lock:
            if not self.connected:
                return None, "PLC 未连接"
            resp = mb.read_holding_registers(
                self._client, d_address, count=2, device_id=cfg.MODBUS_SLAVE_ID
            )
            if resp.isError() or not resp.registers or len(resp.registers) < 2:
                return None, f"读 D{d_address} 失败"
            return _registers_to_float(resp.registers[:2]), ""

    def _write_d_word(self, d_address: int, value: int) -> Result:
        with self._io_lock:
            if not self.connected:
                return False, "PLC 未连接"
            resp = mb.write_registers(
                self._client,
                d_address,
                [int(value) & 0xFFFF],
                device_id=cfg.MODBUS_SLAVE_ID,
            )
            if resp.isError():
                return False, f"写 D{d_address} 失败"
            return True, ""

    def _read_d_word(self, d_address: int) -> Tuple[Optional[int], str]:
        with self._io_lock:
            if not self.connected:
                return None, "PLC 未连接"
            resp = mb.read_holding_registers(
                self._client, d_address, count=1, device_id=cfg.MODBUS_SLAVE_ID
            )
            if resp.isError() or not resp.registers:
                return None, f"读 D{d_address} 失败"
            return int(resp.registers[0]) & 0xFFFF, ""

    def _pulse_d_bit_until(
        self,
        d_cmd: int,
        cmd_bit: int,
        d_sts: int,
        sts_bit: int,
        *,
        timeout_s: float,
        poll_interval_s: float,
        require_moving_s: float = 0.0,
        accept_moving: bool = False,
    ) -> Result:
        """命令字置 bit=1，等到状态字对应 bit=1 后清 0。发令前整字清零。"""
        mask = 1 << cmd_bit
        sts_mask = 1 << sts_bit
        alarm_mask = 1 << cfg.STS_BIT_ALARM
        moving_mask = 1 << cfg.STS_BIT_MOVING

        ok, detail = self._write_d_word(d_cmd, 0)
        if not ok:
            return False, detail
        # HomeDone/MoveDone 随命令撤销而清；PowerOk 使能后保持，不能等其变 0
        if sts_bit in (cfg.STS_BIT_HOME_DONE, cfg.STS_BIT_MOVE_DONE):
            clear_deadline = time.monotonic() + 1.0
            while time.monotonic() < clear_deadline:
                sts, err = self._read_d_word(d_sts)
                if err:
                    return False, err
                if sts is not None and (sts & sts_mask) == 0:
                    break
                # 搅拌等连续速度轴：已在转时 MoveDone 保持为 1，不必等清零
                if (
                    accept_moving
                    and sts is not None
                    and (sts & moving_mask) != 0
                ):
                    break
                time.sleep(poll_interval_s)
            else:
                return False, "PLC 完成位未清除，请点「停止」后重试"

        time.sleep(0.05)
        ok, detail = self._write_d_word(d_cmd, mask)
        if not ok:
            return False, detail

        deadline = time.monotonic() + timeout_s
        moving_deadline = (
            time.monotonic() + require_moving_s if require_moving_s > 0 else None
        )
        saw_activity = False
        cancelled = False
        try:
            while time.monotonic() < deadline:
                if self._motion_cancelled():
                    cancelled = True
                    # Busy 中仅清 CmdMove 不会停轴，必须发 CmdStop → MC_Stop
                    self._write_d_word(d_cmd, 1 << cfg.CMD_BIT_STOP)
                    return False, "已停止"
                sts, err = self._read_d_word(d_sts)
                if err:
                    return False, err
                if sts is not None and (sts & alarm_mask) != 0:
                    return False, "轴报警，请点「停止」或在 InoProShop 轴复位后再试"
                if sts is not None and (sts & sts_mask) != 0:
                    return True, "完成"
                if accept_moving and sts is not None and (sts & moving_mask) != 0:
                    return True, "已启动"
                if sts is not None and (sts & moving_mask) != 0:
                    saw_activity = True
                if (
                    moving_deadline is not None
                    and not saw_activity
                    and time.monotonic() >= moving_deadline
                ):
                    return False, "PLC 未启动该动作（无运动反馈），请检查轴状态与任务配置"
                time.sleep(poll_interval_s)
            return False, "PLC 动作超时"
        finally:
            # 停止中勿清零，否则会抹掉 CmdStop，PLC 可能采不到上升沿
            if not cancelled and not self._motion_cancelled():
                self._write_d_word(d_cmd, 0)

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

        sts, err = self._read_d_word(axis.d_sts)
        if err:
            errors.append(err)
        elif sts is not None:
            status.servo_enabled = (sts & (1 << cfg.STS_BIT_POWER_OK)) != 0
            status.datum_ok = (sts & (1 << cfg.STS_BIT_HOMED)) != 0
            status.moving = (sts & (1 << cfg.STS_BIT_MOVING)) != 0
            status.alarm = (sts & (1 << cfg.STS_BIT_ALARM)) != 0

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
            raw, err = self._read_d_word(do_item.d_register)
            if err:
                errors.append(f"{do_item.label}:{err}")
            elif raw is not None:
                device.do_states[do_item.key] = raw != 0
        di_states, di_err = self.read_di_states()
        device.di_states.update(di_states)
        if di_err:
            errors.append(di_err)
        if errors:
            return device, "；".join(errors)
        return device, ""

    def servo_on(self, axis: AxisMap) -> Result:
        return self._pulse_d_bit_until(
            axis.d_cmd,
            cfg.CMD_BIT_POWER,
            axis.d_sts,
            cfg.STS_BIT_POWER_OK,
            timeout_s=cfg.POWER_ON_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
        )

    def go_datum(self, axis: AxisMap) -> Result:
        """找外部基准点（PLC CmdHome → MC_Home）。"""
        return self._pulse_d_bit_until(
            axis.d_cmd,
            cfg.CMD_BIT_HOME,
            axis.d_sts,
            cfg.STS_BIT_HOME_DONE,
            timeout_s=cfg.DATUM_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
            require_moving_s=3.0,
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
        return self._pulse_d_bit_until(
            axis.d_cmd,
            cfg.CMD_BIT_MOVE,
            axis.d_sts,
            cfg.STS_BIT_MOVE_DONE,
            timeout_s=cfg.COMMAND_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
        )

    def start_velocity(self, axis: AxisMap, velocity: float) -> Result:
        ok, detail = self._write_d_real(axis.d_velocity, velocity)
        if not ok:
            return False, detail
        sts, err = self._read_d_word(axis.d_sts)
        if err:
            return False, err
        moving_mask = 1 << cfg.STS_BIT_MOVING
        if sts is not None and (sts & moving_mask) != 0:
            return True, "已在运行（已更新速度）"
        return self._pulse_d_bit_until(
            axis.d_cmd,
            cfg.CMD_BIT_MOVE,
            axis.d_sts,
            cfg.STS_BIT_MOVE_DONE,
            timeout_s=cfg.COMMAND_TIMEOUT_S,
            poll_interval_s=cfg.POLL_INTERVAL_S,
            accept_moving=True,
        )

    def stop(self, axis: AxisMap) -> Result:
        """写 CmdStop 并保持到轴不再 Moving，避免与定位 finally 清零竞态。"""
        mask = 1 << cfg.CMD_BIT_STOP
        moving_mask = 1 << cfg.STS_BIT_MOVING
        ok, detail = self._write_d_word(axis.d_cmd, mask)
        if not ok:
            return False, detail
        # 至少保持一个 PLC 周期，供 R_TRIG 采到上升沿
        time.sleep(max(0.05, cfg.POLL_INTERVAL_S))
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            # 若定位线程 finally 误清命令字，这里反复置位
            self._write_d_word(axis.d_cmd, mask)
            sts, err = self._read_d_word(axis.d_sts)
            if err:
                break
            if sts is not None and (sts & moving_mask) == 0:
                break
            time.sleep(cfg.POLL_INTERVAL_S)
        self._write_d_word(axis.d_cmd, 0)
        return True, "已停止"

    def set_do_output(self, do_item, on: bool) -> Result:
        ok, detail = self._write_d_word(do_item.d_register, 1 if on else 0)
        if not ok:
            return False, detail
        state = "开启" if on else "关闭"
        return True, f"{do_item.label}（{do_item.q_name}）已{state}"
