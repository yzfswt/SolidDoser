"""机器人动作执行上下文。"""
from __future__ import annotations

from dataclasses import dataclass

from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ParameterManagement.RobotModel import RobotState


@dataclass
class RobotContext:
    param_storage: ParameterStorage
    motion_cancel_requested: bool = False

    @property
    def robot(self) -> RobotState:
        return self.param_storage.robot
