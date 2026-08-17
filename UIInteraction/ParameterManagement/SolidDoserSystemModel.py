"""SolidDoser 系统运行状态（自动流程状态机）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class SystemRunState(Enum):
    """系统级运行状态；忙碌态互斥，结束后回到 IDLE。"""

    IDLE = "空闲中"
    ENABLING = "使能中"
    HOMING = "回基准点中"
    GOING_ORIGIN = "回原点中"
    INITIALIZING = "初始化中"
    FEEDING_BOTTLE = "试剂瓶进料中"
    DOSING = "加样中"
    DISCHARGING_BOTTLE = "试剂瓶出料中"


@dataclass
class SolidDoserSystemState:
    run_state: SystemRunState = SystemRunState.IDLE
    last_action: str = ""
    last_message: str = ""
    last_success: bool = True
    progress_current: int = 0
    progress_total: int = 0
    progress_detail: str = ""
    abort_requested: bool = False
    # 常用系统标识位（由系统动作结束后根据轴状态刷新）
    enabled_ok: bool = False  # 已使能（全部电机）
    datum_ok: bool = False  # 已回基准点（定位相关轴）
    origin_ok: bool = False  # 已回原点（定位相关轴在命名原点）
    materials_ok: bool = False  # 已初始化（8 工位物料表完整有效）
    # 初始化结果：工位 0～7 → 物料条码；失败或作废时清空
    station_materials: Dict[int, str] = field(default_factory=dict)
    # 加样输入（自动页写入，加样动作读取）
    dose_material_id: str = ""
    dose_weight_g: float = 0.0
    # 主系统试剂瓶进料握手（UDP）；进料中保存 request_id 供 DONE 校验
    bottle_feed_request_id: str = ""
    # 本机发起的出料握手
    bottle_discharge_request_id: str = ""
    bottle_discharge_peer_done: bool = False

    @property
    def is_busy(self) -> bool:
        return self.run_state != SystemRunState.IDLE

    @property
    def state_label(self) -> str:
        return self.run_state.value

    def set_progress(self, current: int, total: int, detail: str = "") -> None:
        self.progress_current = max(0, current)
        self.progress_total = max(0, total)
        self.progress_detail = detail

    def clear_progress(self) -> None:
        self.progress_current = 0
        self.progress_total = 0
        self.progress_detail = ""

    def clear_materials(self) -> None:
        """作废物料表。"""
        self.station_materials = {}
        self.materials_ok = False

    def find_station_by_material(self, material_id: str) -> int | None:
        """按条码字符串查找工位；未找到返回 None。"""
        needle = (material_id or "").strip()
        if not needle:
            return None
        for station, code in sorted(self.station_materials.items()):
            if (code or "").strip() == needle:
                return int(station)
        return None

    def flags_summary(self) -> str:
        return " · ".join(
            [
                "已使能" if self.enabled_ok else "未使能",
                "已回基准点" if self.datum_ok else "未回基准点",
                "已回原点" if self.origin_ok else "未回原点",
                "已初始化" if self.materials_ok else "未初始化",
            ]
        )

    def overview_summary(self) -> str:
        parts = [f"状态:{self.state_label}", self.flags_summary()]
        if self.progress_total > 0:
            parts.append(
                f"进度:{self.progress_current}/{self.progress_total}"
            )
        if self.progress_detail:
            parts.append(self.progress_detail)
        if self.last_message:
            parts.append(self.last_message)
        return " · ".join(parts)
