"""SolidDoser 设备调试界面（AM600 运动轴 + 基恩士扫码枪）。"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from BusinessActions.KeyenceScanner.scanner_actions import (
    scanner_clear_result,
    scanner_test_connection,
    scanner_trigger_read,
)
from BusinessActions.KeyenceScanner.scanner_context import ScannerContext
from BusinessActions.SartoriusBalance.balance_actions import (
    balance_clear_result,
    balance_read_weight,
    balance_tare,
    balance_test_connection,
    balance_zero,
)
from BusinessActions.SartoriusBalance.balance_context import BalanceContext
from BusinessActions.SolidDoserMotion.motion_actions import (
    motion_axis_go_home,
    motion_axis_move_abs,
    motion_axis_servo_on,
    motion_axis_stop,
    motion_do_set,
    motion_refresh_all,
)
from BusinessActions.SolidDoserMotion.motion_context import SolidDoserMotionContext
from Drivers.KeyenceScanner import scanner_config as scanner_cfg
from Drivers.SartoriusBalance import balance_config as balance_cfg
from Drivers.SerialServer import dw_rs20tm1_config as serial_cfg
from Drivers.SolidDoserMotion import motion_config as motion_cfg
from Drivers.SolidDoserMotion.motion_config import AxisMap
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

ActionFn = Callable[[SolidDoserMotionContext], Tuple[bool, str]]
ScannerActionFn = Callable[[ScannerContext], Tuple[bool, str]]
BalanceActionFn = Callable[[BalanceContext], Tuple[bool, str]]

_STYLESHEET = """
SolidDoserMotionDebugTabWidget {
    background: #f8fafc;
}
QLabel#PageTitle {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
}
QLabel#PageHint {
    font-size: 12px;
    color: #64748b;
}
QLabel#StatusBar {
    font-size: 12px;
    color: #334155;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
}
QLabel#LogLine {
    font-size: 12px;
    color: #475569;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 12px;
}
QFrame#AxisPanel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QLabel#ColHeader {
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    padding: 4px 0;
}
QLabel#AxisName {
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
}
QLabel#AxisStatus {
    font-size: 11px;
    color: #475569;
}
QLineEdit {
    font-size: 12px;
    padding: 4px 8px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
    min-height: 28px;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
}
QPushButton {
    font-size: 12px;
    padding: 4px 10px;
    min-height: 28px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
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
QPushButton#PrimaryBtn {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#PrimaryBtn:hover {
    background: #1d4ed8;
}
QPushButton#DangerBtn {
    background: #fef2f2;
    border-color: #fecaca;
    color: #b91c1c;
}
QPushButton#DangerBtn:hover {
    background: #fee2e2;
}
"""


class _MotionActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(self, fn: ActionFn, ctx: SolidDoserMotionContext, action_name: str):
        super().__init__()
        self._fn = fn
        self._ctx = ctx
        self._action_name = action_name

    def run(self) -> None:
        try:
            ok, msg = self._fn(self._ctx)
            self.finished.emit(ok, msg, self._action_name)
        except Exception as e:
            self.finished.emit(False, str(e), self._action_name)


class _AxisActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(
        self,
        fn: Callable[[SolidDoserMotionContext, str], Tuple[bool, str]],
        ctx: SolidDoserMotionContext,
        axis_key: str,
        action_name: str,
    ):
        super().__init__()
        self._fn = fn
        self._ctx = ctx
        self._axis_key = axis_key
        self._action_name = action_name

    def run(self) -> None:
        try:
            ok, msg = self._fn(self._ctx, self._axis_key)
            self.finished.emit(ok, msg, self._action_name)
        except Exception as e:
            self.finished.emit(False, str(e), self._action_name)


class _ScannerActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(self, fn: ScannerActionFn, ctx: ScannerContext, action_name: str):
        super().__init__()
        self._fn = fn
        self._ctx = ctx
        self._action_name = action_name

    def run(self) -> None:
        try:
            ok, msg = self._fn(self._ctx)
            self.finished.emit(ok, msg, self._action_name)
        except Exception as e:
            self.finished.emit(False, str(e), self._action_name)


class _BalanceActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(self, fn: BalanceActionFn, ctx: BalanceContext, action_name: str):
        super().__init__()
        self._fn = fn
        self._ctx = ctx
        self._action_name = action_name

    def run(self) -> None:
        try:
            ok, msg = self._fn(self._ctx)
            self.finished.emit(ok, msg, self._action_name)
        except Exception as e:
            self.finished.emit(False, str(e), self._action_name)


class SolidDoserMotionDebugTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SolidDoserMotionDebugTabWidget")
        self.setStyleSheet(_STYLESHEET)
        self._ctx: Optional[SolidDoserMotionContext] = None
        self._scanner_ctx: Optional[ScannerContext] = None
        self._balance_ctx: Optional[BalanceContext] = None
        self._thread: Optional[QThread] = None
        self._buttons: List[QPushButton] = []
        self._status_label: Optional[QLabel] = None
        self._log_label: Optional[QLabel] = None
        self._axis_status_labels: Dict[str, QLabel] = {}
        self._do_status_labels: Dict[str, QLabel] = {}
        self._do_on_buttons: Dict[str, QPushButton] = {}
        self._do_off_buttons: Dict[str, QPushButton] = {}
        self._target_inputs: Dict[str, QLineEdit] = {}
        self._velocity_inputs: Dict[str, QLineEdit] = {}
        self._scanner_status_label: Optional[QLabel] = None
        self._scanner_result_label: Optional[QLabel] = None
        self._balance_status_label: Optional[QLabel] = None
        self._balance_result_label: Optional[QLabel] = None
        self._build_ui()

    def bind_parameter_storage(self, param_storage: ParameterStorage) -> None:
        self._ctx = SolidDoserMotionContext(param_storage)
        self._scanner_ctx = ScannerContext(param_storage)
        self._balance_ctx = BalanceContext(param_storage)
        self._load_motion_params_from_state()
        self._refresh_status()
        self._refresh_scanner_status()
        self._refresh_balance_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("设备调试")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        hint = QLabel(
            f"AM600-CPU1608TN · Modbus TCP {motion_cfg.PLC_HOST}:{motion_cfg.PLC_PORT} · "
            "写入 D 目标/速度，M 脉冲触发 PLC 运动"
        )
        hint.setObjectName("PageHint")
        root.addWidget(hint)

        top_row = QHBoxLayout()
        self._status_label = QLabel("状态：未绑定")
        self._status_label.setObjectName("StatusBar")
        self._status_label.setWordWrap(True)
        top_row.addWidget(self._status_label, 1)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setObjectName("PrimaryBtn")
        btn_refresh.setFixedWidth(72)
        btn_refresh.clicked.connect(
            lambda: self._run_global_action(motion_refresh_all, "刷新全部状态")
        )
        self._buttons.append(btn_refresh)
        top_row.addWidget(btn_refresh)
        root.addLayout(top_row)

        panel = QFrame()
        panel.setObjectName("AxisPanel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        headers = ["电机", "目标", "速度", "状态", "操作"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("ColHeader")
            grid.addWidget(label, 0, col)

        for row, axis in enumerate(motion_cfg.AXES, start=1):
            self._add_axis_row(grid, row, axis)

        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 4)
        grid.setColumnStretch(4, 5)
        root.addWidget(panel)

        do_panel = QFrame()
        do_panel.setObjectName("AxisPanel")
        do_grid = QGridLayout(do_panel)
        do_grid.setContentsMargins(12, 10, 12, 10)
        do_grid.setHorizontalSpacing(10)
        do_grid.setVerticalSpacing(6)
        do_headers = ["设备", "输出点", "状态", "操作"]
        for col, text in enumerate(do_headers):
            label = QLabel(text)
            label.setObjectName("ColHeader")
            do_grid.addWidget(label, 0, col)
        for row, do_item in enumerate(motion_cfg.DO_OUTPUTS, start=1):
            self._add_do_row(do_grid, row, do_item)
        do_grid.setColumnStretch(0, 2)
        do_grid.setColumnStretch(1, 1)
        do_grid.setColumnStretch(2, 2)
        do_grid.setColumnStretch(3, 3)
        root.addWidget(do_panel)

        scanner_title = QLabel("扫码枪")
        scanner_title.setObjectName("PageTitle")
        root.addWidget(scanner_title)

        scanner_hint = QLabel(
            f"{scanner_cfg.SCANNER_MODEL} · TCP {scanner_cfg.SCANNER_HOST}:"
            f"{scanner_cfg.SCANNER_PORT} · 发送 LON 触发单次读码"
        )
        scanner_hint.setObjectName("PageHint")
        root.addWidget(scanner_hint)

        scanner_panel = QFrame()
        scanner_panel.setObjectName("AxisPanel")
        scanner_layout = QVBoxLayout(scanner_panel)
        scanner_layout.setContentsMargins(12, 10, 12, 10)
        scanner_layout.setSpacing(8)

        scanner_top = QHBoxLayout()
        self._scanner_status_label = QLabel("状态：未测试")
        self._scanner_status_label.setObjectName("StatusBar")
        self._scanner_status_label.setWordWrap(True)
        scanner_top.addWidget(self._scanner_status_label, 1)

        btn_scanner_test = QPushButton("连接测试")
        btn_scanner_test.clicked.connect(
            lambda: self._run_scanner_action(scanner_test_connection, "扫码枪连接测试")
        )
        btn_scanner_trigger = QPushButton("触发扫码")
        btn_scanner_trigger.setObjectName("PrimaryBtn")
        btn_scanner_trigger.clicked.connect(
            lambda: self._run_scanner_action(scanner_trigger_read, "触发扫码")
        )
        btn_scanner_clear = QPushButton("清空")
        btn_scanner_clear.clicked.connect(
            lambda: self._run_scanner_action(scanner_clear_result, "清空读码结果")
        )
        self._buttons.extend([btn_scanner_test, btn_scanner_trigger, btn_scanner_clear])
        scanner_top.addWidget(btn_scanner_test)
        scanner_top.addWidget(btn_scanner_trigger)
        scanner_top.addWidget(btn_scanner_clear)
        scanner_layout.addLayout(scanner_top)

        self._scanner_result_label = QLabel("读码结果：—")
        self._scanner_result_label.setObjectName("LogLine")
        self._scanner_result_label.setWordWrap(True)
        self._scanner_result_label.setMinimumHeight(40)
        scanner_layout.addWidget(self._scanner_result_label)
        root.addWidget(scanner_panel)

        balance_title = QLabel("天平")
        balance_title.setObjectName("PageTitle")
        root.addWidget(balance_title)

        balance_hint = QLabel(
            f"{balance_cfg.BALANCE_MODEL} · {serial_cfg.SERIAL_SERVER_MODEL} "
            f"TCP {serial_cfg.SERIAL_SERVER_HOST}:{serial_cfg.SERIAL_SERVER_PORT} "
            f"RS232 透传 · SBI（Esc P/T/V）· 串口侧建议 {serial_cfg.SERIAL_PARAMS_HINT}"
        )
        balance_hint.setObjectName("PageHint")
        balance_hint.setWordWrap(True)
        root.addWidget(balance_hint)

        balance_panel = QFrame()
        balance_panel.setObjectName("AxisPanel")
        balance_layout = QVBoxLayout(balance_panel)
        balance_layout.setContentsMargins(12, 10, 12, 10)
        balance_layout.setSpacing(8)

        balance_top = QHBoxLayout()
        self._balance_status_label = QLabel("状态：未测试")
        self._balance_status_label.setObjectName("StatusBar")
        self._balance_status_label.setWordWrap(True)
        balance_top.addWidget(self._balance_status_label, 1)

        btn_balance_test = QPushButton("连接测试")
        btn_balance_test.clicked.connect(
            lambda: self._run_balance_action(balance_test_connection, "天平连接测试")
        )
        btn_balance_read = QPushButton("读重量")
        btn_balance_read.setObjectName("PrimaryBtn")
        btn_balance_read.clicked.connect(
            lambda: self._run_balance_action(balance_read_weight, "读取重量")
        )
        btn_balance_tare = QPushButton("去皮")
        btn_balance_tare.clicked.connect(
            lambda: self._run_balance_action(balance_tare, "去皮")
        )
        btn_balance_zero = QPushButton("清零")
        btn_balance_zero.clicked.connect(
            lambda: self._run_balance_action(balance_zero, "清零")
        )
        btn_balance_clear = QPushButton("清空")
        btn_balance_clear.clicked.connect(
            lambda: self._run_balance_action(balance_clear_result, "清空读重结果")
        )
        self._buttons.extend(
            [
                btn_balance_test,
                btn_balance_read,
                btn_balance_tare,
                btn_balance_zero,
                btn_balance_clear,
            ]
        )
        balance_top.addWidget(btn_balance_test)
        balance_top.addWidget(btn_balance_read)
        balance_top.addWidget(btn_balance_tare)
        balance_top.addWidget(btn_balance_zero)
        balance_top.addWidget(btn_balance_clear)
        balance_layout.addLayout(balance_top)

        self._balance_result_label = QLabel("读重结果：—")
        self._balance_result_label.setObjectName("LogLine")
        self._balance_result_label.setWordWrap(True)
        self._balance_result_label.setMinimumHeight(40)
        balance_layout.addWidget(self._balance_result_label)
        root.addWidget(balance_panel)

        self._log_label = QLabel("日志：—")
        self._log_label.setObjectName("LogLine")
        self._log_label.setWordWrap(True)
        root.addWidget(self._log_label)

    def _add_axis_row(self, grid: QGridLayout, row: int, axis: AxisMap) -> None:
        name = QLabel(axis.label)
        name.setObjectName("AxisName")
        grid.addWidget(name, row, 0)

        pos_validator = QDoubleValidator(axis.pos_min, axis.pos_max, 3)
        pos_validator.setNotation(QDoubleValidator.StandardNotation)
        vel_validator = QDoubleValidator(0.1, 5000.0, 2)
        vel_validator.setNotation(QDoubleValidator.StandardNotation)

        target_input = QLineEdit()
        target_input.setPlaceholderText(f"0 {axis.unit}")
        target_input.setValidator(pos_validator)
        target_input.editingFinished.connect(lambda k=axis.key: self._sync_axis_params(k))
        self._target_inputs[axis.key] = target_input
        grid.addWidget(target_input, row, 1)

        vel_input = QLineEdit()
        vel_input.setPlaceholderText(f"{axis.vel_default:g}")
        vel_input.setValidator(vel_validator)
        vel_input.editingFinished.connect(lambda k=axis.key: self._sync_axis_params(k))
        self._velocity_inputs[axis.key] = vel_input
        grid.addWidget(vel_input, row, 2)

        status_label = QLabel("未读取")
        status_label.setObjectName("AxisStatus")
        status_label.setWordWrap(True)
        self._axis_status_labels[axis.key] = status_label
        grid.addWidget(status_label, row, 3)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_host = QWidget()
        btn_host.setLayout(btn_row)
        for label, fn, style in (
            ("使能", motion_axis_servo_on, ""),
            ("回零", motion_axis_go_home, ""),
            ("定位", motion_axis_move_abs, ""),
            ("停止", motion_axis_stop, "DangerBtn"),
        ):
            btn = QPushButton(label)
            if style:
                btn.setObjectName(style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(
                lambda _c=False, k=axis.key, f=fn, n=f"{axis.label} {label}": self._run_axis_action(
                    f, k, n
                )
            )
            self._buttons.append(btn)
            btn_row.addWidget(btn)
        grid.addWidget(btn_host, row, 4)

    def _add_do_row(self, grid: QGridLayout, row: int, do_item) -> None:
        name = QLabel(do_item.label)
        name.setObjectName("AxisName")
        grid.addWidget(name, row, 0)

        q_label = QLabel(do_item.q_name)
        q_label.setObjectName("AxisStatus")
        grid.addWidget(q_label, row, 1)

        status_label = QLabel("未读取")
        status_label.setObjectName("AxisStatus")
        self._do_status_labels[do_item.key] = status_label
        grid.addWidget(status_label, row, 2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_host = QWidget()
        btn_host.setLayout(btn_row)

        btn_off = QPushButton("关闭")
        btn_off.clicked.connect(
            lambda _c=False, k=do_item.key, n=f"{do_item.label} 关闭": self._run_do_action(
                k, False, n
            )
        )
        btn_on = QPushButton("开启")
        btn_on.clicked.connect(
            lambda _c=False, k=do_item.key, n=f"{do_item.label} 开启": self._run_do_action(
                k, True, n
            )
        )
        self._do_off_buttons[do_item.key] = btn_off
        self._do_on_buttons[do_item.key] = btn_on
        self._buttons.extend([btn_off, btn_on])
        btn_row.addWidget(btn_off)
        btn_row.addWidget(btn_on)
        grid.addWidget(btn_host, row, 3)

    def _compact_status(self, axis_key: str) -> str:
        if self._ctx is None:
            return "未读取"
        st = self._ctx.motion.axis(axis_key)
        axis = motion_cfg.AXIS_BY_KEY[axis_key]
        flags = []
        flags.append("使能" if st.servo_enabled else "未使能")
        flags.append("已回零" if st.homed else "未回零")
        if st.moving:
            flags.append("运动中")
        if st.alarm:
            flags.append("报警")
        return f"{' · '.join(flags)} · {st.actual_position:g}{axis.unit}"

    def _load_motion_params_from_state(self) -> None:
        if self._ctx is None:
            return
        for axis in motion_cfg.AXES:
            st = self._ctx.motion.axis(axis.key)
            target_input = self._target_inputs.get(axis.key)
            vel_input = self._velocity_inputs.get(axis.key)
            if target_input is not None:
                target_input.setText(f"{st.target_position:g}")
            if vel_input is not None:
                vel_input.setText(f"{st.velocity:g}")

    def _sync_axis_params(self, axis_key: str) -> None:
        if self._ctx is None:
            return
        st = self._ctx.motion.axis(axis_key)
        target_input = self._target_inputs.get(axis_key)
        vel_input = self._velocity_inputs.get(axis_key)
        if target_input is not None and target_input.hasAcceptableInput():
            st.target_position = float(target_input.text())
        if vel_input is not None and vel_input.hasAcceptableInput():
            st.velocity = float(vel_input.text())

    def _sync_all_params(self) -> None:
        for axis in motion_cfg.AXES:
            self._sync_axis_params(axis.key)

    def _refresh_status(self) -> None:
        if self._ctx is None or self._status_label is None:
            return
        motion = self._ctx.motion
        mode = "仿真" if motion.simulation_mode else "联机"
        conn = "已连接" if motion.plc_connected or motion.simulation_mode else "未连接"
        self._status_label.setText(
            f"{conn} · {mode} · 最近：{motion.last_action or '—'}"
        )
        for axis in motion_cfg.AXES:
            label = self._axis_status_labels.get(axis.key)
            if label is not None:
                label.setText(self._compact_status(axis.key))
        self._update_do_controls()

    def _refresh_scanner_status(self) -> None:
        if self._scanner_ctx is None:
            return
        st = self._scanner_ctx.scanner
        if self._scanner_status_label is not None:
            mode = "仿真" if st.simulation_mode else "联机"
            conn = "已连接" if st.connected or st.simulation_mode else "未连接"
            self._scanner_status_label.setText(
                f"状态：{conn} · {mode} · 最近：{st.last_action or '—'}"
            )
        if self._scanner_result_label is not None:
            barcode = st.last_barcode or "—"
            history = " / ".join(st.read_history[:5]) if st.read_history else "—"
            self._scanner_result_label.setText(f"读码结果：{barcode}\n历史：{history}")

    def _refresh_balance_status(self) -> None:
        if self._balance_ctx is None:
            return
        st = self._balance_ctx.balance
        if self._balance_status_label is not None:
            mode = "仿真" if st.simulation_mode else "联机"
            conn = "已连接" if st.connected or st.simulation_mode else "未连接"
            self._balance_status_label.setText(
                f"状态：{conn} · {mode} · 最近：{st.last_action or '—'}"
            )
        if self._balance_result_label is not None:
            weight = st.last_weight_display or "—"
            raw = st.last_raw or "—"
            history = " / ".join(st.read_history[:5]) if st.read_history else "—"
            self._balance_result_label.setText(
                f"读重结果：{weight}\n原始：{raw}\n历史：{history}"
            )

    def _update_do_controls(self) -> None:
        if self._ctx is None:
            return
        for do_item in motion_cfg.DO_OUTPUTS:
            on = self._ctx.motion.do_states.get(do_item.key, False)
            status_label = self._do_status_labels.get(do_item.key)
            if status_label is not None:
                status_label.setText("开启" if on else "关闭")
            btn_on = self._do_on_buttons.get(do_item.key)
            btn_off = self._do_off_buttons.get(do_item.key)
            if btn_on is not None:
                btn_on.setObjectName("PrimaryBtn" if on else "")
                btn_on.setStyleSheet(_STYLESHEET)
            if btn_off is not None:
                btn_off.setObjectName("DangerBtn" if not on else "")
                btn_off.setStyleSheet(_STYLESHEET)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)

    def _append_log(self, ok: bool, msg: str, action_name: str) -> None:
        if self._log_label is None:
            return
        prefix = "成功" if ok else "失败"
        self._log_label.setText(f"日志：{prefix} · {action_name} · {msg}")

    def _on_action_finished(self, ok: bool, msg: str, action_name: str) -> None:
        self._thread = None
        self._set_buttons_enabled(True)
        self._refresh_status()
        self._refresh_scanner_status()
        self._refresh_balance_status()
        self._append_log(ok, msg, action_name)

    def _run_global_action(self, fn: ActionFn, action_name: str) -> None:
        if self._ctx is None or self._thread is not None:
            return
        self._sync_all_params()
        self._set_buttons_enabled(False)
        self._thread = _MotionActionThread(fn, self._ctx, action_name)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()

    def _run_axis_action(
        self,
        fn: Callable[[SolidDoserMotionContext, str], Tuple[bool, str]],
        axis_key: str,
        action_name: str,
    ) -> None:
        if self._ctx is None or self._thread is not None:
            return
        self._sync_axis_params(axis_key)
        self._set_buttons_enabled(False)
        self._thread = _AxisActionThread(fn, self._ctx, axis_key, action_name)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()

    def _run_do_action(self, do_key: str, on: bool, action_name: str) -> None:
        if self._ctx is None or self._thread is not None:
            return
        self._set_buttons_enabled(False)
        self._thread = _MotionActionThread(
            lambda ctx: motion_do_set(ctx, do_key, on),
            self._ctx,
            action_name,
        )
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()

    def _run_scanner_action(self, fn: ScannerActionFn, action_name: str) -> None:
        if self._scanner_ctx is None or self._thread is not None:
            return
        self._set_buttons_enabled(False)
        self._thread = _ScannerActionThread(fn, self._scanner_ctx, action_name)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()

    def _run_balance_action(self, fn: BalanceActionFn, action_name: str) -> None:
        if self._balance_ctx is None or self._thread is not None:
            return
        self._set_buttons_enabled(False)
        self._thread = _BalanceActionThread(fn, self._balance_ctx, action_name)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()
