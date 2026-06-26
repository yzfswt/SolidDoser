"""SolidDoser 机器人单步动作（对接 HitbotStudio 模式 1：F99 调度 + 子流程）。"""
from __future__ import annotations

from typing import Callable, Tuple

from BusinessActions.Robot.robot_context import RobotContext
from BusinessActions.Robot.studio_dispatch import dispatch_studio_action, studio_dispatch_enabled
from Common.ActionLogger import get_action_logger
from Drivers.ElectricActuator import pgc_config as pgc_cfg
from Drivers.ElectricActuator.pgc_driver import apply_status_to_robot, get_pgc_driver
from Drivers.ElectricGripper import gripper_config as gripper_cfg
from Drivers.ElectricGripper.gripper_driver import (
    apply_status_to_robot as apply_gripper_status_to_robot,
    get_gripper_driver,
)
from Drivers.Axis5.axis5_driver import apply_status_to_robot as apply_axis5_status_to_robot, get_axis5_driver
from Drivers.Pipette.pipette_driver import get_pipette_driver
from Drivers.Robot.hitbot_studio_bridge import get_studio_bridge
from Drivers.Robot.robot_com485_transport import stop_robot_move
from Drivers.Robot.tool_detector import detect_attached_tool
from UIInteraction.ParameterManagement.RobotModel import AtrLocation, HeldTool

ActionResult = Tuple[bool, str]


def _log(action: str, detail: str, ok: bool = True) -> None:
    flag = "OK" if ok else "FAIL"
    get_action_logger().record(f"机器人 | {action} | {flag} | {detail}")


def _fail(ctx: RobotContext, action: str, msg: str) -> ActionResult:
    _log(action, msg, ok=False)
    ctx.robot.last_action = action
    ctx.robot.last_message = msg
    ctx.robot.last_success = False
    return False, msg


def _ok(ctx: RobotContext, action: str, msg: str) -> ActionResult:
    _log(action, msg, ok=True)
    ctx.robot.last_action = action
    ctx.robot.last_message = msg
    ctx.robot.last_success = True
    return True, msg


def _require_no_tool(ctx: RobotContext, action: str) -> ActionResult | None:
    if ctx.robot.held_tool != HeldTool.NONE:
        return _fail(
            ctx,
            action,
            f"末端已持有「{ctx.robot.tool_label()}」，请先放下当前工具。",
        )
    return None


def _require_tool(ctx: RobotContext, action: str, tool: HeldTool) -> ActionResult | None:
    if ctx.robot.held_tool != tool:
        return _fail(
            ctx,
            action,
            f"需要持有「{_tool_name(tool)}」，当前为「{ctx.robot.tool_label()}」。",
        )
    return None


def _tool_name(tool: HeldTool) -> str:
    return {
        HeldTool.PIPETTE: "移液枪",
        HeldTool.ELECTRIC_ACTUATOR: "电缸",
        HeldTool.GRIPPER: "电爪",
    }.get(tool, "工具")


def _studio_run(
    ctx: RobotContext,
    action: str,
    action_key: str,
    param1: int = 0,
) -> ActionResult | None:
    """若启用 Studio 调度则执行并返回结果；未启用返回 None 表示走本地逻辑。"""
    if not studio_dispatch_enabled():
        return None
    ok, detail = dispatch_studio_action(action_key, param1=param1)
    if ok:
        return None
    return _fail(ctx, action, detail)


# ---------- 工具检测 ----------

def detect_tool(ctx: RobotContext) -> ActionResult:
    action = "工具检测"
    try:
        tool, detail = detect_attached_tool()
    except Exception as exc:
        return _fail(ctx, action, str(exc))

    if tool == HeldTool.NONE and "检测到多个工具" in detail:
        return _fail(ctx, action, detail)

    previous = ctx.robot.tool_label()
    ctx.robot.held_tool = tool
    if tool == HeldTool.NONE:
        ctx.robot.pipette_has_tip = False
        return _ok(ctx, action, f"{detail}（原记录：{previous} → 无工具）")
    return _ok(ctx, action, f"{detail}（原记录：{previous} → {ctx.robot.tool_label()}）")


# ---------- 移液枪 ----------

def pick_pipette(ctx: RobotContext) -> ActionResult:
    action = "取移液枪"
    if err := _require_no_tool(ctx, action):
        return err
    if err := _studio_run(ctx, action, "pick_pipette"):
        return err
    ctx.robot.held_tool = HeldTool.PIPETTE
    ctx.robot.pipette_has_tip = False
    return _ok(ctx, action, "已取移液枪并安装到机器人末端。")


def place_pipette(ctx: RobotContext) -> ActionResult:
    action = "放移液枪"
    if err := _require_tool(ctx, action, HeldTool.PIPETTE):
        return err
    if ctx.robot.pipette_has_tip:
        return _fail(ctx, action, "移液枪仍装有枪头，请先执行「放枪头」丢弃枪头。")
    if err := _studio_run(ctx, action, "place_pipette"):
        return err
    ctx.robot.held_tool = HeldTool.NONE
    return _ok(ctx, action, "已将移液枪放回工具架。")


# ---------- 电缸 ----------

def pick_electric_actuator(ctx: RobotContext) -> ActionResult:
    action = "取电缸"
    if err := _require_no_tool(ctx, action):
        return err
    if err := _studio_run(ctx, action, "pick_electric_actuator"):
        return err
    ctx.robot.held_tool = HeldTool.ELECTRIC_ACTUATOR
    return _ok(ctx, action, "已取电缸并安装到机器人末端。")


def place_electric_actuator(ctx: RobotContext) -> ActionResult:
    action = "放电缸"
    if err := _require_tool(ctx, action, HeldTool.ELECTRIC_ACTUATOR):
        return err
    if err := _studio_run(ctx, action, "place_electric_actuator"):
        return err
    ctx.robot.held_tool = HeldTool.NONE
    return _ok(ctx, action, "已将电缸放回工具架。")


def use_electric_actuator(ctx: RobotContext) -> ActionResult:
    action = "用电缸"
    if err := _require_tool(ctx, action, HeldTool.ELECTRIC_ACTUATOR):
        return err
    if err := _studio_run(ctx, action, "use_electric_actuator"):
        return err
    return _ok(ctx, action, "电缸作业流程已执行。")


def clean_electric_actuator(ctx: RobotContext) -> ActionResult:
    action = "清洗电缸"
    if err := _require_tool(ctx, action, HeldTool.ELECTRIC_ACTUATOR):
        return err
    if err := _studio_run(ctx, action, "clean_electric_actuator"):
        return err
    return _ok(ctx, action, "电缸清洗流程已执行。")


def _mm_to_001mm(value_mm: float) -> int:
    return max(0, min(65535, int(round(value_mm * 100))))


def _pgc_sync_status(ctx: RobotContext) -> None:
    status, err = get_pgc_driver().read_status()
    apply_status_to_robot(ctx.robot, status)
    if err:
        ctx.robot.pgc_status_summary = f"{status.summary()}（读取警告：{err}）"


def _pgc_refresh_status(ctx: RobotContext) -> ActionResult:
    action = "电缸刷新状态"
    status, err = get_pgc_driver().read_status()
    apply_status_to_robot(ctx.robot, status)
    if err:
        return _fail(ctx, action, err)
    return _ok(ctx, action, status.summary())


def electric_actuator_enable(ctx: RobotContext) -> ActionResult:
    action = "电缸使能"
    ok, detail = get_pgc_driver().enable()
    _pgc_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_disable(ctx: RobotContext) -> ActionResult:
    action = "电缸失能"
    ok, detail = get_pgc_driver().disable()
    _pgc_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_stroke_init(ctx: RobotContext) -> ActionResult:
    action = "电缸初始化"
    ok, detail = get_pgc_driver().stroke_init()
    _pgc_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_home(ctx: RobotContext) -> ActionResult:
    action = "电缸回零"
    ok, detail = get_pgc_driver().home()
    _pgc_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_clear_alarm(ctx: RobotContext) -> ActionResult:
    action = "电缸清除报警"
    ok, detail = get_pgc_driver().clear_alarm()
    _pgc_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_extend(ctx: RobotContext) -> ActionResult:
    action = "电缸伸出"
    r = ctx.robot
    target_001mm = _mm_to_001mm(r.pgc_extend_target_mm)
    push_001mm = _mm_to_001mm(r.pgc_extend_push_segment_mm)
    ok, detail = get_pgc_driver().extend(
        thrust_percent=r.pgc_extend_thrust_percent,
        target_001mm=target_001mm,
        push_segment_001mm=push_001mm,
        speed_001mm_s=pgc_cfg.PGC_EXTEND_SPEED_001MM_S,
        accel_percent=pgc_cfg.PGC_EXTEND_ACCEL_PERCENT,
    )
    if ok:
        _pgc_sync_status(ctx)
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def electric_actuator_retract(ctx: RobotContext) -> ActionResult:
    action = "电缸缩回"
    r = ctx.robot
    target_001mm = _mm_to_001mm(r.pgc_retract_target_mm)
    ok, detail = get_pgc_driver().retract(
        target_001mm=target_001mm,
        speed_001mm_s=pgc_cfg.PGC_RETRACT_SPEED_001MM_S,
        accel_percent=pgc_cfg.PGC_RETRACT_ACCEL_PERCENT,
    )
    if ok:
        _pgc_sync_status(ctx)
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


# ---------- 电爪 ----------

def pick_gripper(ctx: RobotContext) -> ActionResult:
    action = "取电爪"
    if err := _require_no_tool(ctx, action):
        return err
    if err := _studio_run(ctx, action, "pick_gripper"):
        return err
    ctx.robot.held_tool = HeldTool.GRIPPER
    return _ok(ctx, action, "已取电爪并安装到机器人末端。")


def place_gripper(ctx: RobotContext) -> ActionResult:
    action = "放电爪"
    if err := _require_tool(ctx, action, HeldTool.GRIPPER):
        return err
    if err := _studio_run(ctx, action, "place_gripper"):
        return err
    ctx.robot.held_tool = HeldTool.NONE
    return _ok(ctx, action, "已将电爪放回工具架。")


def use_gripper(ctx: RobotContext) -> ActionResult:
    action = "用电爪"
    if err := _require_tool(ctx, action, HeldTool.GRIPPER):
        return err
    if err := _studio_run(ctx, action, "use_gripper"):
        return err
    return _ok(ctx, action, "电爪作业流程已执行。")


def _gripper_sync_status(ctx: RobotContext) -> None:
    status, err = get_gripper_driver().read_status()
    apply_gripper_status_to_robot(ctx.robot, status)
    if err:
        ctx.robot.gripper_status_summary = f"{status.summary()}（读取警告：{err}）"


def gripper_refresh_status(ctx: RobotContext) -> ActionResult:
    action = "电爪刷新状态"
    status, err = get_gripper_driver().read_status()
    apply_gripper_status_to_robot(ctx.robot, status)
    if err:
        return _fail(ctx, action, err)
    return _ok(ctx, action, status.summary())


def gripper_init(ctx: RobotContext) -> ActionResult:
    action = "电爪初始化"
    ok, detail = get_gripper_driver().init()
    _gripper_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def gripper_home(ctx: RobotContext) -> ActionResult:
    action = "电爪回零"
    ok, detail = get_gripper_driver().home()
    _gripper_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def gripper_extend(ctx: RobotContext) -> ActionResult:
    action = "电爪打开"
    r = ctx.robot
    ok, detail = get_gripper_driver().open_jaws(
        target_mm=r.gripper_extend_target_mm,
        speed_percent=gripper_cfg.GRIPPER_EXTEND_SPEED_PERCENT,
        accel_percent=gripper_cfg.GRIPPER_EXTEND_ACCEL_PERCENT,
    )
    if ok:
        _gripper_sync_status(ctx)
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def gripper_retract(ctx: RobotContext) -> ActionResult:
    action = "电爪关闭"
    r = ctx.robot
    ok, detail = get_gripper_driver().grip(
        force_percent=r.gripper_force_percent,
        push_segment_mm=r.gripper_extend_push_segment_mm,
        target_mm=r.gripper_retract_target_mm,
        speed_percent=gripper_cfg.GRIPPER_RETRACT_SPEED_PERCENT,
        accel_percent=gripper_cfg.GRIPPER_RETRACT_ACCEL_PERCENT,
    )
    _gripper_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


# ---------- 枪头（移液枪配套） ----------

def pick_tip(ctx: RobotContext) -> ActionResult:
    action = "取枪头"
    if err := _require_tool(ctx, action, HeldTool.PIPETTE):
        return err
    if ctx.robot.pipette_has_tip:
        return _fail(ctx, action, "移液枪已有枪头，请先丢弃旧枪头。")
    rack = ctx.param_storage.tip_rack
    available = rack.slots_with_tip()
    if not available:
        return _fail(ctx, action, "枪头架无可用枪头，请先在「枪头架设置」中标记有枪头的位置。")
    slot = available[0]
    c = slot.coord
    if err := _studio_run(ctx, action, "pick_tip", param1=slot.tip_id):
        return err
    rack.set_has_tip(slot.tip_id, False)
    ctx.robot.pipette_has_tip = True
    return _ok(
        ctx,
        action,
        f"已从枪头位 #{slot.tip_id} 取枪头（坐标 X={c.x:g}, Y={c.y:g}, Z={c.z:g}）。",
    )


def place_tip(ctx: RobotContext) -> ActionResult:
    """将用过的枪头丢弃至回收箱。"""
    action = "放枪头"
    if err := _require_tool(ctx, action, HeldTool.PIPETTE):
        return err
    if not ctx.robot.pipette_has_tip:
        return _fail(ctx, action, "移液枪当前无枪头。")
    if err := _studio_run(ctx, action, "place_tip"):
        return err
    ctx.robot.pipette_has_tip = False
    return _ok(ctx, action, "已将用过的枪头丢弃至回收箱。")


def _pipette_run(ctx: RobotContext, action: str, fn) -> ActionResult:
    ok, detail = fn()
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def pipette_init(ctx: RobotContext) -> ActionResult:
    """经 ZLAN5212DI RS485 初始化；调试界面不校验 held_tool（物理已接入即可）。"""
    action = "移液枪初始化"
    return _pipette_run(ctx, action, get_pipette_driver().init_device)


def pipette_aspirate(ctx: RobotContext) -> ActionResult:
    """调试：不校验软件枪头状态（物理已装枪头即可）。"""
    action = "移液枪取液"
    volume = ctx.robot.pipette_volume_ul
    return _pipette_run(
        ctx,
        action,
        lambda: get_pipette_driver().aspirate(volume),
    )


def pipette_dispense(ctx: RobotContext) -> ActionResult:
    action = "移液枪排液"
    volume = ctx.robot.pipette_volume_ul
    return _pipette_run(
        ctx,
        action,
        lambda: get_pipette_driver().dispense(volume),
    )


def pipette_eject_tip(ctx: RobotContext) -> ActionResult:
    """调试：不校验软件枪头状态（手动装枪头也可退）。"""
    action = "移液枪退枪头"
    ok, detail = get_pipette_driver().eject_tip()
    if not ok:
        return _fail(ctx, action, detail)
    ctx.robot.pipette_has_tip = False
    return _ok(ctx, action, detail)


# ---------- 物料 ----------

def pick_material(ctx: RobotContext) -> ActionResult:
    action = "取物料"
    tray = ctx.param_storage.tray
    occupied = [
        s
        for s in tray.slots.values()
        if s.has_material and s.effective_material_type().value != "none"
    ]
    if not occupied:
        return _fail(ctx, action, "料盘无可用物料，请先在「料盘设置」中标记有料位置。")
    slot = occupied[0]
    c = slot.coord
    mt = slot.effective_material_type().to_label()
    if err := _studio_run(ctx, action, "pick_material", param1=slot.slot_id):
        return err
    return _ok(
        ctx,
        action,
        f"已从料盘仓位 #{slot.slot_id} 取物料（{mt}，X={c.x:g}, Y={c.y:g}, Z={c.z:g}）。",
    )


# ---------- ATR 载台 ----------

def pick_atr(ctx: RobotContext) -> ActionResult:
    action = "取ATR"
    if ctx.robot.atr_location == AtrLocation.ON_ROBOT:
        return _fail(ctx, action, "ATR 已在机器人上。")
    if ctx.robot.atr_location not in (
        AtrLocation.IN_SPECTROMETER,
        AtrLocation.UNKNOWN,
    ):
        return _fail(ctx, action, f"ATR 当前不在光谱仪内（状态：{ctx.robot.atr_location.value}）。")
    if err := _studio_run(ctx, action, "pick_atr"):
        return err
    ctx.robot.atr_location = AtrLocation.ON_ROBOT
    return _ok(ctx, action, "已从 FTIR 光谱仪内取出 ATR 载台。")


def place_atr(ctx: RobotContext) -> ActionResult:
    action = "放ATR"
    if ctx.robot.atr_location == AtrLocation.IN_SPECTROMETER:
        return _fail(ctx, action, "ATR 已在光谱仪内。")
    if ctx.robot.atr_location == AtrLocation.AT_WASH:
        return _fail(ctx, action, "ATR 仍在清洗位，请先完成清洗。")
    if err := _studio_run(ctx, action, "place_atr"):
        return err
    ctx.robot.atr_location = AtrLocation.IN_SPECTROMETER
    return _ok(ctx, action, "已将 ATR 载台放回 FTIR 光谱仪。")


def clean_atr(ctx: RobotContext) -> ActionResult:
    action = "清洗ATR"
    if ctx.robot.atr_location == AtrLocation.IN_SPECTROMETER:
        return _fail(ctx, action, "ATR 仍在光谱仪内，请先取出。")
    if err := _studio_run(ctx, action, "clean_atr"):
        return err
    ctx.robot.atr_location = AtrLocation.AT_WASH
    return _ok(ctx, action, "ATR 清洗流程已执行，载台可放回光谱仪。")


# ---------- 第五轴（滑台，Modbus TCP → Easy521 PLC） ----------

def _axis5_sync_status(ctx: RobotContext) -> None:
    status, err = get_axis5_driver().read_status()
    apply_axis5_status_to_robot(ctx.robot, status)
    if err:
        ctx.robot.axis5_status_summary = f"{status.summary()}（读取警告：{err}）"


def axis5_refresh_status(ctx: RobotContext) -> ActionResult:
    action = "第五轴刷新状态"
    status, err = get_axis5_driver().read_status()
    apply_axis5_status_to_robot(ctx.robot, status)
    if err:
        return _fail(ctx, action, err)
    return _ok(ctx, action, status.summary())


def axis5_servo_on(ctx: RobotContext) -> ActionResult:
    action = "第五轴使能"
    ok, detail = get_axis5_driver().servo_on()
    _axis5_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def axis5_go_home(ctx: RobotContext) -> ActionResult:
    action = "第五轴回零"
    ok, detail = get_axis5_driver().go_home()
    _axis5_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def axis5_move_to_target(ctx: RobotContext) -> ActionResult:
    action = "第五轴绝对定位"
    target = ctx.robot.axis5_target_mm
    ok, detail = get_axis5_driver().move_absolute(
        target,
        ctx.robot.axis5_velocity_mm_s,
    )
    if ok:
        _axis5_sync_status(ctx)
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def axis5_stop(ctx: RobotContext) -> ActionResult:
    action = "第五轴停止"
    ok, detail = get_axis5_driver().stop()
    _axis5_sync_status(ctx)
    if ok:
        return _ok(ctx, action, detail)
    return _fail(ctx, action, detail)


def robot_stop(ctx: RobotContext) -> ActionResult:
    """急停：取消 Studio 等待、停止第五轴，并尝试停止机械臂。"""
    action = "停止"
    ctx.motion_cancel_requested = True
    parts: list[str] = []

    if get_studio_bridge().cancel_pending():
        parts.append("已取消 Studio 指令等待")

    ok5, detail5 = get_axis5_driver().stop()
    _axis5_sync_status(ctx)
    parts.append(detail5 if ok5 else f"第五轴：{detail5}")

    ok_arm, detail_arm = stop_robot_move()
    if ok_arm:
        parts.append(detail_arm)
    elif "未加载" not in detail_arm:
        parts.append(f"机械臂：{detail_arm}")

    msg = "；".join(parts) if parts else "已发送停止请求"
    return _ok(ctx, action, msg)


ROBOT_ACTIONS: dict[str, tuple[str, Callable[[RobotContext], ActionResult]]] = {
    "detect_tool": ("工具检测", detect_tool),
    "pick_pipette": ("取移液枪", pick_pipette),
    "place_pipette": ("放移液枪", place_pipette),
    "pick_electric_actuator": ("取电缸", pick_electric_actuator),
    "place_electric_actuator": ("放电缸", place_electric_actuator),
    "use_electric_actuator": ("用电缸", use_electric_actuator),
    "clean_electric_actuator": ("清洗电缸", clean_electric_actuator),
    "electric_actuator_extend": ("伸出", electric_actuator_extend),
    "electric_actuator_retract": ("缩回", electric_actuator_retract),
    "electric_actuator_stroke_init": ("初始化", electric_actuator_stroke_init),
    "electric_actuator_home": ("回零", electric_actuator_home),
    "electric_actuator_enable": ("使能", electric_actuator_enable),
    "electric_actuator_disable": ("失能", electric_actuator_disable),
    "electric_actuator_clear_alarm": ("清除报警", electric_actuator_clear_alarm),
    "electric_actuator_refresh_status": ("刷新状态", _pgc_refresh_status),
    "pick_gripper": ("取电爪", pick_gripper),
    "place_gripper": ("放电爪", place_gripper),
    "use_gripper": ("用电爪", use_gripper),
    "gripper_init": ("初始化", gripper_init),
    "gripper_home": ("回零", gripper_home),
    "gripper_extend": ("打开", gripper_extend),
    "gripper_retract": ("关闭", gripper_retract),
    "gripper_refresh_status": ("刷新状态", gripper_refresh_status),
    "pick_tip": ("取枪头", pick_tip),
    "place_tip": ("放枪头", place_tip),
    "pipette_init": ("初始化", pipette_init),
    "pipette_aspirate": ("取液", pipette_aspirate),
    "pipette_dispense": ("排液", pipette_dispense),
    "pipette_eject_tip": ("退枪头", pipette_eject_tip),
    "pick_material": ("取物料", pick_material),
    "pick_atr": ("取ATR", pick_atr),
    "place_atr": ("放ATR", place_atr),
    "clean_atr": ("清洗ATR", clean_atr),
    "axis5_servo_on": ("使能", axis5_servo_on),
    "axis5_go_home": ("回零", axis5_go_home),
    "axis5_move_to_target": ("绝对定位", axis5_move_to_target),
    "axis5_stop": ("停止", axis5_stop),
    "axis5_refresh_status": ("刷新状态", axis5_refresh_status),
    "robot_stop": ("停止", robot_stop),
}
