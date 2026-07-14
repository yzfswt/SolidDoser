"""赛多利斯 MCE524S 天平驱动（经 DW-RS20TM1 TCP→RS232 透传）。"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from Drivers.SartoriusBalance import balance_config as cfg
from Drivers.SartoriusBalance.balance_protocol import BalanceReading, parse_sbi_line
from Drivers.SerialServer.dw_rs20tm1_config import (
    SERIAL_SERVER_HOST,
    SERIAL_SERVER_PORT,
)
from Drivers.SerialServer.dw_rs20tm1_transport import DwRs20tm1TcpClient

logger = logging.getLogger("soliddoser.balance")

Result = Tuple[bool, str]
ReadResult = Tuple[Optional[BalanceReading], str]

_driver: Optional["SartoriusBalanceDriver"] = None


class SartoriusBalanceDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._client = DwRs20tm1TcpClient()

    @property
    def simulation(self) -> bool:
        return self._simulation

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.BALANCE_USE_SIMULATION:
            return True
        client = DwRs20tm1TcpClient()
        ok, _ = client.test_connection()
        if ok:
            return False
        logger.warning(
            "无法连接串口服务器 %s:%s（天平 %s），使用仿真模式",
            SERIAL_SERVER_HOST,
            SERIAL_SERVER_PORT,
            cfg.BALANCE_MODEL,
        )
        return True

    def test_connection(self) -> Result:
        if self._simulation:
            return (
                True,
                f"仿真模式（{SERIAL_SERVER_HOST}:{SERIAL_SERVER_PORT} · {cfg.BALANCE_MODEL}）",
            )
        return self._client.test_connection()

    def _command(self, cmd: bytes, *, expect_reply: bool) -> ReadResult:
        if self._simulation:
            if expect_reply:
                reading, _ = parse_sbi_line("+    12.3456 g")
                return reading, ""
            return (
                BalanceReading(raw="", value=None, unit="", id_code="", display="OK"),
                "",
            )

        raw, err = self._client.transact(cmd)
        if not expect_reply:
            if err and "超时" in err:
                return (
                    BalanceReading(
                        raw="", value=None, unit="", id_code="", display="已发送"
                    ),
                    "",
                )
            if raw is None and err:
                return None, err
            reading, parse_err = parse_sbi_line(raw or b"")
            if reading is None and parse_err and raw:
                return (
                    BalanceReading(
                        raw=raw.decode("ascii", errors="replace").strip(),
                        value=None,
                        unit="",
                        id_code="",
                        display="已发送",
                    ),
                    "",
                )
            return reading, parse_err

        if raw is None:
            return None, err
        return parse_sbi_line(raw)

    def read_weight(self) -> ReadResult:
        return self._command(cfg.CMD_PRINT, expect_reply=True)

    def tare(self) -> ReadResult:
        return self._command(cfg.CMD_TARE, expect_reply=False)

    def zero(self) -> ReadResult:
        return self._command(cfg.CMD_ZERO, expect_reply=False)


def get_balance_driver() -> SartoriusBalanceDriver:
    global _driver
    if _driver is None:
        _driver = SartoriusBalanceDriver()
    return _driver
