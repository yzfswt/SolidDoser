"""清洁工位动作上下文。"""
from __future__ import annotations

from UIInteraction.ParameterManagement.CleaningStationModel import CleaningStationState
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage


class CleaningStationContext:
    def __init__(self, param_storage: ParameterStorage) -> None:
        self._param_storage = param_storage
        self.motion_cancel_requested = False

    @property
    def station(self) -> CleaningStationState:
        return self._param_storage.cleaning_station
