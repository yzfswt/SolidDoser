"""枪头架几何与仓位编号（SolidDoser 项目）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

# 枪头架 A：仓位 1–28，原点 (200, 200, 200)
RACK_A_ORIGIN_X = 200.0
RACK_A_ORIGIN_Y = 200.0
RACK_A_ORIGIN_Z = 200.0

# 枪头架 B：仓位 29–56，原点 (400, 400, 400)
RACK_B_ORIGIN_X = 400.0
RACK_B_ORIGIN_Y = 400.0
RACK_B_ORIGIN_Z = 400.0

# 相邻枪头间距（mm）
TIP_SPACING_X = 10.0
TIP_SPACING_Y = 10.0

# X 方向 4 个，Y 方向 7 个
GRID_COLS = 4
GRID_ROWS = 7
TIPS_PER_RACK = GRID_COLS * GRID_ROWS  # 28
TOTAL_TIPS = TIPS_PER_RACK * 2  # 56

RACK_A_TIP_MIN = 1
RACK_A_TIP_MAX = 28
RACK_B_TIP_MIN = 29
RACK_B_TIP_MAX = 56


@dataclass(frozen=True)
class TipRackCoord:
    """单个枪头位的机械坐标。"""

    tip_id: int
    rack_part: str  # "A" or "B"
    row: int  # Y 方向索引 0–6
    col: int  # X 方向索引 0–3
    x: float
    y: float
    z: float


def _rack_part_and_local_index(tip_id: int) -> Tuple[str, int]:
    if RACK_A_TIP_MIN <= tip_id <= RACK_A_TIP_MAX:
        return "A", tip_id - RACK_A_TIP_MIN
    if RACK_B_TIP_MIN <= tip_id <= RACK_B_TIP_MAX:
        return "B", tip_id - RACK_B_TIP_MIN
    raise ValueError(f"枪头位编号须在 1–56 之间，当前为 {tip_id}")


def calc_tip_coord(tip_id: int) -> TipRackCoord:
    """
    根据枪头位编号计算 XYZ。
    4×7 矩阵按行优先：X 为列 (0–3)，Y 为行 (0–6)。
    """
    part, local_index = _rack_part_and_local_index(tip_id)
    row = local_index // GRID_COLS
    col = local_index % GRID_COLS

    if part == "A":
        ox, oy, oz = RACK_A_ORIGIN_X, RACK_A_ORIGIN_Y, RACK_A_ORIGIN_Z
    else:
        ox, oy, oz = RACK_B_ORIGIN_X, RACK_B_ORIGIN_Y, RACK_B_ORIGIN_Z

    x = ox + col * TIP_SPACING_X
    y = oy + row * TIP_SPACING_Y
    z = oz

    return TipRackCoord(
        tip_id=tip_id,
        rack_part=part,
        row=row,
        col=col,
        x=x,
        y=y,
        z=z,
    )
