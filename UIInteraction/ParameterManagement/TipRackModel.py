"""枪头架 56 枪头位状态模型。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from Common.TipRackGeometry import TOTAL_TIPS, TipRackCoord, calc_tip_coord


@dataclass
class TipSlotState:
    """单个枪头位：架上是否仍有可用枪头。"""

    tip_id: int
    has_tip: bool = False

    @property
    def coord(self) -> TipRackCoord:
        return calc_tip_coord(self.tip_id)


class TipRackModel:
    """枪头架 A(1–28) + B(29–56)。"""

    def __init__(self) -> None:
        self.slots: Dict[int, TipSlotState] = {
            i: TipSlotState(tip_id=i) for i in range(1, TOTAL_TIPS + 1)
        }

    def get_slot(self, tip_id: int) -> TipSlotState:
        return self.slots[tip_id]

    def set_has_tip(self, tip_id: int, has_tip: bool) -> None:
        self.slots[tip_id].has_tip = has_tip

    def set_range_has_tip(self, tip_id_min: int, tip_id_max: int, has_tip: bool) -> None:
        for tip_id in range(tip_id_min, tip_id_max + 1):
            self.set_has_tip(tip_id, has_tip)

    def slots_with_tip(self) -> List[TipSlotState]:
        return [s for s in self.slots.values() if s.has_tip]

    def available_count(self) -> int:
        return sum(1 for s in self.slots.values() if s.has_tip)

    def to_dict(self) -> dict:
        return {
            str(tid): {
                "has_tip": s.has_tip,
                "x": s.coord.x,
                "y": s.coord.y,
                "z": s.coord.z,
            }
            for tid, s in self.slots.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> TipRackModel:
        model = cls()
        for key, item in data.items():
            tid = int(key)
            if tid not in model.slots:
                continue
            model.set_has_tip(tid, bool(item.get("has_tip", False)))
        return model
