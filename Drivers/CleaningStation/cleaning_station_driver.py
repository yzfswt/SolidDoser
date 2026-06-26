"""清洁工位驱动：Modbus TCP → Easy521 PLC。"""

from __future__ import annotations



import logging

from typing import Callable, Optional, Tuple



from Drivers.CleaningStation import cleaning_station_config as cfg

from Drivers.CleaningStation.cleaning_station_protocol import CleaningStationModbusClient

from Drivers.CleaningStation.cleaning_station_status import (

    CleaningStationDeviceStatus,

    LiftStatus,

    RotationStatus,

    infer_lift_workstation,

    infer_rotation_workstation,

)

from UIInteraction.ParameterManagement.CleaningStationModel import CleaningStationState



logger = logging.getLogger("soliddoser.cleaning_station")



Result = Tuple[bool, str]



_driver: Optional["CleaningStationDriver"] = None





class CleaningStationDriver:

    def __init__(self) -> None:

        self._simulation = self._resolve_simulation_mode()

        self._client = CleaningStationModbusClient()

        self._sim_status = CleaningStationDeviceStatus()



    def set_motion_cancel_check(
        self, check: Optional[Callable[[], bool]]
    ) -> None:
        self._client.set_motion_cancel_check(check)

    @staticmethod
    def _resolve_simulation_mode() -> bool:

        if cfg.CLEANING_STATION_USE_SIMULATION:

            return True

        client = CleaningStationModbusClient()

        ok, _ = client.connect()

        if ok:

            client.close()

            return False

        logger.warning("无法连接汇川 PLC，清洁工位使用仿真模式")

        return True



    def _ensure_connected(self) -> Result:

        if self._simulation:

            return True, ""

        if self._client.connected:

            return True, ""

        return self._client.connect()



    def read_status(self) -> Tuple[CleaningStationDeviceStatus, str]:

        if self._simulation:

            return self._sim_status, ""



        ok, detail = self._ensure_connected()

        if not ok:

            return self._sim_status, detail

        return self._client.read_status()



    @staticmethod

    def _check_move_ready(

        axis: RotationStatus | LiftStatus, axis_name: str

    ) -> Result:

        if not axis.servo_enabled:

            return False, f"{axis_name}未使能，请先点击「使能」。"

        if not axis.homed:

            return False, f"{axis_name}尚未回零，请先点击「回零」。"

        return True, ""



    def rotation_servo_on(self) -> Result:

        if self._simulation:

            self._sim_status.rotation.servo_enabled = True

            return True, "合盖电机已使能（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        ok, detail = self._client.rotation_servo_on()

        if ok:

            return True, "合盖电机已使能"

        return False, detail



    def rotation_go_home(self) -> Result:

        if self._simulation:

            if not self._sim_status.rotation.servo_enabled:

                return False, "合盖电机未使能，请先点击「使能」。"

            self._sim_status.rotation.homed = True

            self._sim_status.rotation.moving = False

            self._sim_status.rotation.actual_position = 0.0

            return True, "合盖电机已回零（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取合盖电机状态失败：%s", err)

        if not status.rotation.servo_enabled:

            return False, "合盖电机未使能，请先点击「使能」。"

        ok, detail = self._client.rotation_go_home()

        if not ok:

            return False, detail

        return True, f"合盖电机已回零（{detail}）"



    def rotation_to_open(self, station: Optional[CleaningStationState] = None) -> Result:

        if self._simulation:

            if station is not None:

                self._sim_status.rotation.actual_position = station.rotation_open_position

            self._sim_status.rotation.at_open = True

            self._sim_status.rotation.at_close = False

            self._sim_status.rotation.moving = False

            ready, detail = self._check_move_ready(self._sim_status.rotation, "合盖电机")

            if not ready:

                return False, detail

            return True, "旋转已至开盖位（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取合盖电机状态失败：%s", err)

        ready, detail = self._check_move_ready(status.rotation, "合盖电机")

        if not ready:

            return False, detail

        return self._client.rotation_to_open(station)



    def rotation_to_close(self, station: Optional[CleaningStationState] = None) -> Result:

        if self._simulation:

            if station is not None:

                self._sim_status.rotation.actual_position = station.rotation_close_position

            self._sim_status.rotation.at_open = False

            self._sim_status.rotation.at_close = True

            self._sim_status.rotation.moving = False

            ready, detail = self._check_move_ready(self._sim_status.rotation, "合盖电机")

            if not ready:

                return False, detail

            return True, "旋转已至合盖位（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取合盖电机状态失败：%s", err)

        ready, detail = self._check_move_ready(status.rotation, "合盖电机")

        if not ready:

            return False, detail

        return self._client.rotation_to_close(station)



    def rotation_stop(self) -> Result:

        if self._simulation:

            self._sim_status.rotation.moving = False

            return True, "旋转已停止（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        return self._client.rotation_stop()



    def lift_servo_on(self) -> Result:

        if self._simulation:

            self._sim_status.lift.servo_enabled = True

            return True, "升降电机已使能（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        ok, detail = self._client.lift_servo_on()

        if ok:

            return True, "升降电机已使能"

        return False, detail



    def lift_go_home(self) -> Result:

        if self._simulation:

            if not self._sim_status.lift.servo_enabled:

                return False, "升降电机未使能，请先点击「使能」。"

            self._sim_status.lift.homed = True

            self._sim_status.lift.moving = False

            self._sim_status.lift.actual_position = 0.0

            return True, "升降电机已回零（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取升降电机状态失败：%s", err)

        if not status.lift.servo_enabled:

            return False, "升降电机未使能，请先点击「使能」。"

        ok, detail = self._client.lift_go_home()

        if not ok:

            return False, detail

        return True, f"升降电机已回零（{detail}）"



    def lift_to_up(self, station: Optional[CleaningStationState] = None) -> Result:

        if self._simulation:

            if station is not None:

                self._sim_status.lift.actual_position = station.lift_up_position

            self._sim_status.lift.at_up = True

            self._sim_status.lift.at_down = False

            self._sim_status.lift.moving = False

            ready, detail = self._check_move_ready(self._sim_status.lift, "升降电机")

            if not ready:

                return False, detail

            return True, "升降已至上升位（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取升降电机状态失败：%s", err)

        ready, detail = self._check_move_ready(status.lift, "升降电机")

        if not ready:

            return False, detail

        return self._client.lift_to_up(station)



    def lift_to_down(self, station: Optional[CleaningStationState] = None) -> Result:

        if self._simulation:

            if station is not None:

                self._sim_status.lift.actual_position = station.lift_down_position

            self._sim_status.lift.at_up = False

            self._sim_status.lift.at_down = True

            self._sim_status.lift.moving = False

            ready, detail = self._check_move_ready(self._sim_status.lift, "升降电机")

            if not ready:

                return False, detail

            return True, "升降已至下降位（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        status, err = self._client.read_status()

        if err:

            logger.warning("读取升降电机状态失败：%s", err)

        ready, detail = self._check_move_ready(status.lift, "升降电机")

        if not ready:

            return False, detail

        return self._client.lift_to_down(station)



    def lift_stop(self) -> Result:

        if self._simulation:

            self._sim_status.lift.moving = False

            return True, "升降已停止（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        return self._client.lift_stop()



    def set_pump(self, index: int, on: bool) -> Result:

        if self._simulation:

            if 0 <= index < len(self._sim_status.pumps):

                self._sim_status.pumps[index] = on

            return True, f"泵 Y{index} 已{'开启' if on else '关闭'}（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        return self._client.set_pump(index, on)



    def all_pumps_off(self) -> Result:

        if self._simulation:

            self._sim_status.pumps = [False] * 5

            return True, "全部泵已关闭（仿真）"

        ok, detail = self._ensure_connected()

        if not ok:

            return False, detail

        return self._client.all_pumps_off()





def get_cleaning_station_driver() -> CleaningStationDriver:

    global _driver

    if _driver is None:

        _driver = CleaningStationDriver()

    return _driver





def apply_status_to_state(

    state: CleaningStationState, status: CleaningStationDeviceStatus

) -> None:

    infer_rotation_workstation(

        status.rotation,

        state.rotation_open_position,

        state.rotation_close_position,

    )

    infer_lift_workstation(

        status.lift,

        state.lift_up_position,

        state.lift_down_position,

    )



    state.rotation_servo_enabled = status.rotation.servo_enabled

    state.rotation_homed = status.rotation.homed

    state.rotation_at_open = status.rotation.at_open

    state.rotation_at_close = status.rotation.at_close

    state.rotation_moving = status.rotation.moving

    state.rotation_alarm = status.rotation.alarm

    state.rotation_status_summary = status.rotation.summary()

    state.rotation_actual_position = status.rotation.actual_position



    state.lift_servo_enabled = status.lift.servo_enabled

    state.lift_homed = status.lift.homed

    state.lift_at_up = status.lift.at_up

    state.lift_at_down = status.lift.at_down

    state.lift_moving = status.lift.moving

    state.lift_alarm = status.lift.alarm

    state.lift_status_summary = status.lift.summary()

    state.lift_actual_position = status.lift.actual_position



    if len(status.pumps) >= 5:

        state.pump_y0_on = status.pumps[0]

        state.pump_y1_on = status.pumps[1]

        state.pump_y2_on = status.pumps[2]

        state.pump_y3_on = status.pumps[3]

        state.pump_y4_on = status.pumps[4]

