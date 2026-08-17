"""SolidDoser 系统运行上下文。"""
from __future__ import annotations

from BusinessActions.KeyenceScanner.scanner_context import ScannerContext
from BusinessActions.SartoriusBalance.balance_context import BalanceContext
from BusinessActions.SolidDoserMotion.motion_context import SolidDoserMotionContext
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ParameterManagement.SolidDoserSystemModel import SolidDoserSystemState


class SolidDoserSystemContext:
    def __init__(self, param_storage: ParameterStorage) -> None:
        self._param_storage = param_storage
        self.motion_ctx = SolidDoserMotionContext(param_storage)
        self.scanner_ctx = ScannerContext(param_storage)
        self.balance_ctx = BalanceContext(param_storage)

    @property
    def param_storage(self) -> ParameterStorage:
        return self._param_storage

    @property
    def system(self) -> SolidDoserSystemState:
        return self._param_storage.solid_doser_system
