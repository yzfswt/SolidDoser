"""清洁工位 Modbus TCP（Easy521 M/D 映射）。"""

from __future__ import annotations



import struct

import time

from typing import Callable, Optional, Tuple



from Drivers.CleaningStation import cleaning_station_config as cfg

from UIInteraction.ParameterManagement.CleaningStationModel import CleaningStationState

from Drivers.CleaningStation.cleaning_station_status import (

    CleaningStationDeviceStatus,

    LiftStatus,

    RotationStatus,

)

from Drivers import plc_modbus_compat as mb



Result = Tuple[bool, str]





def _float_to_registers(value: float) -> list[int]:

    raw = struct.pack("<f", float(value))

    return [regs & 0xFFFF for regs in struct.unpack("<HH", raw)]





def _registers_to_float(regs: list[int]) -> float:

    if len(regs) < 2:

        return 0.0

    raw = struct.pack("<HH", regs[0] & 0xFFFF, regs[1] & 0xFFFF)

    return float(struct.unpack("<f", raw)[0])





class CleaningStationModbusClient:

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



    def _write_d_int(self, d_address: int, value: int) -> Result:

        if not self.connected:

            return False, "PLC 未连接"

        resp = mb.write_registers(

            self._client, d_address, [int(value) & 0xFFFF], device_id=cfg.MODBUS_SLAVE_ID

        )

        if resp.isError():

            return False, f"写 D{d_address} 失败"

        return True, ""



    def _read_d_int(self, d_address: int) -> Tuple[Optional[int], str]:

        if not self.connected:

            return None, "PLC 未连接"

        resp = mb.read_holding_registers(

            self._client, d_address, count=1, device_id=cfg.MODBUS_SLAVE_ID

        )

        if resp.isError() or not resp.registers:

            return None, f"读 D{d_address} 失败"

        return int(resp.registers[0]) & 0xFFFF, ""



    def _read_coil(self, address: int) -> Tuple[Optional[bool], str]:

        if not self.connected:

            return None, "PLC 未连接"

        resp = mb.read_coils(

            self._client, address, count=1, device_id=cfg.MODBUS_SLAVE_ID

        )

        if resp.isError() or not resp.bits:

            return None, f"读 M{address} 失败"

        return bool(resp.bits[0]), ""



    def _pulse_m_until(

        self,

        cmd_m: int,

        done_m: int,

        *,

        timeout_s: float,

        poll_interval_s: float,

        clear_done_m: bool = False,

        alarm_m: Optional[int] = None,

        timeout_hint: str = "",

    ) -> Result:

        if clear_done_m:

            ok, detail = self._write_coil(done_m, False)

            if not ok:

                return False, detail

            time.sleep(0.05)

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

                if alarm_m is not None:

                    alarm, err = self._read_coil(alarm_m)

                    if err:

                        return False, err

                    if alarm:

                        return False, f"轴报警（M{alarm_m}=1），动作中止"

                done, err = self._read_coil(done_m)

                if err:

                    return False, err

                if done:

                    return True, "完成"

                time.sleep(poll_interval_s)

            msg = "动作超时"

            if timeout_hint:

                msg = f"{msg}：{timeout_hint}"

            return False, msg

        finally:

            self._write_coil(cmd_m, False)



    def _send_stop(self, stop_m: int) -> Result:

        ok, detail = self._write_coil(stop_m, True)

        if not ok:

            return False, detail

        time.sleep(0.1)

        self._write_coil(stop_m, False)

        return True, "已发送停止指令"



    def _read_axis_coils(

        self,

        axis: RotationStatus | LiftStatus,

        *,

        power_ok_m: int,

        homed_m: int,

        moving_m: int,

        alarm_m: int,

        errors: list[str],

    ) -> None:

        power_ok, err = self._read_coil(power_ok_m)

        if err:

            errors.append(err)

        elif power_ok is not None:

            axis.servo_enabled = power_ok



        for attr, m_addr in (

            ("homed", homed_m),

            ("moving", moving_m),

            ("alarm", alarm_m),

        ):

            val, err = self._read_coil(m_addr)

            if err:

                errors.append(err)

            elif val is not None:

                setattr(axis, attr, val)



    def rotation_servo_on(self) -> Result:

        return self._pulse_m_until(

            cfg.M_CMD_ROTATION_POWER,

            cfg.M_STATUS_ROTATION_POWER_OK,

            timeout_s=cfg.POWER_ON_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

        )



    def rotation_go_home(self) -> Result:

        return self._pulse_m_until(

            cfg.M_CMD_ROTATION_HOME,

            cfg.M_STATUS_ROTATION_HOME_DONE,

            timeout_s=cfg.HOME_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

            clear_done_m=True,

            alarm_m=cfg.M_STATUS_ROTATION_ALARM,

            timeout_hint=(

                f"M{cfg.M_STATUS_ROTATION_HOME_DONE} 未置位；"

                "请确认 PLC 已将 MC_Home.Done → SET 合盖电机_回零完成"

            ),

        )



    def rotation_stop(self) -> Result:

        return self._send_stop(cfg.M_CMD_ROTATION_STOP)



    def _write_rotation_move(self, target: float, velocity: float) -> Result:

        ok, detail = self._write_d_real(cfg.D_ROTATION_TARGET, target)

        if not ok:

            return False, detail

        return self._write_d_real(cfg.D_ROTATION_VELOCITY, velocity)



    def _rotation_move_absolute(self, target: float, velocity: float) -> Result:

        ok, detail = self._write_rotation_move(target, velocity)

        if not ok:

            return False, detail

        return self._pulse_m_until(

            cfg.M_CMD_ROTATION_MOVE,

            cfg.M_STATUS_ROTATION_MOVE_DONE,

            timeout_s=cfg.COMMAND_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

        )



    def rotation_to_open(self, station: Optional[CleaningStationState] = None) -> Result:

        if station is None:

            return self._rotation_move_absolute(0.0, cfg.ROTATION_VELOCITY_DEFAULT)

        return self._rotation_move_absolute(

            station.rotation_open_position, station.rotation_velocity

        )



    def rotation_to_close(self, station: Optional[CleaningStationState] = None) -> Result:

        if station is None:

            return self._rotation_move_absolute(

                cfg.ROTATION_CLOSE_POSITION_DEFAULT, cfg.ROTATION_VELOCITY_DEFAULT

            )

        return self._rotation_move_absolute(

            station.rotation_close_position, station.rotation_velocity

        )



    def lift_servo_on(self) -> Result:

        return self._pulse_m_until(

            cfg.M_CMD_LIFT_POWER,

            cfg.M_STATUS_LIFT_POWER_OK,

            timeout_s=cfg.POWER_ON_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

        )



    def lift_go_home(self) -> Result:

        return self._pulse_m_until(

            cfg.M_CMD_LIFT_HOME,

            cfg.M_STATUS_LIFT_HOME_DONE,

            timeout_s=cfg.HOME_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

            clear_done_m=True,

            alarm_m=cfg.M_STATUS_LIFT_ALARM,

            timeout_hint=(

                f"M{cfg.M_STATUS_LIFT_HOME_DONE} 未置位；"

                "请确认 PLC：M134↑ 且 M132=1 触发 MC_Home，"

                "且 MC_Home.Done → SET 升降电机_回零完成（试运行能回零说明轴 OK，"

                "多为梯图未锁存 Done）"

            ),

        )



    def lift_stop(self) -> Result:

        return self._send_stop(cfg.M_CMD_LIFT_STOP)



    def _write_lift_move(self, target: float, velocity: float) -> Result:

        ok, detail = self._write_d_real(cfg.D_LIFT_TARGET, target)

        if not ok:

            return False, detail

        return self._write_d_real(cfg.D_LIFT_VELOCITY, velocity)



    def _lift_move_absolute(self, target: float, velocity: float) -> Result:

        ok, detail = self._write_lift_move(target, velocity)

        if not ok:

            return False, detail

        return self._pulse_m_until(

            cfg.M_CMD_LIFT_MOVE,

            cfg.M_STATUS_LIFT_MOVE_DONE,

            timeout_s=cfg.COMMAND_TIMEOUT_S,

            poll_interval_s=cfg.POLL_INTERVAL_S,

        )



    def lift_to_up(self, station: Optional[CleaningStationState] = None) -> Result:

        if station is None:

            return self._lift_move_absolute(0.0, cfg.LIFT_VELOCITY_DEFAULT)

        return self._lift_move_absolute(

            station.lift_up_position, station.lift_velocity

        )



    def lift_to_down(self, station: Optional[CleaningStationState] = None) -> Result:

        if station is None:

            return self._lift_move_absolute(

                cfg.LIFT_DOWN_POSITION_DEFAULT, cfg.LIFT_VELOCITY_DEFAULT

            )

        return self._lift_move_absolute(

            station.lift_down_position, station.lift_velocity

        )



    def set_pump(self, index: int, on: bool) -> Result:

        if index < 0 or index >= len(cfg.PUMP_COILS):

            return False, f"泵索引无效：{index}"

        return self._write_coil(cfg.PUMP_COILS[index], on)



    def all_pumps_off(self) -> Result:

        for m_addr in cfg.PUMP_COILS:

            ok, detail = self._write_coil(m_addr, False)

            if not ok:

                return False, detail

        return True, "全部泵已关闭"



    def read_status(self) -> Tuple[CleaningStationDeviceStatus, str]:

        status = CleaningStationDeviceStatus()

        errors: list[str] = []



        self._read_axis_coils(

            status.rotation,

            power_ok_m=cfg.M_STATUS_ROTATION_POWER_OK,

            homed_m=cfg.M_STATUS_ROTATION_HOMED,

            moving_m=cfg.M_STATUS_ROTATION_MOVING,

            alarm_m=cfg.M_STATUS_ROTATION_ALARM,

            errors=errors,

        )

        self._read_axis_coils(

            status.lift,

            power_ok_m=cfg.M_STATUS_LIFT_POWER_OK,

            homed_m=cfg.M_STATUS_LIFT_HOMED,

            moving_m=cfg.M_STATUS_LIFT_MOVING,

            alarm_m=cfg.M_STATUS_LIFT_ALARM,

            errors=errors,

        )



        for i, m_addr in enumerate(cfg.PUMP_COILS):

            val, err = self._read_coil(m_addr)

            if err:

                errors.append(err)

            elif val is not None:

                status.pumps[i] = val



        pos, err = self._read_d_real(cfg.D_ROTATION_ACTUAL)

        if err:

            errors.append(err)

        elif pos is not None:

            status.rotation.actual_position = pos



        pos, err = self._read_d_real(cfg.D_LIFT_ACTUAL)

        if err:

            errors.append(err)

        elif pos is not None:

            status.lift.actual_position = pos



        if errors:

            return status, "；".join(errors)

        return status, ""

