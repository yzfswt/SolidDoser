"""末端工具检测：经 ZLAN5212DI RS485 按从站地址识别当前工具。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Tuple

from Drivers.ElectricActuator import pgc_config as pgc_cfg
from Drivers.ElectricActuator import modbus_rtu as mb
from Drivers.ElectricActuator.pgc_protocol import REG_STATUS_WORD as PGC_REG_STATUS
from Drivers.ElectricGripper import gripper_config as gripper_cfg
from Drivers.ElectricGripper.gripper_protocol import REG_HOME_STATUS as GRIPPER_REG_HOME_STATUS
from Drivers.Pipette import pipette_config as pipette_cfg
from Drivers.Pipette import st5000p_protocol as pipette_proto
from Drivers.SerialServer import zlan5212di_transport as transport
from UIInteraction.ParameterManagement.RobotModel import HeldTool

Result = Tuple[bool, str]


@dataclass(frozen=True)
class ToolProbeTarget:
    tool: HeldTool
    label: str
    address: int


TOOL_PROBE_TARGETS: tuple[ToolProbeTarget, ...] = (
    ToolProbeTarget(HeldTool.GRIPPER, "电爪", gripper_cfg.MODBUS_SLAVE_ID),
    ToolProbeTarget(HeldTool.ELECTRIC_ACTUATOR, "电缸", pgc_cfg.MODBUS_SLAVE_ID),
    ToolProbeTarget(HeldTool.PIPETTE, "移液枪", pipette_cfg.PIPETTE_DEVICE_ADDRESS),
)

PROBE_TIMEOUT_S = 0.35
PIPETTE_PROBE_POLL_S = 0.02


def _probe_modbus(slave_id: int, register: int, *, count: int = 1) -> bool:
    req = mb.build_read_registers(slave_id, register, count)
    resp = transport.transact(
        req,
        min_response_len=5 + count * 2,
        timeout_s=PROBE_TIMEOUT_S,
    )
    _, err = mb.parse_read_registers(resp, slave_id, count)
    return not err


def _probe_gripper() -> bool:
    return _probe_modbus(gripper_cfg.MODBUS_SLAVE_ID, GRIPPER_REG_HOME_STATUS)


def _probe_pgc() -> bool:
    return _probe_modbus(pgc_cfg.MODBUS_SLAVE_ID, PGC_REG_STATUS)


def _probe_pipette() -> bool:
    return pipette_proto.probe_device(
        transport.send_frame,
        transport.recv_frame,
        pipette_cfg.PIPETTE_DEVICE_ADDRESS,
        timeout_s=PROBE_TIMEOUT_S,
        poll_interval_s=PIPETTE_PROBE_POLL_S,
    )


def _probe_target(target: ToolProbeTarget) -> bool:
    if target.tool == HeldTool.GRIPPER:
        return _probe_gripper()
    if target.tool == HeldTool.ELECTRIC_ACTUATOR:
        return _probe_pgc()
    if target.tool == HeldTool.PIPETTE:
        return _probe_pipette()
    return False


def detect_attached_tool() -> Tuple[HeldTool, str]:
    """扫描 RS485 从站，返回识别到的末端工具与说明文字。"""
    if not transport.sdk_available():
        return HeldTool.NONE, "串口服务器不可用"

    found: List[ToolProbeTarget] = []
    errors: List[str] = []
    for target in TOOL_PROBE_TARGETS:
        try:
            if _probe_target(target):
                found.append(target)
        except (RuntimeError, OSError) as exc:
            errors.append(f"{target.label}(地址{target.address})：{exc}")

    if errors and not found:
        return HeldTool.NONE, "；".join(errors)

    if not found:
        extra = f"（{'；'.join(errors)}）" if errors else ""
        return HeldTool.NONE, f"未检测到工具（地址 1/2/3 均无有效应答）{extra}"

    if len(found) > 1:
        names = "、".join(f"{t.label}(地址{t.address})" for t in found)
        return (
            HeldTool.NONE,
            f"检测到多个工具应答：{names}，请确认总线上仅连接一个末端工具。",
        )

    target = found[0]
    return (
        target.tool,
        f"检测到{target.label}（RS485 地址 {target.address}）",
    )
