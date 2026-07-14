"""基恩士扫码枪状态（调试界面同步）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScannerState:
    connected: bool = False
    simulation_mode: bool = False
    last_barcode: str = ""
    read_history: List[str] = field(default_factory=list)
    last_action: str = ""
    last_message: str = ""
    last_success: bool = True

    def append_history(self, barcode: str, *, limit: int = 20) -> None:
        if not barcode:
            return
        self.read_history.insert(0, barcode)
        del self.read_history[limit:]
