"""SolidDoser 主运动轴配置：汇川 AM600-CPU1608TN + EtherCAT。

4 台伺服（水平 / 分度 / 升降 / 搅拌）+ 1 台承粉步进，经 EtherCAT 挂 AM600。
上位机经 Modbus TCP 写 M 脉冲、D 目标/速度，由 PLC 侧 MC 指令驱动 EtherCAT 轴。
显示顺序与 SoftMotion 轴号一致：0 水平 / 1 分度 / 2 升降 / 3 搅拌 / 4 承粉。

通讯参数见 Common/PlcConfig.py；点表见
Dependencies/汇川/AM600-CPU1608TN/SOLIDDOSER_MOTION_PLC_INTERFACE.md。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from Common.PlcConfig import MODBUS_SLAVE_ID, PLC_HOST, PLC_MODEL, PLC_PORT

MOTION_USE_SIMULATION = False

COMMAND_TIMEOUT_S = 120.0
DATUM_TIMEOUT_S = 180.0  # 找外部基准点（PLC CmdHome / MC_Home）超时
POWER_ON_TIMEOUT_S = 15.0
POLL_INTERVAL_S = 0.2
POSITION_MATCH_TOLERANCE = 0.5

# 分度盘：8 工位，工位号 0～7，相邻相差 45°
INDEXING_STATION_COUNT = 8
INDEXING_STEP_DEG = 45.0
INDEXING_AXIS_KEY = "indexing"

# 水平轴命名位置（mm）：原点 / 空闲 / 工作
HORIZONTAL_AXIS_KEY = "horizontal"


@dataclass(frozen=True)
class IndexingNamedPosition:
    key: str
    label: str
    position_deg: float


# 分度轴命名位置（°）：原点对应工位 0
INDEXING_POSITIONS: Tuple[IndexingNamedPosition, ...] = (
    IndexingNamedPosition("origin", "原点位置", 0.0),
)

INDEXING_POSITION_BY_KEY: Dict[str, IndexingNamedPosition] = {
    p.key: p for p in INDEXING_POSITIONS
}


def indexing_position_deg(key: str) -> float:
    """按命名位置 key 取目标角度（°）。"""
    if key not in INDEXING_POSITION_BY_KEY:
        raise KeyError(f"未知分度位置: {key}")
    return INDEXING_POSITION_BY_KEY[key].position_deg


@dataclass(frozen=True)
class HorizontalNamedPosition:
    key: str
    label: str
    position_mm: float


HORIZONTAL_POSITIONS: Tuple[HorizontalNamedPosition, ...] = (
    HorizontalNamedPosition("origin", "原点位置", 0.0),
    HorizontalNamedPosition("idle", "空闲位置", 10.0),
    HorizontalNamedPosition("work", "工作位置", 20.0),
)

HORIZONTAL_POSITION_BY_KEY: Dict[str, HorizontalNamedPosition] = {
    p.key: p for p in HORIZONTAL_POSITIONS
}


def horizontal_position_mm(key: str) -> float:
    """按命名位置 key 取目标行程（mm）。"""
    if key not in HORIZONTAL_POSITION_BY_KEY:
        raise KeyError(f"未知水平位置: {key}")
    return HORIZONTAL_POSITION_BY_KEY[key].position_mm


# 升降轴命名位置（mm）：原点 / 空闲 / 工作
LIFT_AXIS_KEY = "lift"


@dataclass(frozen=True)
class LiftNamedPosition:
    key: str
    label: str
    position_mm: float


LIFT_POSITIONS: Tuple[LiftNamedPosition, ...] = (
    LiftNamedPosition("origin", "原点位置", 0.0),
    LiftNamedPosition("idle", "空闲位置", 10.0),
    LiftNamedPosition("work", "工作位置", 20.0),
)

LIFT_POSITION_BY_KEY: Dict[str, LiftNamedPosition] = {
    p.key: p for p in LIFT_POSITIONS
}


def lift_position_mm(key: str) -> float:
    """按命名位置 key 取目标行程（mm）。"""
    if key not in LIFT_POSITION_BY_KEY:
        raise KeyError(f"未知升降位置: {key}")
    return LIFT_POSITION_BY_KEY[key].position_mm


# 承粉轴命名位置（mm）：原点 / 空闲 / 工作
POWDER_AXIS_KEY = "powder"


@dataclass(frozen=True)
class PowderNamedPosition:
    key: str
    label: str
    position_mm: float


POWDER_POSITIONS: Tuple[PowderNamedPosition, ...] = (
    PowderNamedPosition("origin", "原点位置", 0.0),
    PowderNamedPosition("idle", "空闲位置", 10.0),
    PowderNamedPosition("work", "工作位置", 20.0),
)

POWDER_POSITION_BY_KEY: Dict[str, PowderNamedPosition] = {
    p.key: p for p in POWDER_POSITIONS
}


def powder_position_mm(key: str) -> float:
    """按命名位置 key 取目标行程（mm）。"""
    if key not in POWDER_POSITION_BY_KEY:
        raise KeyError(f"未知承粉位置: {key}")
    return POWDER_POSITION_BY_KEY[key].position_mm


def indexing_station_to_angle(station: int) -> float:
    """工位号 → 目标角度（°）。"""
    s = station % INDEXING_STATION_COUNT
    if s < 0:
        s += INDEXING_STATION_COUNT
    return s * INDEXING_STEP_DEG


def indexing_angle_to_station(angle_deg: float) -> int:
    """角度 → 最近工位号（0～7），用于绝对定位后同步逻辑工位。"""
    return int(round(angle_deg / INDEXING_STEP_DEG)) % INDEXING_STATION_COUNT


def normalize_indexing_station(station: int) -> int:
    s = station % INDEXING_STATION_COUNT
    if s < 0:
        s += INDEXING_STATION_COUNT
    return s


@dataclass(frozen=True)
class AxisMap:
    key: str
    label: str
    motor_type: str
    m_cmd_power: int
    m_status_power_ok: int
    # 下列线圈对应 PLC CmdHome / StatusHomeDone / StatusHomed（找基准点 datum）
    m_cmd_home: int
    m_status_home_done: int
    m_cmd_move: int
    m_status_move_done: int
    m_cmd_stop: int
    m_status_homed: int
    m_status_moving: int
    m_status_alarm: int
    d_target: int
    d_velocity: int
    d_actual: int
    pos_min: float
    pos_max: float
    vel_default: float
    unit: str


def _axis_block(
    key: str,
    label: str,
    motor_type: str,
    m_base: int,
    d_target: int,
    *,
    pos_min: float,
    pos_max: float,
    vel_default: float,
    unit: str,
) -> AxisMap:
    return AxisMap(
        key=key,
        label=label,
        motor_type=motor_type,
        m_cmd_power=m_base,
        m_status_power_ok=m_base + 2,
        m_cmd_home=m_base + 10,
        m_status_home_done=m_base + 20,
        m_cmd_move=m_base + 12,
        m_status_move_done=m_base + 21,
        m_cmd_stop=m_base + 13,
        m_status_homed=m_base + 22,
        m_status_moving=m_base + 23,
        m_status_alarm=m_base + 24,
        d_target=d_target,
        d_velocity=d_target + 2,
        d_actual=d_target + 4,
        pos_min=pos_min,
        pos_max=pos_max,
        vel_default=vel_default,
        unit=unit,
    )


AXES: Tuple[AxisMap, ...] = (
    _axis_block(
        "horizontal",
        "水平电机",
        "SV630N",
        m_base=500,
        d_target=500,
        pos_min=0.0,
        pos_max=2000.0,
        vel_default=100.0,
        unit="mm",
    ),
    _axis_block(
        "indexing",
        "分度电机",
        "SV630N",
        m_base=590,
        d_target=530,
        pos_min=0.0,
        pos_max=360.0,
        vel_default=30.0,
        unit="°",
    ),
    _axis_block(
        "lift",
        "升降电机",
        "SV630N",
        m_base=530,
        d_target=510,
        pos_min=0.0,
        pos_max=500.0,
        vel_default=50.0,
        unit="mm",
    ),
    _axis_block(
        "stirring",
        "搅拌电机",
        "SV630N",
        m_base=560,
        d_target=520,
        pos_min=0.0,
        pos_max=360.0,
        vel_default=60.0,
        unit="°",
    ),
    _axis_block(
        "powder",
        "承粉电机",
        "STF05-ECX-H",
        m_base=620,
        d_target=540,
        pos_min=0.0,
        pos_max=200.0,
        vel_default=20.0,
        unit="mm",
    ),
)

AXIS_BY_KEY: Dict[str, AxisMap] = {axis.key: axis for axis in AXES}


@dataclass(frozen=True)
class DoOutputMap:
    key: str
    label: str
    m_coil: int
    q_name: str


# DO 输出：上位机写 M 线圈，PLC 程序映射至 Q 点
DO_OUTPUTS: Tuple[DoOutputMap, ...] = (
    DoOutputMap("vibration", "振动电机", 650, "Q0"),
    DoOutputMap("ion_fan", "离子风扇", 651, "Q1"),
)

DO_BY_KEY: Dict[str, DoOutputMap] = {item.key: item for item in DO_OUTPUTS}


@dataclass(frozen=True)
class DiInputMap:
    key: str
    label: str
    x_address: int  # AM600 X 点 Modbus 地址（X0=0, X6=6, X8=8, XA=10 …）
    x_name: str     # 丝印名，如 "Xn6"


# DI 输入：试剂瓶有无传感器，接 AM600 Xn6 / Xn8 / XnA
DI_INPUTS: Tuple[DiInputMap, ...] = (
    DiInputMap("bottle_1", "试剂瓶1", 6, "Xn6"),
    DiInputMap("bottle_2", "试剂瓶2", 8, "Xn8"),
    DiInputMap("bottle_3", "试剂瓶3", 10, "XnA"),
)

DI_BY_KEY: Dict[str, DiInputMap] = {item.key: item for item in DI_INPUTS}
