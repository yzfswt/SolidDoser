"""SolidDoser 系统状态机动作（框架；局部步骤后续可优化）。"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional, Sequence, Tuple

from BusinessActions.KeyenceScanner.scanner_actions import scanner_trigger_read
from BusinessActions.SartoriusBalance.balance_actions import balance_read_weight
from BusinessActions.SolidDoserMotion import motion_actions as motion
from BusinessActions.SolidDoserSystem.system_context import SolidDoserSystemContext
from Common.ActionLogger import get_action_logger
from Drivers.SolidDoserMotion import motion_config as cfg
from Drivers.SolidDoserMotion.indexing_disc import get_indexing_disc
from Drivers.SolidDoserMotion.motion_driver import (
    apply_status_to_state,
    get_motion_driver,
)
from UIInteraction.ParameterManagement.SolidDoserMotionModel import SolidDoserMotionState
from UIInteraction.ParameterManagement.SolidDoserSystemModel import SystemRunState

ActionResult = Tuple[bool, str]
_dose_log = logging.getLogger("soliddoser.dose")

# 加样参数
DOSE_STIR_DURATION_S = 20.0
DOSE_WEIGHT_POLL_S = 0.3
DOSE_WEIGHT_TIMEOUT_S = 120.0

# 回基准点覆盖轴及顺序（搅拌不参与）
SYSTEM_DATUM_AXIS_KEYS: Sequence[str] = (
    cfg.HORIZONTAL_AXIS_KEY,
    cfg.LIFT_AXIS_KEY,
    cfg.POWDER_AXIS_KEY,
    cfg.INDEXING_AXIS_KEY,
)

_STIR_AXIS_KEY = "stirring"

# 「已回原点」判定轴：水平/升降空闲位、承粉工作位、分度任意工位、搅拌停止；另要求振动停止
SYSTEM_ORIGIN_AXIS_KEYS: Sequence[str] = (
    cfg.HORIZONTAL_AXIS_KEY,
    cfg.INDEXING_AXIS_KEY,
    cfg.LIFT_AXIS_KEY,
    cfg.POWDER_AXIS_KEY,
    _STIR_AXIS_KEY,
)

# 「已回原点」判定用位置目标（与「回原点」动作目标可不相同）
_ORIGIN_TARGET_GETTERS: dict[str, Callable[[], float]] = {
    cfg.HORIZONTAL_AXIS_KEY: lambda: cfg.horizontal_position_mm("idle"),
    cfg.INDEXING_AXIS_KEY: lambda: cfg.indexing_position_deg("origin"),
    cfg.LIFT_AXIS_KEY: lambda: cfg.lift_position_mm("idle"),
    cfg.POWDER_AXIS_KEY: lambda: cfg.powder_position_mm("work"),
}


def _ok(ctx: SolidDoserSystemContext, action: str, msg: str) -> ActionResult:
    ctx.system.last_action = action
    ctx.system.last_message = msg
    ctx.system.last_success = True
    return True, msg


def _fail(ctx: SolidDoserSystemContext, action: str, msg: str) -> ActionResult:
    ctx.system.last_action = action
    ctx.system.last_message = msg
    ctx.system.last_success = False
    return False, msg


def _sync_busy_flag(ctx: SolidDoserSystemContext) -> None:
    ctx.param_storage.is_system_busy = ctx.system.is_busy


def _sync_motion_status(ctx: SolidDoserSystemContext) -> None:
    status, err = get_motion_driver().read_status()
    apply_status_to_state(ctx.motion_ctx.motion, status)
    ctx.motion_ctx.motion.set_indexing_station(get_indexing_disc().current_station)
    if err:
        ctx.motion_ctx.motion.last_message = err


def _position_near(
    actual: float, target: float, *, wrap_span: float | None = None
) -> bool:
    tol = cfg.POSITION_MATCH_TOLERANCE
    if wrap_span is not None and wrap_span > 0:
        delta = abs(actual - target) % wrap_span
        delta = min(delta, wrap_span - delta)
        return delta <= tol
    return abs(actual - target) <= tol


def _axis_at_named_origin(motion_state: SolidDoserMotionState, axis_key: str) -> bool:
    if axis_key == _STIR_AXIS_KEY:
        # 搅拌轴：停止（非运动）即视为已回原点条件满足
        return not motion_state.axis(axis_key).moving
    actual = motion_state.axis(axis_key).actual_position
    if axis_key == cfg.INDEXING_AXIS_KEY:
        # 分度轴：停在任意逻辑工位（0～7，45° 对齐）即视为已回原点
        axis = cfg.AXIS_BY_KEY[axis_key]
        span = axis.pos_max - axis.pos_min
        station = cfg.indexing_angle_to_station(actual)
        target = cfg.indexing_station_to_angle(station)
        return _position_near(actual, target, wrap_span=span)
    getter = _ORIGIN_TARGET_GETTERS.get(axis_key)
    if getter is None:
        return False
    return _position_near(actual, getter())


def refresh_system_flags(ctx: SolidDoserSystemContext) -> None:
    """根据当前轴状态刷新系统标识位（已使能 / 已回基准点 / 已回原点）。"""
    _sync_motion_status(ctx)
    motion_state = ctx.motion_ctx.motion
    ctx.system.enabled_ok = all(
        motion_state.axis(axis.key).servo_enabled for axis in cfg.AXES
    )
    ctx.system.datum_ok = all(
        motion_state.axis(key).datum_ok for key in SYSTEM_DATUM_AXIS_KEYS
    )
    ctx.system.origin_ok = all(
        _axis_at_named_origin(motion_state, key) for key in SYSTEM_ORIGIN_AXIS_KEYS
    ) and (not motion_state.do_states.get("vibration", False))


def _begin(
    ctx: SolidDoserSystemContext,
    new_state: SystemRunState,
    action: str,
) -> Optional[ActionResult]:
    """仅允许从空闲进入忙碌态；失败时返回 ActionResult，成功返回 None。"""
    if new_state == SystemRunState.IDLE:
        return _fail(ctx, action, "内部错误：不能 begin 到空闲。")
    if ctx.system.run_state != SystemRunState.IDLE:
        return _fail(
            ctx,
            action,
            f"系统忙碌（{ctx.system.state_label}），请等待完成或停止。",
        )
    ctx.system.abort_requested = False
    ctx.system.run_state = new_state
    ctx.system.last_action = action
    ctx.system.last_message = f"进入{new_state.value}"
    ctx.system.last_success = True
    ctx.system.clear_progress()
    _sync_busy_flag(ctx)
    return None


def _finish(
    ctx: SolidDoserSystemContext,
    ok: bool,
    action: str,
    msg: str,
) -> ActionResult:
    ctx.system.run_state = SystemRunState.IDLE
    ctx.system.abort_requested = False
    ctx.system.bottle_feed_request_id = ""
    ctx.system.bottle_discharge_request_id = ""
    ctx.system.bottle_discharge_peer_done = False
    ctx.system.clear_progress()
    _sync_busy_flag(ctx)
    refresh_system_flags(ctx)
    if ok:
        return _ok(ctx, action, msg)
    return _fail(ctx, action, msg)


def _aborted(ctx: SolidDoserSystemContext) -> bool:
    return ctx.system.abort_requested


def system_request_abort(ctx: SolidDoserSystemContext) -> ActionResult:
    """请求停止当前忙碌流程（由运行中的步骤轮询生效）。

    试剂瓶进料/出料为等待主系统握手的占位态，停止时立即回到空闲并解锁。
    """
    action = "停止"
    if not ctx.system.is_busy:
        return _fail(ctx, action, "当前空闲，无需停止。")
    if ctx.system.run_state in (
        SystemRunState.FEEDING_BOTTLE,
        SystemRunState.DISCHARGING_BOTTLE,
    ):
        return _finish(
            ctx,
            False,
            action,
            f"{ctx.system.state_label}已由本机停止解除，请通知主系统中止对应流程。",
        )
    ctx.system.abort_requested = True
    ctx.system.last_message = "已请求停止…"
    return _ok(ctx, action, "已请求停止，等待当前步骤结束。")


def system_bottle_feed_request(
    ctx: SolidDoserSystemContext, request_id: str = ""
) -> Tuple[bool, str, dict]:
    """主系统进料请求：空闲 + 在原点 + 试剂瓶3无瓶时进入「试剂瓶进料中」并锁定本机动作。

    返回 (accepted, message, response_dict)。
    """
    action = "试剂瓶进料请求"
    rid = (request_id or "").strip()
    base = {"cmd": "BOTTLE_FEED_REQUEST", "request_id": rid}

    refresh_system_flags(ctx)
    if ctx.system.run_state != SystemRunState.IDLE:
        reason = "not_idle"
        msg = f"系统忙碌（{ctx.system.state_label}），不具备进料条件。"
        return False, msg, {**base, "status": "rejected", "reason": reason, "message": msg}

    if not ctx.system.origin_ok:
        reason = "not_at_origin"
        msg = "系统未在原点位置，不具备进料条件。"
        return False, msg, {**base, "status": "rejected", "reason": reason, "message": msg}

    bottle3 = bool(ctx.motion_ctx.motion.di_states.get("bottle_3", False))
    if bottle3:
        reason = "bottle3_occupied"
        msg = "试剂瓶3已有瓶，无需进料。"
        return False, msg, {**base, "status": "rejected", "reason": reason, "message": msg}

    blocked = _begin(ctx, SystemRunState.FEEDING_BOTTLE, action)
    if blocked is not None:
        reason = "not_idle"
        msg = blocked[1]
        return False, msg, {**base, "status": "rejected", "reason": reason, "message": msg}

    ctx.system.bottle_feed_request_id = rid
    ctx.system.set_progress(0, 1, "等待主系统进料完成")
    ctx.system.last_message = "已接受进料请求，等待 BOTTLE_FEED_DONE。"
    msg = "可以进料。"
    return True, msg, {**base, "status": "accepted", "message": msg}


def system_bottle_feed_done(
    ctx: SolidDoserSystemContext, request_id: str = ""
) -> Tuple[bool, str, dict]:
    """主系统进料完成：校验状态与 request_id 后回到空闲。"""
    action = "试剂瓶进料完成"
    rid = (request_id or "").strip()
    base = {"cmd": "BOTTLE_FEED_DONE", "request_id": rid}

    if ctx.system.run_state != SystemRunState.FEEDING_BOTTLE:
        reason = "not_feeding"
        msg = f"当前非进料态（{ctx.system.state_label}），忽略完成信号。"
        return False, msg, {**base, "status": "error", "reason": reason, "message": msg}

    expected = (ctx.system.bottle_feed_request_id or "").strip()
    if expected and rid and expected != rid:
        reason = "request_id_mismatch"
        msg = f"request_id 不匹配（期望 {expected}，收到 {rid}）。"
        return False, msg, {**base, "status": "error", "reason": reason, "message": msg}

    _finish(ctx, True, action, "主系统进料完成，已回到空闲。")
    msg = "进料流程结束。"
    return True, msg, {**base, "status": "success", "message": msg}


def system_bottle_discharge_done(
    ctx: SolidDoserSystemContext, request_id: str = ""
) -> Tuple[bool, str, dict]:
    """主系统出料完成信号：校验后置位，由出料等待线程结束流程。"""
    rid = (request_id or "").strip()
    base = {"cmd": "BOTTLE_DISCHARGE_DONE", "request_id": rid}

    if ctx.system.run_state != SystemRunState.DISCHARGING_BOTTLE:
        reason = "not_discharging"
        msg = f"当前非出料态（{ctx.system.state_label}），忽略完成信号。"
        return False, msg, {**base, "status": "error", "reason": reason, "message": msg}

    expected = (ctx.system.bottle_discharge_request_id or "").strip()
    if expected and rid and expected != rid:
        reason = "request_id_mismatch"
        msg = f"request_id 不匹配（期望 {expected}，收到 {rid}）。"
        return False, msg, {**base, "status": "error", "reason": reason, "message": msg}

    ctx.system.bottle_discharge_peer_done = True
    ctx.system.last_message = "已收到主系统出料完成信号。"
    msg = "出料完成信号已接收。"
    return True, msg, {**base, "status": "success", "message": msg}


def system_run_bottle_discharge(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 试剂瓶出料中 → 空闲。

    条件：空闲 + 在原点 + 试剂瓶3有瓶。
    向主系统发送 BOTTLE_DISCHARGE_REQUEST，等待 BOTTLE_DISCHARGE_DONE（默认 5 分钟超时）。
    """
    from Common.HostBottleFeedConfig import BOTTLE_DISCHARGE_TIMEOUT_S
    from BusinessActions.HostComm.bottle_feed_udp import get_bottle_comm

    action = "试剂瓶出料"
    refresh_system_flags(ctx)
    if ctx.system.run_state != SystemRunState.IDLE:
        return _fail(ctx, action, f"系统忙碌（{ctx.system.state_label}），无法出料。")
    if not ctx.system.origin_ok:
        return _fail(ctx, action, "系统未在原点位置，无法出料。")
    bottle3 = bool(ctx.motion_ctx.motion.di_states.get("bottle_3", False))
    if not bottle3:
        return _fail(ctx, action, "试剂瓶3无瓶，无法出料。")

    blocked = _begin(ctx, SystemRunState.DISCHARGING_BOTTLE, action)
    if blocked is not None:
        return blocked

    import uuid

    rid = str(uuid.uuid4())
    ctx.system.bottle_discharge_request_id = rid
    ctx.system.bottle_discharge_peer_done = False
    ctx.system.set_progress(0, 2, "向主系统发送出料请求")

    try:
        try:
            comm = get_bottle_comm()
        except RuntimeError as exc:
            return _finish(ctx, False, action, str(exc))

        sent = comm.send_to_host(
            {
                "cmd": "BOTTLE_DISCHARGE_REQUEST",
                "request_id": rid,
                "message": "加样系统请求试剂瓶出料",
            }
        )
        if not sent:
            return _finish(ctx, False, action, "向主系统发送出料请求失败。")

        ctx.system.set_progress(1, 2, "等待主系统出料完成")
        ctx.system.last_message = (
            f"已发送出料请求（{rid[:8]}…），等待 BOTTLE_DISCHARGE_DONE…"
        )

        deadline = time.monotonic() + float(BOTTLE_DISCHARGE_TIMEOUT_S)
        while time.monotonic() < deadline:
            if _aborted(ctx):
                return _finish(ctx, False, action, "出料已停止。")
            # 停止键对出料态会直接 _finish；若已空闲则退出等待
            if ctx.system.run_state != SystemRunState.DISCHARGING_BOTTLE:
                return (
                    ctx.system.last_success,
                    ctx.system.last_message or "出料已结束。",
                )
            if ctx.system.bottle_discharge_peer_done:
                return _finish(ctx, True, action, "试剂瓶出料完成。")
            time.sleep(0.2)

        return _finish(
            ctx,
            False,
            action,
            f"等待主系统出料完成超时（{BOTTLE_DISCHARGE_TIMEOUT_S:g} s）。",
        )
    except Exception as exc:  # noqa: BLE001
        return _finish(ctx, False, action, f"出料异常: {exc}")


def system_refresh_status(ctx: SolidDoserSystemContext) -> ActionResult:
    action = "刷新系统状态"
    refresh_system_flags(ctx)
    return _ok(ctx, action, ctx.system.overview_summary())


def system_run_servo_on_all(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 使能中 → 空闲。按显示顺序使能全部电机。"""
    action = "系统使能"
    blocked = _begin(ctx, SystemRunState.ENABLING, action)
    if blocked is not None:
        return blocked

    keys = [axis.key for axis in cfg.AXES]
    ctx.system.set_progress(0, len(keys), "准备使能")
    try:
        for i, axis_key in enumerate(keys):
            if _aborted(ctx):
                return _finish(ctx, False, action, "使能已中止。")
            label = cfg.AXIS_BY_KEY[axis_key].label
            ctx.system.set_progress(i, len(keys), f"{label} 使能")
            ok, detail = motion.motion_axis_servo_on(ctx.motion_ctx, axis_key)
            if not ok:
                return _finish(ctx, False, action, detail)
            ctx.system.set_progress(i + 1, len(keys), f"{label} 完成")
        return _finish(ctx, True, action, "全部电机已使能。")
    except Exception as exc:  # noqa: BLE001
        return _finish(ctx, False, action, f"使能异常: {exc}")


def system_run_go_datum(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 回基准点中 → 空闲。框架：按轴顺序调用单轴回基准点。"""
    action = "系统回基准点"
    blocked = _begin(ctx, SystemRunState.HOMING, action)
    if blocked is not None:
        return blocked

    keys = list(SYSTEM_DATUM_AXIS_KEYS)
    ctx.system.set_progress(0, len(keys), "准备回基准点")
    try:
        for i, axis_key in enumerate(keys):
            if _aborted(ctx):
                return _finish(ctx, False, action, "回基准点已中止。")
            label = cfg.AXIS_BY_KEY[axis_key].label
            ctx.system.set_progress(i, len(keys), f"{label} 回基准点")
            ok, detail = motion.motion_axis_go_datum(ctx.motion_ctx, axis_key)
            if not ok:
                return _finish(ctx, False, action, detail)
            ctx.system.set_progress(i + 1, len(keys), f"{label} 完成")
        return _finish(ctx, True, action, "系统回基准点完成。")
    except Exception as exc:  # noqa: BLE001 — 框架兜底回空闲
        return _finish(ctx, False, action, f"回基准点异常: {exc}")


def system_run_go_origin(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 回原点中 → 空闲。

    顺序：风扇停 → 振动停 → 水平空闲位 → 搅拌停 → 升降空闲位 → 承粉工作位
    → 分度对齐最近工位（已在分度位则跳过）。
    """
    action = "系统回原点"
    blocked = _begin(ctx, SystemRunState.GOING_ORIGIN, action)
    if blocked is not None:
        return blocked

    steps: list[tuple[str, Callable[[], ActionResult]]] = [
        ("风扇停止", lambda: motion.motion_do_set(ctx.motion_ctx, "ion_fan", False)),
        ("振动电机停止", lambda: motion.motion_do_set(ctx.motion_ctx, "vibration", False)),
        (
            "水平电机到空闲位置",
            lambda: motion.motion_horizontal_go_named(ctx.motion_ctx, "idle"),
        ),
        ("搅拌电机停止", lambda: motion.motion_axis_stop(ctx.motion_ctx, _STIR_AXIS_KEY)),
        (
            "升降电机到空闲位置",
            lambda: motion.motion_lift_go_named(ctx.motion_ctx, "idle"),
        ),
        (
            "承粉电机到工作位置",
            lambda: motion.motion_powder_go_named(ctx.motion_ctx, "work"),
        ),
        (
            "分度电机对齐工位",
            lambda: motion.motion_indexing_align_nearest_station(ctx.motion_ctx),
        ),
    ]
    total = len(steps)
    ctx.system.set_progress(0, total, "准备回原点")
    try:
        for i, (label, runner) in enumerate(steps):
            if _aborted(ctx):
                return _finish(ctx, False, action, "回原点已中止。")
            ctx.system.set_progress(i, total, label)
            ok, detail = runner()
            if not ok:
                return _finish(ctx, False, action, detail)
            ctx.system.set_progress(i + 1, total, f"{label} 完成")
        return _finish(ctx, True, action, "系统回原点完成。")
    except Exception as exc:  # noqa: BLE001
        return _finish(ctx, False, action, f"回原点异常: {exc}")


def system_run_initialize(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 初始化中 → 空闲。

    须已回原点。分度盘转一圈扫 8 工位，建立工位→物料条码表。
    任一步失败或中止则整表作废；全部成功则 materials_ok=True。
    """
    action = "物料初始化"
    refresh_system_flags(ctx)
    if not ctx.system.enabled_ok:
        return _fail(ctx, action, "未使能，请先执行使能。")
    if not ctx.system.datum_ok:
        return _fail(ctx, action, "未回基准点，请先执行回基准点。")
    if not ctx.system.origin_ok:
        return _fail(ctx, action, "未回原点，请先执行回原点。")

    blocked = _begin(ctx, SystemRunState.INITIALIZING, action)
    if blocked is not None:
        return blocked

    station_count = cfg.INDEXING_STATION_COUNT
    ctx.system.clear_materials()
    ctx.system.station_materials = {i: "" for i in range(station_count)}
    ctx.system.materials_ok = False
    ctx.system.set_progress(0, station_count, "准备扫码")
    disc = get_indexing_disc()
    velocity = ctx.motion_ctx.motion.axis(cfg.INDEXING_AXIS_KEY).velocity

    def _fail_init(msg: str) -> ActionResult:
        ctx.system.clear_materials()
        return _finish(ctx, False, action, msg)

    try:
        for station in range(station_count):
            if _aborted(ctx):
                return _fail_init("初始化已中止，物料表已作废。")
            ctx.system.set_progress(station, station_count, f"工位 {station} 定位")
            ok, detail = disc.go_to_station(station, velocity)
            ctx.motion_ctx.motion.set_indexing_station(disc.current_station)
            if not ok:
                return _fail_init(f"工位 {station} 定位失败: {detail}")

            if _aborted(ctx):
                return _fail_init("初始化已中止，物料表已作废。")
            ctx.system.set_progress(station, station_count, f"工位 {station} 扫码")
            ok, detail = scanner_trigger_read(ctx.scanner_ctx)
            barcode = (ctx.scanner_ctx.scanner.last_barcode or "").strip()
            if not ok or not barcode:
                return _fail_init(f"工位 {station} 扫码失败: {detail}")
            ctx.system.station_materials[station] = barcode
            ctx.system.set_progress(
                station + 1, station_count, f"工位 {station} → {barcode}"
            )

        if any(
            not (ctx.system.station_materials.get(i) or "").strip()
            for i in range(station_count)
        ):
            return _fail_init("物料表不完整，已作废。")

        ctx.system.materials_ok = True
        mapped = "；".join(
            f"{s}:{c}" for s, c in sorted(ctx.system.station_materials.items())
        )
        return _finish(ctx, True, action, f"初始化完成。{mapped}")
    except Exception as exc:  # noqa: BLE001
        return _fail_init(f"初始化异常: {exc}")


def system_run_dose(ctx: SolidDoserSystemContext) -> ActionResult:
    """空闲 → 加样中 →（完成后调用系统回原点）→ 空闲。

    输入：system.dose_material_id（条码）、system.dose_weight_g（净重 g）。
    """
    action = "加样"
    material_id = (ctx.system.dose_material_id or "").strip()
    dose_weight = float(ctx.system.dose_weight_g or 0.0)
    audit = get_action_logger()

    def _log_dose(msg: str) -> None:
        audit.record(msg)
        _dose_log.info("%s", msg)

    if not ctx.system.materials_ok:
        msg = "未完成物料初始化，请先执行物料初始化。"
        _log_dose(f"加样失败：{msg}")
        return _fail(ctx, action, msg)
    if not material_id:
        msg = "请输入物料编号（条码）。"
        _log_dose(f"加样失败：{msg}")
        return _fail(ctx, action, msg)
    if dose_weight <= 0:
        msg = "加样重量必须大于 0。"
        _log_dose(f"加样失败：{msg}")
        return _fail(ctx, action, msg)

    refresh_system_flags(ctx)
    if not ctx.system.enabled_ok:
        msg = "未使能，请先执行使能。"
        _log_dose(f"加样失败：{msg}")
        return _fail(ctx, action, msg)

    station = ctx.system.find_station_by_material(material_id)
    if station is None:
        msg = f"物料表中无此物料编号：{material_id}"
        _log_dose(f"加样失败：{msg}")
        return _fail(ctx, action, msg)

    blocked = _begin(ctx, SystemRunState.DOSING, action)
    if blocked is not None:
        _log_dose(f"加样失败：{blocked[1]}")
        return blocked

    _log_dose(
        f"加样开始：物料={material_id}，工位={station}，目标净重={dose_weight:g} g"
    )

    total = 11
    disc = get_indexing_disc()
    indexing_vel = ctx.motion_ctx.motion.axis(cfg.INDEXING_AXIS_KEY).velocity
    w0: float | None = None
    w_final: float | None = None

    def _safe_stop_actuators() -> None:
        motion.motion_do_set(ctx.motion_ctx, "vibration", False)
        motion.motion_axis_stop(ctx.motion_ctx, _STIR_AXIS_KEY)

    def _fail_dose(msg: str) -> ActionResult:
        _safe_stop_actuators()
        extra = ""
        if w0 is not None:
            extra += f"，初重={w0:g} g"
        if w_final is not None:
            net = w_final - w0 if w0 is not None else None
            extra += f"，终重={w_final:g} g"
            if net is not None:
                extra += f"，实际净增={net:g} g"
        _log_dose(
            f"加样失败：物料={material_id}，工位={station}，"
            f"目标净重={dose_weight:g} g{extra}，原因={msg}"
        )
        return _finish(ctx, False, action, msg)

    def _sleep_interruptible(seconds: float, detail: str) -> Optional[str]:
        """可中断等待；返回错误信息，None 表示正常结束。"""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if _aborted(ctx):
                return "加样已停止。"
            remain = deadline - time.monotonic()
            ctx.system.progress_detail = f"{detail}（剩余 {remain:.0f}s）"
            time.sleep(min(0.2, max(0.0, remain)))
        return None

    try:
        # 1 已完成查表
        ctx.system.set_progress(1, total, f"物料 {material_id} → 工位 {station}")

        # 2 搅拌停止
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(2, total, "搅拌电机停止")
        ok, detail = motion.motion_axis_stop(ctx.motion_ctx, _STIR_AXIS_KEY)
        if not ok:
            return _fail_dose(detail)

        # 3 振动停止
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(3, total, "振动电机停止")
        ok, detail = motion.motion_do_set(ctx.motion_ctx, "vibration", False)
        if not ok:
            return _fail_dose(detail)

        # 4 升降 → 空闲
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(4, total, "升降电机 → 空闲位置")
        ok, detail = motion.motion_lift_go_named(ctx.motion_ctx, "idle")
        if not ok:
            return _fail_dose(detail)

        # 5 承粉 → 空闲
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(5, total, "承粉电机 → 空闲位置")
        ok, detail = motion.motion_powder_go_named(ctx.motion_ctx, "idle")
        if not ok:
            return _fail_dose(detail)

        # 6 分度 → 加样工位
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(6, total, f"分度盘 → 工位 {station}")
        ok, detail = disc.go_to_station(station, indexing_vel)
        ctx.motion_ctx.motion.set_indexing_station(disc.current_station)
        if not ok:
            return _fail_dose(detail)

        # 7 水平 → 工作
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(7, total, "水平电机 → 工作位置")
        ok, detail = motion.motion_horizontal_go_named(ctx.motion_ctx, "work")
        if not ok:
            return _fail_dose(detail)

        # 8 升降 → 工作
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(8, total, "升降电机 → 工作位置")
        ok, detail = motion.motion_lift_go_named(ctx.motion_ctx, "work")
        if not ok:
            return _fail_dose(detail)

        # 9 搅拌运行 20s 后停止
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(9, total, "搅拌电机运行")
        ok, detail = motion.motion_axis_move_abs(ctx.motion_ctx, _STIR_AXIS_KEY)
        if not ok:
            return _fail_dose(detail)
        err = _sleep_interruptible(DOSE_STIR_DURATION_S, "搅拌电机运行")
        motion.motion_axis_stop(ctx.motion_ctx, _STIR_AXIS_KEY)
        if err:
            return _fail_dose(err)

        # 10 天平加样：读初重 → 振动 → 达目标停振动
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(10, total, "读取天平初始重量")
        ok, detail = balance_read_weight(ctx.balance_ctx)
        if not ok:
            return _fail_dose(detail)
        w0 = ctx.balance_ctx.balance.last_weight_value
        if w0 is None:
            return _fail_dose("天平未返回有效重量值。")
        target_w = w0 + dose_weight
        _log_dose(
            f"加样称重：物料={material_id}，工位={station}，"
            f"初重={w0:g} g，目标净重={dose_weight:g} g，目标总重={target_w:g} g"
        )
        ctx.system.set_progress(
            10, total, f"振动加样中（目标 {target_w:g} g）"
        )
        ok, detail = motion.motion_do_set(ctx.motion_ctx, "vibration", True)
        if not ok:
            return _fail_dose(detail)

        deadline = time.monotonic() + DOSE_WEIGHT_TIMEOUT_S
        reached = False
        while time.monotonic() < deadline:
            if _aborted(ctx):
                motion.motion_do_set(ctx.motion_ctx, "vibration", False)
                w_final = ctx.balance_ctx.balance.last_weight_value
                return _fail_dose("加样已停止。")
            ok, detail = balance_read_weight(ctx.balance_ctx)
            if not ok:
                motion.motion_do_set(ctx.motion_ctx, "vibration", False)
                return _fail_dose(detail)
            current = ctx.balance_ctx.balance.last_weight_value
            if current is None:
                motion.motion_do_set(ctx.motion_ctx, "vibration", False)
                return _fail_dose("天平未返回有效重量值。")
            w_final = current
            ctx.system.progress_detail = (
                f"振动加样中（当前 {current:g} / 目标 {target_w:g} g）"
            )
            if current >= target_w:
                reached = True
                break
            time.sleep(DOSE_WEIGHT_POLL_S)

        motion.motion_do_set(ctx.motion_ctx, "vibration", False)
        if not reached:
            return _fail_dose(
                f"加样超时（{DOSE_WEIGHT_TIMEOUT_S:.0f}s），未达到目标重量。"
            )

        actual_net = (w_final - w0) if (w_final is not None and w0 is not None) else None
        _log_dose(
            f"加样称重完成：物料={material_id}，工位={station}，"
            f"初重={w0:g} g，终重={w_final:g} g，"
            f"实际净增={actual_net:g} g，目标净重={dose_weight:g} g"
        )

        # 11 系统回原点（独立流程）
        if _aborted(ctx):
            return _fail_dose("加样已停止。")
        ctx.system.set_progress(11, total, "系统回原点")
        ctx.system.run_state = SystemRunState.IDLE
        ctx.system.abort_requested = False
        _sync_busy_flag(ctx)
        ok, detail = system_run_go_origin(ctx)
        if not ok:
            msg = f"加样后回原点失败: {detail}"
            _log_dose(
                f"加样部分成功但回原点失败：物料={material_id}，工位={station}，"
                f"初重={w0:g} g，终重={w_final:g} g，实际净增={actual_net:g} g，"
                f"目标净重={dose_weight:g} g，原因={detail}"
            )
            return _fail(ctx, action, msg)
        done_msg = (
            f"加样完成（物料 {material_id}，工位 {station}，"
            f"目标净重 {dose_weight:g} g，实际净增 {actual_net:g} g）。{detail}"
        )
        _log_dose(
            f"加样成功：物料={material_id}，工位={station}，"
            f"初重={w0:g} g，终重={w_final:g} g，"
            f"实际净增={actual_net:g} g，目标净重={dose_weight:g} g"
        )
        return _ok(ctx, action, done_msg)
    except Exception as exc:  # noqa: BLE001
        return _fail_dose(f"加样异常: {exc}")
