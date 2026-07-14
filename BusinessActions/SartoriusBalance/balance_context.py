"""赛多利斯天平调试上下文。"""
from __future__ import annotations

from UIInteraction.ParameterManagement.BalanceModel import BalanceState
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage


class BalanceContext:
    def __init__(self, param_storage: ParameterStorage) -> None:
        self._param_storage = param_storage

    @property
    def balance(self) -> BalanceState:
        return self._param_storage.balance
