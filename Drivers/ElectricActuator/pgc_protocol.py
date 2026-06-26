"""MCEA 电缸 Modbus-RTU 0x1600 协议（大寰 MCEA 手册 2.4 节）。"""

from __future__ import annotations



import logging

import time

from typing import Callable, Optional, Tuple



from Drivers.ElectricActuator import pgc_config as cfg

from Drivers.ElectricActuator.modbus_rtu import (

    build_read_registers,

    build_write_register,

    build_write_registers,

    parse_read_u16,

    parse_read_registers,

    parse_write_response,

)



from Drivers.ElectricActuator.pgc_status import PgcDeviceStatus



logger = logging.getLogger("soliddoser.pgc")



Result = Tuple[bool, str]



REG_TARGET_POS = 0x1600

REG_PUSH_SEGMENT = 0x1601

REG_MAX_SPEED = 0x1602

REG_ACCEL = 0x1603

REG_FORCE = 0x1604

REG_CONTROL_WORD = 0x1605

REG_POSITION_FB = 0x160C

REG_ALARM = 0x160F

REG_STATUS_WORD = 0x1611



# 0x1611 状态字位

STAT_IN_POSITION = 1 << 5

STAT_HOMED = 1 << 6

STAT_MOVING = 1 << 8

STAT_ALARM = 1 << 9

STAT_ENABLED = 1 << 10



# 堵转报警（推压模式预期）

ALARM_STALL = 0x2BF7





def _write_reg(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

    value: int,

) -> Result:

    req = build_write_register(slave_id, address, value)

    resp = transact(req, min_response_len=8)

    ok, detail = parse_write_response(resp, slave_id)

    if not ok:

        return False, detail or f"写入 0x{address:04X} 失败"

    return True, ""





def _write_motion_block(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    *,

    position_001mm: int,

    push_segment_001mm: int,

    speed_001mm_s: int,

    accel_percent: int,

    force_percent: int,

    control_word: int,

) -> Result:

    values = [

        position_001mm & 0xFFFF,

        push_segment_001mm & 0xFFFF,

        speed_001mm_s & 0xFFFF,

        accel_percent & 0xFFFF,

        force_percent & 0xFFFF,

        control_word & 0xFFFF,

    ]

    req = build_write_registers(slave_id, REG_TARGET_POS, values)

    resp = transact(req, min_response_len=8)

    ok, detail = parse_write_response(resp, slave_id)

    if not ok:

        return False, detail or "写入运动参数块失败"

    return True, ""





def _read_reg(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

) -> Tuple[Optional[int], str]:

    req = build_read_registers(slave_id, address, 1)

    resp = transact(req, min_response_len=7)

    return parse_read_u16(resp, slave_id)





def _read_reg_soft(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

) -> Tuple[Optional[int], str]:

    try:

        return _read_reg(transact, slave_id, address)

    except RuntimeError as exc:

        return None, str(exc)





def _read_regs(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

    count: int,

) -> Tuple[Optional[list[int]], str]:

    req = build_read_registers(slave_id, address, count)

    min_len = 5 + count * 2

    resp = transact(req, min_response_len=min_len)

    return parse_read_registers(resp, slave_id, count)





def _is_device_enabled(
    transact: Callable[[bytes, int], bytes], slave_id: int
) -> Tuple[Optional[bool], str]:
    """0x1611 Bit10：电机已使能（抱闸释放，应有「啪嗒」反馈）。"""
    word_val, err = _read_reg(transact, slave_id, REG_STATUS_WORD)
    if err:
        return None, f"读取状态字失败：{err}"
    if word_val is not None and (word_val & STAT_ENABLED):
        return True, ""
    return False, ""


def _read_alarm_state(
    transact: Callable[[bytes, int], bytes], slave_id: int
) -> Tuple[bool, Optional[int], str]:
    word_val, err = _read_reg(transact, slave_id, REG_STATUS_WORD)
    if err:
        return True, None, f"读取状态字失败：{err}"
    alarm_code, err = _read_reg(transact, slave_id, REG_ALARM)
    if err:
        return bool(word_val and (word_val & STAT_ALARM)), None, f"读取报警码失败：{err}"
    active = bool(word_val and (word_val & STAT_ALARM)) or bool(alarm_code)
    return active, alarm_code, ""


def _wait_alarm_cleared(
    transact: Callable[[bytes, int], bytes],
    slave_id: int,
    *,
    timeout_s: float = cfg.PGC_ALARM_CLEAR_TIMEOUT_S,
    poll_interval_s: float = cfg.PGC_ENABLE_POLL_INTERVAL_S,
) -> Result:
    deadline = time.monotonic() + timeout_s
    last_code: Optional[int] = None
    while time.monotonic() < deadline:
        active, code, err = _read_alarm_state(transact, slave_id)
        if err:
            return False, err
        if not active:
            return True, ""
        last_code = code
        time.sleep(poll_interval_s)
    if last_code:
        return False, f"报警未清除（0x{last_code:04X}）"
    return False, "报警未清除（0x1611 Bit9 仍为 1）"


def _enable_timeout_detail(
    transact: Callable[[bytes, int], bytes], slave_id: int
) -> str:
    word_val, _ = _read_reg(transact, slave_id, REG_STATUS_WORD)
    ctrl_val, _ = _read_reg(transact, slave_id, REG_CONTROL_WORD)
    active, alarm_code, _ = _read_alarm_state(transact, slave_id)
    parts = [f"Modbus ID={slave_id}", "未读到 0x1611 Bit10（电机使能反馈）"]
    if word_val is not None:
        parts.append(f"0x1611=0x{word_val:04X}")
    if ctrl_val is not None:
        parts.append(f"0x1605=0x{ctrl_val:04X}")
    if alarm_code:
        parts.append(f"0x160F=0x{alarm_code:04X}")
    if active:
        parts.append("设备处于报警状态，请先点「清除报警」")
    return "；".join(parts)


def _wait_enabled_feedback(
    transact: Callable[[bytes, int], bytes],
    slave_id: int,
    *,
    timeout_s: float = cfg.PGC_ENABLE_TIMEOUT_S,
    poll_interval_s: float = cfg.PGC_ENABLE_POLL_INTERVAL_S,
) -> Result:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        enabled, err = _is_device_enabled(transact, slave_id)
        if err:
            return False, err
        if enabled:
            return True, ""
        time.sleep(poll_interval_s)
    return False, f"电缸使能超时（{_enable_timeout_detail(transact, slave_id)}）"


def _require_enabled(transact: Callable[[bytes, int], bytes], slave_id: int) -> Result:
    enabled, err = _is_device_enabled(transact, slave_id)
    if err:
        return False, err
    if not enabled:
        return False, "电缸未使能，请先点击「使能」。"
    return True, ""


def _require_homed(transact: Callable[[bytes, int], bytes], slave_id: int) -> Result:
    value, err = _read_reg(transact, slave_id, REG_STATUS_WORD)
    if err:
        return False, f"读取状态字失败：{err}"
    if value is None or not (value & STAT_HOMED):
        return False, "电缸未回零，请先完成「初始化」后点击「回零」。"
    return True, ""


def read_status_word(
    transact: Callable[[bytes, int], bytes],
) -> Tuple[Optional[int], str]:
    """仅读 0x1611 状态字（单次 Modbus，用于快速校验）。"""
    return _read_reg(transact, cfg.MODBUS_SLAVE_ID, REG_STATUS_WORD)


def _wait_stroke_init_done(
    transact: Callable[[bytes, int], bytes],
    slave_id: int,
    *,
    timeout_s: float = cfg.PGC_STROKE_INIT_TIMEOUT_S,
    poll_interval_s: float = cfg.PGC_MOTION_POLL_INTERVAL_S,
) -> Result:
    """等待 0x0100=0xA5 行程标定完成（读 0x0200，须先见到标定中再成功）。"""
    start = time.monotonic()
    deadline = start + timeout_s
    motion_deadline = start + cfg.PGC_HOME_MOTION_START_TIMEOUT_S
    saw_in_progress = False
    first_sample = True

    while time.monotonic() < deadline:
        value, err = _read_reg_soft(transact, slave_id, cfg.PGC_REG_LEGACY_STATUS)
        if err:
            if saw_in_progress:
                time.sleep(poll_interval_s)
                continue
            return False, f"读取 0x0200 失败：{err}"
        if value == 2:
            saw_in_progress = True
        if not first_sample and value == 1 and saw_in_progress:
            return True, "行程初始化完成"
        if (
            time.monotonic() >= motion_deadline
            and not saw_in_progress
            and value != 1
        ):
            return False, (
                f"行程初始化未启动（{cfg.PGC_HOME_MOTION_START_TIMEOUT_S:g}s 内 "
                f"0x0200 未进入标定中；当前={value}）。"
            )
        first_sample = False
        time.sleep(poll_interval_s)

    if saw_in_progress:
        for _ in range(4):
            value, err = _read_reg_soft(transact, slave_id, cfg.PGC_REG_LEGACY_STATUS)
            if not err and value == 1:
                return True, "行程初始化完成"
            time.sleep(poll_interval_s)

    return False, "行程初始化超时"


def stroke_init_device(
    transact: Callable[[bytes, int], bytes], *, trust_session: bool = False
) -> Result:
    """行程初始化：写 0x0100=0xA5（全行程标定，须先使能）。"""
    slave = cfg.MODBUS_SLAVE_ID
    if not trust_session:
        ok, detail = _require_enabled(transact, slave)
        if not ok:
            return False, detail
    ok, detail = _write_reg(
        transact, slave, cfg.PGC_REG_LEGACY_CMD, cfg.PGC_CMD_STROKE_INIT
    )
    if not ok:
        return False, detail
    return _wait_stroke_init_done(transact, slave)


def _prepare_motion(
    transact: Callable[[bytes, int], bytes],
    slave_id: int,
    *,
    verify: bool = True,
) -> Result:
    """运动前：可选校验使能；写 0x1605=0x0020 清除定位触发位（不要求已回零）。"""
    if verify:
        ok, detail = _require_enabled(transact, slave_id)
        if not ok:
            return False, detail
    return _write_reg(transact, slave_id, REG_CONTROL_WORD, cfg.PGC_CTRL_ENABLE)





def _wait_home_done(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    *,

    timeout_s: float,

    poll_interval_s: float = cfg.PGC_MOTION_POLL_INTERVAL_S,

) -> Result:

    """等待回零完成；须先观察到运动或 Bit6 由 0→1，避免沿用旧的「已回零」状态误判成功。"""

    start = time.monotonic()

    deadline = start + timeout_s

    motion_deadline = start + cfg.PGC_HOME_MOTION_START_TIMEOUT_S

    saw_moving = False

    saw_unhomed = False

    first_sample = True

    while time.monotonic() < deadline:

        value, err = _read_reg_soft(transact, slave_id, REG_STATUS_WORD)

        if err:

            if saw_moving or saw_unhomed:

                time.sleep(poll_interval_s)

                continue

            return False, f"读取状态字失败：{err}"

        if value is None:

            time.sleep(poll_interval_s)

            continue

        if value & STAT_ALARM:

            alarm, _ = _read_reg_soft(transact, slave_id, REG_ALARM)

            return False, f"回零报警，代码 0x{alarm:04X}" if alarm else "回零报警"

        if value & STAT_MOVING:

            saw_moving = True

        if not (value & STAT_HOMED):

            saw_unhomed = True

        if (

            not first_sample

            and (value & STAT_HOMED)

            and (saw_moving or saw_unhomed)

        ):

            return True, "回零完成"

        if (

            time.monotonic() >= motion_deadline

            and not saw_moving

            and not saw_unhomed

        ):

            sw = f"0x{value:04X}"

            return False, (

                f"回零未启动（{cfg.PGC_HOME_MOTION_START_TIMEOUT_S:g}s 内无运动；"

                f"0x1611={sw}）。请先「初始化」，或「失能」→「使能」后再「回零」。"

            )

        first_sample = False

        time.sleep(poll_interval_s)

    return False, "回零超时"





def _wait_motion_done(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    *,

    timeout_s: float,

    poll_interval_s: float,

    allow_stall: bool,

) -> Result:

    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:

        value, err = _read_reg(transact, slave_id, REG_STATUS_WORD)

        if err:

            return False, f"读取状态字失败：{err}"

        if value is None:

            time.sleep(poll_interval_s)

            continue

        if value & STAT_MOVING:

            time.sleep(poll_interval_s)

            continue

        if value & STAT_ALARM:

            if allow_stall:

                alarm, _ = _read_reg(transact, slave_id, REG_ALARM)

                if alarm == ALARM_STALL:

                    return True, "堵转（推压模式预期）"

            alarm, _ = _read_reg(transact, slave_id, REG_ALARM)

            code = f"0x{alarm:04X}" if alarm is not None else "未知"

            return False, f"运动报警，代码 {code}"

        if value & STAT_IN_POSITION:

            return True, "到位"

        time.sleep(poll_interval_s)

    return False, "电缸动作超时"





def set_enable(

    transact: Callable[[bytes, int], bytes],

    enabled: bool,

) -> Result:

    slave = cfg.MODBUS_SLAVE_ID

    if enabled:
        active, alarm_code, err = _read_alarm_state(transact, slave)
        if err:
            return False, err
        if active:
            ok, detail = clear_alarm(transact)
            if not ok:
                code_txt = f"0x{alarm_code:04X}" if alarm_code else "未知"
                return False, f"使能前清除报警失败（{code_txt}）：{detail}"
            ok, detail = _wait_alarm_cleared(transact, slave)
            if not ok:
                code_txt = f"0x{alarm_code:04X}" if alarm_code else "未知"
                return False, f"使能前报警未解除（{code_txt}）：{detail}"

        ok, detail = _write_motion_block(
            transact,
            slave,
            position_001mm=0,
            push_segment_001mm=0,
            speed_001mm_s=0,
            accel_percent=0,
            force_percent=0,
            control_word=cfg.PGC_CTRL_ENABLE,
        )
        if not ok:
            return False, detail
        return _wait_enabled_feedback(transact, slave)

    return _write_motion_block(

        transact,

        slave,

        position_001mm=0,

        push_segment_001mm=0,

        speed_001mm_s=0,

        accel_percent=0,

        force_percent=0,

        control_word=cfg.PGC_CTRL_DISABLE,

    )





def clear_alarm(transact: Callable[[bytes, int], bytes]) -> Result:

    slave = cfg.MODBUS_SLAVE_ID

    ok, detail = _write_motion_block(

        transact,

        slave,

        position_001mm=0,

        push_segment_001mm=0,

        speed_001mm_s=0,

        accel_percent=0,

        force_percent=0,

        control_word=cfg.PGC_CTRL_CLEAR_ALARM,

    )

    if not ok:

        return False, detail

    ok, detail = _wait_alarm_cleared(transact, slave)

    if ok:

        return True, "报警已清除。"

    return False, detail





def _home_device_once(

    transact: Callable[[bytes, int], bytes],

    *,

    timeout_s: float,

    poll_interval_s: float,

    trust_session: bool = False,

) -> Result:

    """单次回零：FC10 写 0x0020（使能+Bit1=0）→ 0x0022（回零上升沿）。"""

    slave = cfg.MODBUS_SLAVE_ID

    if not trust_session:

        ok, detail = _require_enabled(transact, slave)

        if not ok:

            return False, detail

    ok, detail = _write_motion_block(

        transact,

        slave,

        position_001mm=0,

        push_segment_001mm=0,

        speed_001mm_s=0,

        accel_percent=0,

        force_percent=0,

        control_word=cfg.PGC_CTRL_ENABLE,

    )

    if not ok:

        return False, detail

    time.sleep(cfg.PGC_HOME_PREP_DELAY_S)

    ok, detail = _write_motion_block(

        transact,

        slave,

        position_001mm=0,

        push_segment_001mm=0,

        speed_001mm_s=0,

        accel_percent=0,

        force_percent=0,

        control_word=cfg.PGC_CTRL_HOME,

    )

    if not ok:

        return False, detail

    return _wait_home_done(

        transact,

        slave,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

    )





def home_device(

    transact: Callable[[bytes, int], bytes],

    *,

    timeout_s: float = cfg.PGC_HOME_TIMEOUT_S,

    poll_interval_s: float = cfg.PGC_POLL_INTERVAL_S,

    trust_session: bool = False,

) -> Result:

    """回零：须已使能且已完成行程初始化；0x1605 Bit1 上升沿。"""

    return _home_device_once(

        transact,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

        trust_session=trust_session,

    )





def read_device_status(

    transact: Callable[[bytes, int], bytes],

) -> Tuple[PgcDeviceStatus, str]:

    """刷新状态：2 次 Modbus 读（0x160C~0x1611 批量 + 0x0200）。"""

    slave = cfg.MODBUS_SLAVE_ID

    status = PgcDeviceStatus()

    block, err = _read_regs(
        transact, slave, REG_POSITION_FB, cfg.PGC_STATUS_BLOCK_REGS
    )

    if err:

        return status, err

    if block and len(block) >= cfg.PGC_STATUS_BLOCK_REGS:

        status.position_mm = block[0] / 100.0

        status.alarm_code = block[3]

        word_val = block[5]

        status.status_word = word_val

        status.enabled = bool(word_val & STAT_ENABLED)

        status.homed = bool(word_val & STAT_HOMED)

        status.moving = bool(word_val & STAT_MOVING)

        status.alarm = bool(word_val & STAT_ALARM) or bool(block[3])

        status.home_status = 1 if status.homed else (2 if status.moving else 0)

        if word_val & STAT_IN_POSITION:

            status.run_status = 1

        elif status.moving:

            status.run_status = 0

        elif status.alarm:

            status.run_status = 2

    legacy_val, _ = _read_reg_soft(transact, slave, cfg.PGC_REG_LEGACY_STATUS)

    if legacy_val is not None:

        status.legacy_status = legacy_val

    return status, ""





def extend_thrust(

    transact: Callable[[bytes, int], bytes],

    *,

    thrust_percent: int,

    target_001mm: int,

    push_segment_001mm: int,

    speed_001mm_s: int,

    accel_percent: int,

    timeout_s: float = cfg.PGC_COMMAND_TIMEOUT_S,

    poll_interval_s: float = cfg.PGC_POLL_INTERVAL_S,

) -> Result:

    """伸出：0x1600 目标位置、0x1601 推压段、0x1604 推力；推压段>0 为推压模式，=0 为绝对定位。"""

    slave = cfg.MODBUS_SLAVE_ID

    ok, detail = _prepare_motion(transact, slave, verify=False)

    if not ok:

        return False, detail

    if push_segment_001mm > 0:

        control_word = cfg.PGC_CTRL_ABS_PUSH

        force_percent = thrust_percent

    else:

        control_word = cfg.PGC_CTRL_ABS_POS

        force_percent = 0

    ok, detail = _write_motion_block(

        transact,

        slave,

        position_001mm=target_001mm,

        push_segment_001mm=push_segment_001mm,

        speed_001mm_s=speed_001mm_s,

        accel_percent=accel_percent,

        force_percent=force_percent,

        control_word=control_word,

    )

    if not ok:

        return False, detail

    return _wait_motion_done(

        transact,

        slave,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

        allow_stall=True,

    )





def retract_absolute(

    transact: Callable[[bytes, int], bytes],

    *,

    target_001mm: int,

    speed_001mm_s: int,

    accel_percent: int,

    timeout_s: float = cfg.PGC_COMMAND_TIMEOUT_S,

    poll_interval_s: float = cfg.PGC_POLL_INTERVAL_S,

) -> Result:

    """缩回：绝对位置运动（推压段=0）。"""

    slave = cfg.MODBUS_SLAVE_ID

    ok, detail = _prepare_motion(transact, slave, verify=False)

    if not ok:

        return False, detail

    ok, detail = _write_motion_block(

        transact,

        slave,

        position_001mm=target_001mm,

        push_segment_001mm=0,

        speed_001mm_s=speed_001mm_s,

        accel_percent=accel_percent,

        force_percent=0,

        control_word=cfg.PGC_CTRL_ABS_POS,

    )

    if not ok:

        return False, detail

    return _wait_motion_done(

        transact,

        slave,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

        allow_stall=False,

    )





def read_position(

    transact: Callable[[bytes, int], bytes],

) -> Tuple[Optional[float], str]:

    value, err = _read_reg(transact, cfg.MODBUS_SLAVE_ID, REG_POSITION_FB)

    if err:

        return None, err

    if value is None:

        return None, "无位置反馈"

    return value / 100.0, ""

