"""料盘 32 仓位状态模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from Common.TrayGeometry import (
    MaterialType,
    TOTAL_SLOTS,
    TraySlotCoord,
    calc_slot_coord,
)


@dataclass
class TraySlotState:
    """单个仓位：是否有料、物料类型、机械坐标。"""

    slot_id: int
    has_material: bool = False
    material_type: MaterialType = MaterialType.NONE

    @property
    def coord(self) -> TraySlotCoord:
        return calc_slot_coord(self.slot_id)

    def effective_material_type(self) -> MaterialType:
        if not self.has_material:
            return MaterialType.NONE
        return self.material_type


class TrayModel:
    """料盘 A(1–16) + 料盘 B(17–32)。"""

    def __init__(self) -> None:
        self.slots: Dict[int, TraySlotState] = {
            i: TraySlotState(slot_id=i) for i in range(1, TOTAL_SLOTS + 1)
        }

    def get_slot(self, slot_id: int) -> TraySlotState:
        return self.slots[slot_id]

    def set_slot(
        self,
        slot_id: int,
        has_material: bool,
        material_type: MaterialType,
    ) -> None:
        slot = self.slots[slot_id]
        slot.has_material = has_material
        if has_material and material_type == MaterialType.NONE:
            slot.material_type = MaterialType.SOLID
        else:
            slot.material_type = material_type if has_material else MaterialType.NONE

    def slots_with_material(self) -> List[TraySlotState]:
        return [s for s in self.slots.values() if s.has_material]

    def occupied_count(self) -> int:
        return sum(1 for s in self.slots.values() if s.has_material)

    def to_dict(self) -> dict:
        return {
            str(sid): {
                "has_material": s.has_material,
                "material_type": s.material_type.value,
                "x": s.coord.x,
                "y": s.coord.y,
                "z": s.coord.z,
            }
            for sid, s in self.slots.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrayModel:
        model = cls()
        for key, item in data.items():
            sid = int(key)
            if sid not in model.slots:
                continue
            mt = MaterialType(item.get("material_type", "none"))
            has = bool(item.get("has_material", False))
            model.set_slot(sid, has, mt)
        return model
