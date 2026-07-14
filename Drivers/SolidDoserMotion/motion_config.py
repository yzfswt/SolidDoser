"""SolidDoser 主运动轴配置：汇川 AM600-CPU1608TN + EtherCAT。

4 台伺服（水平 / 升降 / 搅拌 / 分度）+ 1 台承粉步进，经 EtherCAT 挂 AM600。
上位机经 Modbus TCP 写 M 脉冲、D 目标/速度，由 PLC 侧 MC 指令驱动 EtherCAT 轴。

通讯参数见 Common/PlcConfig.py；点表见
Dependencies/汇川/AM600-CPU1608TN/SOLIDDOSER_MOTION_PLC_INTERFACE.md。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from Common.PlcConfig import MODBUS_SLAVE_ID, PLC_HOST, PLC_MODEL, PLC_PORT

MOTION_USE_SIMULATION = False

COMMAND_TIMEOUT_S = 120.0
HOME_TIMEOUT_S = 180.0
POWER_ON_TIMEOUT_S = 15.0
POLL_INTERVAL_S = 0.2
POSITION_MATCH_TOLERANCE = 0.5


@dataclass(frozen=True)
class AxisMap:
    key: str
    label: str
    motor_type: str
    m_cmd_power: int
    m_status_power_ok: int
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
