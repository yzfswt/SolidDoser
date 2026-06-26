"""MCEA 电缸状态模型。"""
from __future__ import annotations

from dataclasses import dataclass


STROKE_STATUS_LABELS = {
    0: "未标定",
    1: "已标定",
    2: "标定中",
}

HOME_STATUS_LABELS = {
    0: "未回零",
    1: "已回零",
    2: "回零中",
}

RUN_STATUS_LABELS = {
    0: "运动中",
    1: "到位",
    2: "堵转",
}


@dataclass
class PgcDeviceStatus:
    enabled: bool = False
    stroke_initialized: bool = False
    legacy_status: int = 0
    homed: bool = False
    homing: bool = False
    moving: bool = False
    alarm: bool = False
    alarm_code: int = 0
    home_status: int = 0
    run_status: int = 0
    position_mm: float = 0.0
    status_word: int = 0

    def stroke_label(self) -> str:
        return STROKE_STATUS_LABELS.get(self.legacy_status, f"未知({self.legacy_status})")

    def home_label(self) -> str:
        return HOME_STATUS_LABELS.get(self.home_status, f"未知({self.home_status})")

    def run_label(self) -> str:
        return RUN_STATUS_LABELS.get(self.run_status, f"未知({self.run_status})")

    def summary(self) -> str:
        enable = "已使能" if self.enabled else "未使能"
        stroke = (
            "行程已标定" if self.stroke_initialized else f"行程：{self.stroke_label()}"
        )
        home = self.home_label()
        run = self.run_label()
        if self.alarm and self.alarm_code:
            alarm = f"有报警 0x{self.alarm_code:04X}"
        elif self.alarm:
            alarm = "有报警"
        else:
            alarm = "无报警"
        return (
            f"{enable} | {stroke} | 回零：{home} | 运行：{run} | "
            f"位置 {self.position_mm:g} mm | {alarm}"
        )
