"""ST5000P 移液枪：初始化 / 取液 / 排液 / 退枪头（经 ZLAN5212DI RS485）。"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from Drivers.Pipette import pipette_config as cfg
from Drivers.SerialServer import zlan5212di_transport as transport
from Drivers.Pipette import st5000p_protocol as proto

logger = logging.getLogger("soliddoser.pipette")

Result = Tuple[bool, str]

_driver: Optional["PipetteDriver"] = None


class PipetteDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.PIPETTE_USE_SIMULATION:
            return True
        if transport.sdk_available():
            return False
        logger.warning("ZLAN5212DI 串口服务器不可用，移液枪使用仿真模式")
        return True

    def _run(
        self,
        command: str,
        success_message: str,
    ) -> Result:
        if self._simulation:
            logger.info("pipette sim cmd=%s", command)
            return True, f"{success_message}（仿真）"

        try:
            ok, detail, _responses = proto.execute_command(
                transport.send_frame,
                transport.recv_frame,
                cfg.PIPETTE_DEVICE_ADDRESS,
                command,
                timeout_s=cfg.PIPETTE_COMMAND_TIMEOUT_S,
                poll_interval_s=cfg.PIPETTE_POLL_INTERVAL_S,
            )
        except Exception as exc:
            logger.exception("移液枪通讯异常")
            return False, str(exc)

        if ok:
            return True, success_message
        return False, detail

    def init_device(self) -> Result:
        return self._run(proto.build_init_command(), "移液枪已初始化")

    def aspirate(self, volume_ul: int) -> Result:
        if volume_ul <= 0:
            return False, "取液体积须大于 0 µL。"
        if volume_ul > 1100:
            return False, "取液体积不能超过 1100 µL（ST5000P 量程）。"
        cmd = proto.build_aspirate_command(volume_ul, cfg.PIPETTE_ASPIRATE_PROFILE)
        return self._run(cmd, f"已取液 {volume_ul} µL")

    def dispense(self, volume_ul: int) -> Result:
        if volume_ul <= 0:
            return False, "排液体积须大于 0 µL。"
        if volume_ul > 1100:
            return False, "排液体积不能超过 1100 µL（ST5000P 量程）。"
        cmd = proto.build_dispense_command(volume_ul, cfg.PIPETTE_DISPENSE_PROFILE)
        return self._run(cmd, f"已排液 {volume_ul} µL")

    def eject_tip(self) -> Result:
        return self._run(proto.build_eject_tip_command(), "已退枪头")


def get_pipette_driver() -> PipetteDriver:
    global _driver
    if _driver is None:
        _driver = PipetteDriver()
    return _driver