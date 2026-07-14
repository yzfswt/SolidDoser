"""基恩士扫码枪调试上下文。"""
from __future__ import annotations

from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ParameterManagement.ScannerModel import ScannerState


class ScannerContext:
    def __init__(self, param_storage: ParameterStorage) -> None:
        self._param_storage = param_storage

    @property
    def scanner(self) -> ScannerState:
        return self._param_storage.scanner
