"""SolidDoser 主运动调试上下文。"""
from __future__ import annotations

from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ParameterManagement.SolidDoserMotionModel import SolidDoserMotionState


class SolidDoserMotionContext:
    def __init__(self, param_storage: ParameterStorage) -> None:
        self._param_storage = param_storage

    @property
    def motion(self) -> SolidDoserMotionState:
        return self._param_storage.solid_doser_motion
