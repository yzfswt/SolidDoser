"""清洁工位调试动作。"""
from __future__ import annotations

from typing import Callable, Tuple

from BusinessActions.CleaningStation.cleaning_station_context import CleaningStationContext
from Drivers.CleaningStation.cleaning_station_driver import (
    apply_status_to_state,
    get_cleaning_station_driver,
)

ActionResult = Tuple[bool, str]


def _ok(ctx: CleaningStationContext, action: str, msg: str) -> ActionResult:
    ctx.station.last_action = action
    ctx.station.last_message = msg
    ctx.station.last_success = True
    return True, msg


def _fail(ctx: CleaningStationContext, action: str, msg: str) -> ActionResult:
    ctx.station.last_action = action
    ctx.station.last_message = msg
    ctx.station.last_success = False
    return False, msg


def _sync_status(ctx: CleaningStationContext) -> None:
    status, err = get_cleaning_station_driver().read_status()
    apply_status_to_state(ctx.station, status)
    if err:
        ctx.station.rotation_status_summary = (
            f"{status.rotation.summary()}（读取警告：{err}）"
        )
        ctx.station.lift_status_summary = (
            f"{status.lift.summary()}（读取警告：{err}）"
        )


def cleaning_refresh_all(ctx: CleaningStationContext) -> ActionResult:
    action = "刷新清洁工位状态"
    status, err = get_cleaning_station_driver().read_status()
    apply_status_to_state(ctx.station, status)
    if err:
        return _fail(ctx, action, err)
    summary = (
        f"旋转：{status.rotation.summary()}；"
        f"升降：{status.lift.summary()}；"
        f"泵：{ctx.station.pump_summary()}"
    )
    return _ok(ctx, action, summary)


def cleaning_rotation_servo_on(ctx: CleaningStationContext) -> ActionResult:
    action = "合盖电机使能"
    ok, detail = get_cleaning_station_driver().rotation_servo_on()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_rotation_go_home(ctx: CleaningStationContext) -> ActionResult:
    action = "合盖电机回零"
    ok, detail = get_cleaning_station_driver().rotation_go_home()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_rotation_open(ctx: CleaningStationContext) -> ActionResult:
    action = "旋转→开盖位"
    ok, detail = get_cleaning_station_driver().rotation_to_open(ctx.station)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_rotation_close(ctx: CleaningStationContext) -> ActionResult:
    action = "旋转→合盖位"
    ok, detail = get_cleaning_station_driver().rotation_to_close(ctx.station)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_rotation_stop(ctx: CleaningStationContext) -> ActionResult:
    action = "停止"
    ok, detail = get_cleaning_station_driver().rotation_stop()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_lift_servo_on(ctx: CleaningStationContext) -> ActionResult:
    action = "升降电机使能"
    ok, detail = get_cleaning_station_driver().lift_servo_on()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_lift_go_home(ctx: CleaningStationContext) -> ActionResult:
    action = "升降电机回零"
    ok, detail = get_cleaning_station_driver().lift_go_home()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_lift_up(ctx: CleaningStationContext) -> ActionResult:
    action = "升降→上升位"
    ok, detail = get_cleaning_station_driver().lift_to_up(ctx.station)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_lift_down(ctx: CleaningStationContext) -> ActionResult:
    action = "升降→下降位"
    ok, detail = get_cleaning_station_driver().lift_to_down(ctx.station)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def cleaning_lift_stop(ctx: CleaningStationContext) -> ActionResult:
    action = "停止"
    ok, detail = get_cleaning_station_driver().lift_stop()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def _pump_on(index: int, label: str) -> Callable[[CleaningStationContext], ActionResult]:
    def _action(ctx: CleaningStationContext) -> ActionResult:
        action = f"{label}开启"
        ok, detail = get_cleaning_station_driver().set_pump(index, True)
        _sync_status(ctx)
        if ok:
            return _ok(ctx, action, detail)
        return _fail(ctx, action, detail)

    return _action


def _pump_off(index: int, label: str) -> Callable[[CleaningStationContext], ActionResult]:
    def _action(ctx: CleaningStationContext) -> ActionResult:
        action = f"{label}关闭"
        ok, detail = get_cleaning_station_driver().set_pump(index, False)
        _sync_status(ctx)
        if ok:
            return _ok(ctx, action, detail)
        return _fail(ctx, action, detail)

    return _action


def cleaning_pumps_all_off(ctx: CleaningStationContext) -> ActionResult:
    action = "全部泵关闭"
    ok, detail = get_cleaning_station_driver().all_pumps_off()
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


CLEANING_STATION_ACTIONS: dict[
    str, tuple[str, Callable[[CleaningStationContext], ActionResult]]
] = {
    "cleaning_refresh_all": ("刷新全部状态", cleaning_refresh_all),
    "cleaning_rotation_servo_on": ("使能", cleaning_rotation_servo_on),
    "cleaning_rotation_go_home": ("回零", cleaning_rotation_go_home),
    "cleaning_rotation_open": ("开盖位", cleaning_rotation_open),
    "cleaning_rotation_close": ("合盖位", cleaning_rotation_close),
    "cleaning_rotation_stop": ("停止", cleaning_rotation_stop),
    "cleaning_lift_servo_on": ("使能", cleaning_lift_servo_on),
    "cleaning_lift_go_home": ("回零", cleaning_lift_go_home),
    "cleaning_lift_up": ("上升位", cleaning_lift_up),
    "cleaning_lift_down": ("下降位", cleaning_lift_down),
    "cleaning_lift_stop": ("停止", cleaning_lift_stop),
    "cleaning_pump_y0_on": ("气泵1 开", _pump_on(0, "气泵1/Y0")),
    "cleaning_pump_y0_off": ("气泵1 关", _pump_off(0, "气泵1/Y0")),
    "cleaning_pump_y1_on": ("气泵2 开", _pump_on(1, "气泵2/Y1")),
    "cleaning_pump_y1_off": ("气泵2 关", _pump_off(1, "气泵2/Y1")),
    "cleaning_pump_y2_on": ("液泵1 开", _pump_on(2, "液泵1/Y2")),
    "cleaning_pump_y2_off": ("液泵1 关", _pump_off(2, "液泵1/Y2")),
    "cleaning_pump_y3_on": ("液泵2 开", _pump_on(3, "液泵2/Y3")),
    "cleaning_pump_y3_off": ("液泵2 关", _pump_off(3, "液泵2/Y3")),
    "cleaning_pump_y4_on": ("废液泵 开", _pump_on(4, "废液泵/Y4")),
    "cleaning_pump_y4_off": ("废液泵 关", _pump_off(4, "废液泵/Y4")),
    "cleaning_pumps_all_off": ("全部关闭", cleaning_pumps_all_off),
}
