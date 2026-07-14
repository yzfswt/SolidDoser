"""基恩士 SR-X100WP 扫码枪驱动。"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from Drivers.KeyenceScanner import scanner_config as cfg
from Drivers.KeyenceScanner.scanner_protocol import KeyenceScannerTcpClient

logger = logging.getLogger("soliddoser.scanner")

Result = Tuple[bool, str]
ReadResult = Tuple[Optional[str], str]

_driver: Optional["KeyenceScannerDriver"] = None


class KeyenceScannerDriver:
    def __init__(self) -> None:
        self._simulation = self._resolve_simulation_mode()
        self._client = KeyenceScannerTcpClient()

    @property
    def simulation(self) -> bool:
        return self._simulation

    @staticmethod
    def _resolve_simulation_mode() -> bool:
        if cfg.SCANNER_USE_SIMULATION:
            return True
        client = KeyenceScannerTcpClient()
        ok, _ = client.test_connection()
        if ok:
            return False
        logger.warning(
            "无法连接扫码枪 %s:%s，扫码功能使用仿真模式",
            cfg.SCANNER_HOST,
            cfg.SCANNER_PORT,
        )
        return True

    def test_connection(self) -> Result:
        if self._simulation:
            return True, f"仿真模式（{cfg.SCANNER_HOST}:{cfg.SCANNER_PORT}）"
        return self._client.test_connection()

    def trigger_read(self) -> ReadResult:
        if self._simulation:
            return "SIM-DEMO-001", ""
        return self._client.trigger_read()


def get_scanner_driver() -> KeyenceScannerDriver:
    global _driver
    if _driver is None:
        _driver = KeyenceScannerDriver()
    return _driver
