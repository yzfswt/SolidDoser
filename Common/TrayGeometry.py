"""料盘几何与仓位编号（SolidDoser 项目）。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class MaterialType(str, Enum):
    """物料类型。"""

    NONE = "none"
    SOLID = "solid"
    LIQUID = "liquid"

    @classmethod
    def from_label(cls, label: str) -> MaterialType:
        mapping = {
            "无": cls.NONE,
            "固体": cls.SOLID,
            "液体": cls.LIQUID,
        }
        return mapping.get(label, cls.NONE)

    def to_label(self) -> str:
        return {
            MaterialType.NONE: "无",
            MaterialType.SOLID: "固体",
            MaterialType.LIQUID: "液体",
        }[self]


# 料盘 A：仓位 1–16，原点 (0, 0, 0)
TRAY_A_ORIGIN_X = 0.0
TRAY_A_ORIGIN_Y = 0.0
TRAY_A_ORIGIN_Z = 0.0

# 料盘 B：仓位 17–32，原点 (500, 500, 500)
TRAY_B_ORIGIN_X = 500.0
TRAY_B_ORIGIN_Y = 500.0
TRAY_B_ORIGIN_Z = 500.0

# 相邻仓位间距（mm）
SLOT_SPACING_X = 10.0
SLOT_SPACING_Y = 10.0

GRID_COLS = 4
GRID_ROWS = 4
SLOTS_PER_TRAY = GRID_COLS * GRID_ROWS  # 16
TOTAL_SLOTS = SLOTS_PER_TRAY * 2  # 32

TRAY_A_SLOT_MIN = 1
TRAY_A_SLOT_MAX = 16
TRAY_B_SLOT_MIN = 17
TRAY_B_SLOT_MAX = 32


@dataclass(frozen=True)
class TraySlotCoord:
    """单个仓位的机械坐标。"""

    slot_id: int
    tray_part: str  # "A" or "B"
    row: int  # 0–3
    col: int  # 0–3
    x: float
    y: float
    z: float


def _tray_part_and_local_index(slot_id: int) -> Tuple[str, int]:
    if TRAY_A_SLOT_MIN <= slot_id <= TRAY_A_SLOT_MAX:
        return "A", slot_id - TRAY_A_SLOT_MIN
    if TRAY_B_SLOT_MIN <= slot_id <= TRAY_B_SLOT_MAX:
        return "B", slot_id - TRAY_B_SLOT_MIN
    raise ValueError(f"仓位编号须在 1–32 之间，当前为 {slot_id}")


def calc_slot_coord(slot_id: int) -> TraySlotCoord:
    """
    根据仓位编号计算 XYZ。
    4×4 矩阵按行优先：第 1 行 col=0..3，第 2 行 col=0..3 …
    """
    part, local_index = _tray_part_and_local_index(slot_id)
    row = local_index // GRID_COLS
    col = local_index % GRID_COLS

    if part == "A":
        ox, oy, oz = TRAY_A_ORIGIN_X, TRAY_A_ORIGIN_Y, TRAY_A_ORIGIN_Z
    else:
        ox, oy, oz = TRAY_B_ORIGIN_X, TRAY_B_ORIGIN_Y, TRAY_B_ORIGIN_Z

    x = ox + col * SLOT_SPACING_X
    y = oy + row * SLOT_SPACING_Y
    z = oz

    return TraySlotCoord(
        slot_id=slot_id,
        tray_part=part,
        row=row,
        col=col,
        x=x,
        y=y,
        z=z,
    )
