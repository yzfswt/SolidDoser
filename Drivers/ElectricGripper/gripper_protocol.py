"""PGC 电爪 Modbus-RTU 0x0100 协议（大寰 PGC 手册 2.3 节）。"""

from __future__ import annotations



import time

from typing import Callable, List, Optional, Tuple



from Drivers.ElectricActuator.modbus_rtu import (

    build_read_registers,

    build_write_register,

    build_write_registers,

    parse_read_registers,

    parse_read_u16,

    parse_write_response,

)

from Drivers.ElectricGripper import gripper_config as cfg

from Drivers.ElectricGripper.gripper_status import GripperDeviceStatus



Result = Tuple[bool, str]



REG_HOME = 0x0100

REG_FORCE = 0x0101

REG_PUSH_SEGMENT = 0x0102

REG_TARGET_POS = 0x0103

REG_MAX_SPEED = 0x0104

REG_ACCEL = 0x0105

REG_HOME_STATUS = 0x0200

REG_RUN_STATUS = 0x0201

REG_POSITION_FB = 0x0202



RUN_MOVING = 0

RUN_ARRIVED = 1

RUN_GRIPPED = 2

RUN_DROPPED = 3

RUN_STALL = RUN_GRIPPED



INIT_NOT_DONE = 0

INIT_DONE = 1

INIT_IN_PROGRESS = 2



HOME_NOT_DONE = INIT_NOT_DONE

HOME_DONE = INIT_DONE

HOME_IN_PROGRESS = INIT_IN_PROGRESS





def mm_to_permille(mm: float) -> int:

    ratio = mm / cfg.GRIPPER_MAX_STROKE_MM

    return max(0, min(cfg.GRIPPER_POSITION_PERMILLE_MAX, int(round(ratio * 1000))))





def permille_to_mm(permille: int) -> float:

    return permille / cfg.GRIPPER_POSITION_PERMILLE_MAX * cfg.GRIPPER_MAX_STROKE_MM





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





def _write_regs(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    start_address: int,

    values: List[int],

) -> Result:

    req = build_write_registers(slave_id, start_address, values)

    resp = transact(req, min_response_len=8)

    ok, detail = parse_write_response(resp, slave_id)

    if not ok:

        return False, detail or f"批量写入 0x{start_address:04X} 失败"

    return True, ""





def _read_reg(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

) -> Tuple[Optional[int], str]:

    req = build_read_registers(slave_id, address, 1)

    resp = transact(req, min_response_len=7)

    return parse_read_u16(resp, slave_id)





def _read_regs(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    address: int,

    count: int,

) -> Tuple[Optional[List[int]], str]:

    req = build_read_registers(slave_id, address, count)

    min_len = 5 + count * 2

    resp = transact(req, min_response_len=min_len)

    return parse_read_registers(resp, slave_id, count)





def _read_motion_feedback(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

) -> Tuple[Optional[int], Optional[int], str]:

    """一次读取 0x0201 运行状态 + 0x0202 位置反馈。"""

    values, err = _read_regs(transact, slave_id, REG_RUN_STATUS, 2)

    if err:

        return None, None, err

    if values is None or len(values) < 2:

        return None, None, "运行/位置反馈为空"

    return values[0], values[1], ""





def _at_target(pos_permille: Optional[int], target_permille: int) -> bool:

    if pos_permille is None:

        return False

    return abs(pos_permille - target_permille) <= cfg.GRIPPER_POSITION_TOLERANCE_PERMILLE





def _wait_motion_done(

    transact: Callable[[bytes, int], bytes],

    slave_id: int,

    *,

    timeout_s: float,

    poll_interval_s: float,

    allow_gripped: bool,

    target_permille: Optional[int] = None,

) -> Result:

    deadline = time.monotonic() + timeout_s

    no_motion_deadline = time.monotonic() + cfg.GRIPPER_NO_MOTION_TIMEOUT_S

    _, start_pos, _ = _read_motion_feedback(transact, slave_id)

    seen_moving = False



    while time.monotonic() < deadline:

        run_val, pos_val, err = _read_motion_feedback(transact, slave_id)

        if err:

            return False, f"读取运行状态失败：{err}"



        if run_val == RUN_MOVING:

            seen_moving = True

        elif (

            start_pos is not None

            and pos_val is not None

            and abs(pos_val - start_pos) > cfg.GRIPPER_POSITION_TOLERANCE_PERMILLE

        ):

            seen_moving = True



        if seen_moving:

            if run_val == RUN_ARRIVED:

                return True, "到位"

            if run_val == RUN_GRIPPED and allow_gripped:

                return True, "夹住物体"

            if run_val == RUN_DROPPED:

                return False, "物体掉落"

            if run_val not in (RUN_MOVING,):

                return False, f"运行异常，状态码 {run_val}"



        if target_permille is not None and _at_target(pos_val, target_permille):

            if run_val in (RUN_ARRIVED, RUN_GRIPPED):

                return True, "到位"



        if (

            not seen_moving

            and target_permille is not None

            and time.monotonic() >= no_motion_deadline

        ):

            if _at_target(start_pos, target_permille):

                return True, "已在目标位置"

            return False, "电爪未开始运动（请确认已初始化且目标位置有效）"



        time.sleep(poll_interval_s)



    _, pos_val, _ = _read_motion_feedback(transact, slave_id)

    if target_permille is not None and _at_target(pos_val, target_permille):

        return True, "到位（位置已到达）"

    return False, "电爪动作超时"





def _wait_init_done(

    transact: Callable[[bytes, int], bytes],

    *,

    timeout_s: float,

    poll_interval_s: float,

) -> Result:

    slave = cfg.MODBUS_SLAVE_ID

    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:

        value, err = _read_reg(transact, slave, REG_HOME_STATUS)

        if err:

            return False, f"读取初始化状态失败：{err}"

        if value == INIT_DONE:

            return True, "初始化完成"

        if value in (INIT_NOT_DONE, INIT_IN_PROGRESS):

            time.sleep(poll_interval_s)

            continue

        return False, f"初始化异常，状态码 {value}"

    return False, "初始化超时"





def _trigger_init(

    transact: Callable[[bytes, int], bytes],

    command: int,

    *,

    timeout_s: float,

    poll_interval_s: float = cfg.GRIPPER_POLL_INTERVAL_S,

) -> Result:

    slave = cfg.MODBUS_SLAVE_ID

    ok, detail = _write_reg(transact, slave, REG_HOME, command)

    if not ok:

        return False, detail

    return _wait_init_done(

        transact,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

    )





def init_device(

    transact: Callable[[bytes, int], bytes],

    *,

    timeout_s: float = cfg.GRIPPER_INIT_TIMEOUT_S,

    poll_interval_s: float = cfg.GRIPPER_POLL_INTERVAL_S,

) -> Result:

    return _trigger_init(

        transact,

        cfg.GRIPPER_CMD_CALIBRATE,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

    )





def home_device(

    transact: Callable[[bytes, int], bytes],

    *,

    timeout_s: float = cfg.GRIPPER_HOME_TIMEOUT_S,

    poll_interval_s: float = cfg.GRIPPER_POLL_INTERVAL_S,

) -> Result:

    return _trigger_init(

        transact,

        cfg.GRIPPER_CMD_HOME,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

    )





def read_device_status(

    transact: Callable[[bytes, int], bytes],

) -> Tuple[GripperDeviceStatus, str]:

    slave = cfg.MODBUS_SLAVE_ID

    status = GripperDeviceStatus()



    values, err = _read_regs(transact, slave, REG_HOME_STATUS, 3)

    if err:

        return status, err

    if values is None or len(values) < 3:

        return status, "状态反馈为空"



    home_val, run_val, pos_val = values

    status.home_status = home_val

    status.homed = home_val == INIT_DONE

    status.homing = home_val == INIT_IN_PROGRESS

    status.run_status = run_val

    status.moving = run_val == RUN_MOVING

    status.position_mm = permille_to_mm(pos_val)

    return status, ""





def move_absolute(
    transact: Callable[[bytes, int], bytes],
    *,
    target_permille: int,
    speed_percent: int,
    accel_percent: int,
    timeout_s: float = cfg.GRIPPER_COMMAND_TIMEOUT_S,
    poll_interval_s: float = cfg.GRIPPER_POLL_INTERVAL_S,
) -> Result:
    """绝对位置运动（打开/移动到指定开口）。"""
    slave = cfg.MODBUS_SLAVE_ID
    ok, detail = _write_regs(
        transact,
        slave,
        REG_TARGET_POS,
        [target_permille, speed_percent, accel_percent],
    )
    if not ok:
        return False, detail
    return _wait_motion_done(
        transact,
        slave,
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        allow_gripped=False,
        target_permille=target_permille,
    )


def grip_push(

    transact: Callable[[bytes, int], bytes],

    *,

    force_percent: int,

    target_permille: int,

    push_segment_permille: int,

    speed_percent: int,

    accel_percent: int,

    timeout_s: float = cfg.GRIPPER_COMMAND_TIMEOUT_S,

    poll_interval_s: float = cfg.GRIPPER_POLL_INTERVAL_S,

) -> Result:

    """力控推压夹持：FC10 一次写入 0x0101–0x0105。"""

    slave = cfg.MODBUS_SLAVE_ID

    force = max(cfg.GRIPPER_MIN_FORCE_PERCENT, min(100, force_percent))

    ok, detail = _write_regs(

        transact,

        slave,

        REG_FORCE,

        [force, push_segment_permille, target_permille, speed_percent, accel_percent],

    )

    if not ok:

        return False, detail

    return _wait_motion_done(

        transact,

        slave,

        timeout_s=timeout_s,

        poll_interval_s=poll_interval_s,

        allow_gripped=True,

        target_permille=target_permille,

    )





extend_push = grip_push
retract_absolute = move_absolute


def read_position(

    transact: Callable[[bytes, int], bytes],

) -> Tuple[Optional[float], str]:

    value, err = _read_reg(transact, cfg.MODBUS_SLAVE_ID, REG_POSITION_FB)

    if err:

        return None, err

    if value is None:

        return None, "无位置反馈"

    return permille_to_mm(value), ""

