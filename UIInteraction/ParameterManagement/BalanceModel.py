"""赛多利斯天平状态（调试界面同步）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BalanceState:
    connected: bool = False
    simulation_mode: bool = False
    last_weight_display: str = ""
    last_weight_value: Optional[float] = None
    last_weight_unit: str = ""
    last_raw: str = ""
    read_history: List[str] = field(default_factory=list)
    last_action: str = ""
    last_message: str = ""
    last_success: bool = True

    def append_history(self, text: str, *, limit: int = 20) -> None:
        if not text:
            return
        self.read_history.insert(0, text)
        del self.read_history[limit:]
