"""第五轴状态模型。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Axis5DeviceStatus:
    servo_enabled: bool = False
    homed: bool = False
    moving: bool = False
    alarm: bool = False
    position_mm: float = 0.0
    target_mm: float = 0.0

    def summary(self) -> str:
        power = "已使能" if self.servo_enabled else "未使能"
        home = "已回零" if self.homed else "未回零"
        run = "运动中" if self.moving else "静止"
        alarm = "有报警" if self.alarm else "无报警"
        return f"{power} | {home} | {run} | 位置 {self.position_mm:g} mm | {alarm}"
