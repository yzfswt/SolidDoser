"""SolidDoser 主运动调试动作。"""
from __future__ import annotations

from typing import Tuple

from BusinessActions.SolidDoserMotion.motion_context import SolidDoserMotionContext
from Drivers.SolidDoserMotion import motion_config as cfg
from Drivers.SolidDoserMotion.motion_driver import (
    apply_status_to_state,
    get_motion_driver,
)

ActionResult = Tuple[bool, str]


def _ok(ctx: SolidDoserMotionContext, action: str, msg: str) -> ActionResult:
    ctx.motion.last_action = action
    ctx.motion.last_message = msg
    ctx.motion.last_success = True
    return True, msg


def _fail(ctx: SolidDoserMotionContext, action: str, msg: str) -> ActionResult:
    ctx.motion.last_action = action
    ctx.motion.last_message = msg
    ctx.motion.last_success = False
    return False, msg


def _sync_status(ctx: SolidDoserMotionContext) -> None:
    status, err = get_motion_driver().read_status()
    apply_status_to_state(ctx.motion, status)
    if err:
        ctx.motion.last_message = err


def motion_refresh_all(ctx: SolidDoserMotionContext) -> ActionResult:
    action = "刷新全部电机状态"
    status, err = get_motion_driver().read_status()
    apply_status_to_state(ctx.motion, status)
    if err:
        return _fail(ctx, action, err)
    return _ok(ctx, action, ctx.motion.overview_summary())


def motion_axis_servo_on(ctx: SolidDoserMotionContext, axis_key: str) -> ActionResult:
    axis = cfg.AXIS_BY_KEY[axis_key]
    action = f"{axis.label} 使能"
    ok, detail = get_motion_driver().servo_on(axis_key)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def motion_axis_go_home(ctx: SolidDoserMotionContext, axis_key: str) -> ActionResult:
    axis = cfg.AXIS_BY_KEY[axis_key]
    action = f"{axis.label} 回零"
    ok, detail = get_motion_driver().go_home(axis_key)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def motion_axis_move_abs(ctx: SolidDoserMotionContext, axis_key: str) -> ActionResult:
    axis = cfg.AXIS_BY_KEY[axis_key]
    st = ctx.motion.axis(axis_key)
    action = f"{axis.label} 绝对定位"
    ok, detail = get_motion_driver().move_absolute(
        axis_key, st.target_position, st.velocity
    )
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def motion_axis_stop(ctx: SolidDoserMotionContext, axis_key: str) -> ActionResult:
    axis = cfg.AXIS_BY_KEY[axis_key]
    action = f"{axis.label} 停止"
    ok, detail = get_motion_driver().stop(axis_key)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def motion_do_set(ctx: SolidDoserMotionContext, do_key: str, on: bool) -> ActionResult:
    do_item = cfg.DO_BY_KEY[do_key]
    action = f"{do_item.label} {'开启' if on else '关闭'}"
    ok, detail = get_motion_driver().set_do_output(do_key, on)
    _sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)
