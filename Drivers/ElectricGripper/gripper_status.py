"""PGC 电爪状态模型。"""
from __future__ import annotations

from dataclasses import dataclass

HOME_STATUS_LABELS = {
    0: "未初始化",
    1: "初始化成功",
    2: "初始化中",
}

RUN_STATUS_LABELS = {
    0: "运动中",
    1: "到位",
    2: "夹住物体",
    3: "物体掉落",
}


@dataclass
class GripperDeviceStatus:
    homed: bool = False
    homing: bool = False
    moving: bool = False
    home_status: int = 0
    run_status: int = 0
    position_mm: float = 0.0

    def home_label(self) -> str:
        return HOME_STATUS_LABELS.get(self.home_status, f"未知({self.home_status})")

    def run_label(self) -> str:
        return RUN_STATUS_LABELS.get(self.run_status, f"未知({self.run_status})")

    def summary(self) -> str:
        home = self.home_label()
        run = self.run_label()
        return f"初始化：{home} | 运行：{run} | 位置 {self.position_mm:g} mm"
