"""清洁工位设备状态。"""

from __future__ import annotations



from dataclasses import dataclass



from Drivers.CleaningStation import cleaning_station_config as cfg





@dataclass

class RotationStatus:

    servo_enabled: bool = False

    homed: bool = False

    at_open: bool = False

    at_close: bool = False

    moving: bool = False

    alarm: bool = False

    actual_position: float = 0.0



    def summary(self) -> str:

        power = "已使能" if self.servo_enabled else "未使能"

        home = "已回零" if self.homed else "未回零"

        pos = "开盖位" if self.at_open else ("合盖位" if self.at_close else "未知位")

        run = "运动中" if self.moving else "静止"

        alarm = "有报警" if self.alarm else "无报警"

        return f"{power} | {home} | {pos} | {run} | {alarm}"





@dataclass

class LiftStatus:

    servo_enabled: bool = False

    homed: bool = False

    at_up: bool = False

    at_down: bool = False

    moving: bool = False

    alarm: bool = False

    actual_position: float = 0.0



    def summary(self) -> str:

        power = "已使能" if self.servo_enabled else "未使能"

        home = "已回零" if self.homed else "未回零"

        pos = "上升位" if self.at_up else ("下降位" if self.at_down else "未知位")

        run = "运动中" if self.moving else "静止"

        alarm = "有报警" if self.alarm else "无报警"

        return f"{power} | {home} | {pos} | {run} | {alarm}"





@dataclass

class CleaningStationDeviceStatus:

    rotation: RotationStatus

    lift: LiftStatus

    pumps: list[bool]



    def __init__(self) -> None:

        self.rotation = RotationStatus()

        self.lift = LiftStatus()

        self.pumps = [False] * 5





def infer_rotation_workstation(

    rotation: RotationStatus,

    open_position: float,

    close_position: float,

    *,

    tolerance: float = cfg.POSITION_MATCH_TOLERANCE,

) -> None:

    if rotation.moving:

        return

    actual = rotation.actual_position

    if abs(actual - open_position) <= tolerance:

        rotation.at_open = True

        rotation.at_close = False

    elif abs(actual - close_position) <= tolerance:

        rotation.at_open = False

        rotation.at_close = True

    else:

        rotation.at_open = False

        rotation.at_close = False





def infer_lift_workstation(

    lift: LiftStatus,

    up_position: float,

    down_position: float,

    *,

    tolerance: float = cfg.POSITION_MATCH_TOLERANCE,

) -> None:

    if lift.moving:

        return

    actual = lift.actual_position

    if abs(actual - up_position) <= tolerance:

        lift.at_up = True

        lift.at_down = False

    elif abs(actual - down_position) <= tolerance:

        lift.at_up = False

        lift.at_down = True

    else:

        lift.at_up = False

        lift.at_down = False

