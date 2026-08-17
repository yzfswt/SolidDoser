"""SolidDoser 自动运行界面（系统状态机入口）。"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from BusinessActions.SolidDoserSystem.system_actions import (
    system_request_abort,
    system_run_bottle_discharge,
    system_run_dose,
    system_run_go_datum,
    system_run_go_origin,
    system_run_initialize,
    system_run_servo_on_all,
)
from BusinessActions.SolidDoserSystem.system_context import SolidDoserSystemContext
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

ActionFn = Callable[[SolidDoserSystemContext], Tuple[bool, str]]

# 与调试页轴按钮一致的高度/字号；宽度兼顾「试剂瓶出料」
_AUTO_BTN_MIN_WIDTH = 96
_AUTO_BTN_SPACING = 4

_STYLESHEET = """
SolidDoserAutoTabWidget {
    background: #f1f5f9;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QLabel#Title {
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
}
QLabel#Hint {
    font-size: 11px;
    color: #64748b;
}
QLabel#StateValue {
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
}
QLabel#LogValue {
    font-size: 12px;
    color: #475569;
}
QLabel#Field {
    font-size: 12px;
    color: #64748b;
}
QLineEdit {
    font-size: 12px;
    padding: 2px 6px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
    min-height: 30px;
    max-height: 30px;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
}
QLineEdit:disabled {
    background: #f8fafc;
    color: #94a3b8;
}
QPushButton {
    font-size: 12px;
    padding: 2px 10px;
    min-height: 30px;
    max-height: 30px;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    background: #ffffff;
    color: #334155;
}
QPushButton:hover {
    background: #f1f5f9;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background: #e2e8f0;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #f8fafc;
}
QPushButton#DangerBtn {
    border-color: #fca5a5;
    color: #b91c1c;
    background: #fff1f2;
}
QPushButton#DangerBtn:hover {
    background: #fee2e2;
    border-color: #f87171;
}
QPushButton#DangerBtn:disabled {
    color: #fca5a5;
    background: #fff1f2;
    border-color: #fecdd3;
}
"""


class _SystemActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(self, fn: ActionFn, ctx: SolidDoserSystemContext, action_name: str):
        super().__init__()
        self._fn = fn
        self._ctx = ctx
        self._action_name = action_name

    def run(self) -> None:
        try:
            ok, msg = self._fn(self._ctx)
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, str(exc)
        self.finished.emit(ok, msg, self._action_name)


class SolidDoserAutoTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SolidDoserAutoTabWidget")
        self.setStyleSheet(_STYLESHEET)
        self._ctx: Optional[SolidDoserSystemContext] = None
        self._thread: Optional[_SystemActionThread] = None
        self._action_buttons: Dict[str, QPushButton] = {}
        self._buttons: List[QPushButton] = []
        self._state_label: Optional[QLabel] = None
        self._flags_label: Optional[QLabel] = None
        self._progress_label: Optional[QLabel] = None
        self._log_label: Optional[QLabel] = None
        self._materials_label: Optional[QLabel] = None
        self._material_input: Optional[QLineEdit] = None
        self._dose_weight_input: Optional[QLineEdit] = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._refresh_status)
        self._build_ui()

    def bind_parameter_storage(self, param_storage: ParameterStorage) -> None:
        self._ctx = SolidDoserSystemContext(param_storage)
        if self._material_input is not None:
            self._material_input.setText(param_storage.solid_doser_system.dose_material_id)
        if self._dose_weight_input is not None:
            w = param_storage.solid_doser_system.dose_weight_g
            self._dose_weight_input.setText("" if w <= 0 else f"{w:g}")
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("自动运行")
        title.setObjectName("Title")
        root.addWidget(title)

        hint = QLabel("系统状态机入口：空闲时可启动流程；忙碌时仅可停止。")
        hint.setObjectName("Hint")
        root.addWidget(hint)

        status_card = QFrame()
        status_card.setObjectName("Card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(6)
        self._state_label = QLabel("状态：空闲中")
        self._state_label.setObjectName("StateValue")
        self._flags_label = QLabel(
            "标识：未使能 · 未回基准点 · 未回原点 · 未初始化"
        )
        self._flags_label.setObjectName("LogValue")
        self._progress_label = QLabel("进度：—")
        self._progress_label.setObjectName("LogValue")
        self._log_label = QLabel("日志：—")
        self._log_label.setObjectName("LogValue")
        self._materials_label = QLabel("物料表：尚未初始化")
        self._materials_label.setObjectName("LogValue")
        self._materials_label.setWordWrap(True)
        status_layout.addWidget(self._state_label)
        status_layout.addWidget(self._flags_label)
        status_layout.addWidget(self._progress_label)
        status_layout.addWidget(self._log_label)
        status_layout.addWidget(self._materials_label)
        root.addWidget(status_card)

        dose_card = QFrame()
        dose_card.setObjectName("Card")
        dose_layout = QHBoxLayout(dose_card)
        dose_layout.setContentsMargins(12, 12, 12, 12)
        dose_layout.setSpacing(12)

        mat_lab = QLabel("物料编号")
        mat_lab.setObjectName("Field")
        self._material_input = QLineEdit()
        self._material_input.setPlaceholderText("条码字符串")
        self._material_input.setMinimumWidth(160)
        self._material_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dose_layout.addWidget(mat_lab)
        dose_layout.addWidget(self._material_input, 2)

        w_lab = QLabel("加样重量(g)")
        w_lab.setObjectName("Field")
        self._dose_weight_input = QLineEdit()
        self._dose_weight_input.setPlaceholderText("净重")
        self._dose_weight_input.setMinimumWidth(100)
        weight_validator = QDoubleValidator(0.001, 100000.0, 4)
        weight_validator.setNotation(QDoubleValidator.StandardNotation)
        self._dose_weight_input.setValidator(weight_validator)
        dose_layout.addWidget(w_lab)
        dose_layout.addWidget(self._dose_weight_input, 1)
        dose_layout.addStretch(1)
        root.addWidget(dose_card)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(_AUTO_BTN_SPACING)

        actions = (
            ("使能", system_run_servo_on_all),
            ("回基准点", system_run_go_datum),
            ("回原点", system_run_go_origin),
            ("物料初始化", system_run_initialize),
            ("加样", system_run_dose),
            ("试剂瓶出料", system_run_bottle_discharge),
        )
        for text, fn in actions:
            btn = QPushButton(text)
            btn.setMinimumWidth(_AUTO_BTN_MIN_WIDTH)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(
                lambda _c=False, f=fn, n=text: self._run_action(f, n)
            )
            self._action_buttons[text] = btn
            self._buttons.append(btn)
            card_layout.addWidget(btn, 1)

        btn_abort = QPushButton("停止")
        btn_abort.setObjectName("DangerBtn")
        btn_abort.setMinimumWidth(_AUTO_BTN_MIN_WIDTH)
        btn_abort.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_abort.clicked.connect(self._on_abort)
        self._action_buttons["停止"] = btn_abort
        self._buttons.append(btn_abort)
        card_layout.addWidget(btn_abort, 1)

        root.addWidget(card)
        root.addStretch(1)
        self._set_controls_for_idle(True)

    def _refresh_status(self) -> None:
        if self._ctx is None:
            return
        st = self._ctx.system
        if self._state_label is not None:
            self._state_label.setText(f"状态：{st.state_label}")
        if self._flags_label is not None:
            self._flags_label.setText(f"标识：{st.flags_summary()}")
        if self._progress_label is not None:
            if st.progress_total > 0:
                detail = f" · {st.progress_detail}" if st.progress_detail else ""
                self._progress_label.setText(
                    f"进度：{st.progress_current}/{st.progress_total}{detail}"
                )
            else:
                self._progress_label.setText("进度：—")
        if self._log_label is not None:
            prefix = "成功" if st.last_success else "失败"
            msg = st.last_message or "—"
            self._log_label.setText(f"日志：{prefix} · {msg}")
        if self._materials_label is not None:
            if st.materials_ok and st.station_materials:
                mapped = "；".join(
                    f"{s}:{(c or '—')}"
                    for s, c in sorted(st.station_materials.items())
                )
                self._materials_label.setText(f"物料表：{mapped}")
            else:
                self._materials_label.setText("物料表：尚未初始化")

    def _set_controls_for_idle(self, idle: bool) -> None:
        for name, btn in self._action_buttons.items():
            if name == "停止":
                btn.setEnabled(not idle)
            else:
                btn.setEnabled(idle)
        if self._material_input is not None:
            self._material_input.setEnabled(idle)
        if self._dose_weight_input is not None:
            self._dose_weight_input.setEnabled(idle)

    def _sync_dose_params(self) -> None:
        if self._ctx is None:
            return
        material = (
            self._material_input.text().strip() if self._material_input is not None else ""
        )
        weight_text = (
            self._dose_weight_input.text().strip()
            if self._dose_weight_input is not None
            else ""
        )
        try:
            weight = float(weight_text) if weight_text else 0.0
        except ValueError:
            weight = 0.0
        self._ctx.system.dose_material_id = material
        self._ctx.system.dose_weight_g = weight

    def _run_action(self, fn: ActionFn, action_name: str) -> None:
        if self._ctx is None or self._thread is not None:
            return
        if self._ctx.system.is_busy:
            self._refresh_status()
            return
        self._sync_dose_params()
        self._set_controls_for_idle(False)
        self._thread = _SystemActionThread(fn, self._ctx, action_name)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()
        self._poll_timer.start()
        self._state_label.setText(f"状态：启动{action_name}…")

    def _on_abort(self) -> None:
        if self._ctx is None:
            return
        system_request_abort(self._ctx)
        self._refresh_status()

    def _on_action_finished(self, ok: bool, msg: str, action_name: str) -> None:
        self._thread = None
        self._poll_timer.stop()
        self._set_controls_for_idle(True)
        self._refresh_status()
        if self._log_label is not None:
            prefix = "成功" if ok else "失败"
            self._log_label.setText(f"日志：{prefix} · {action_name} · {msg}")
