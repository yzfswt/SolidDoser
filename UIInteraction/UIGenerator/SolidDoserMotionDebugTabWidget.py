"""SolidDoser 设备调试界面（运动轴 / DO / 扫码枪 / 天平）。"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, Signal
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
    indexing_disc_step_backward,
    indexing_disc_step_forward,
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
from Drivers.SolidDoserMotion.motion_config import AxisMap, DoOutputMap
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

ActionFn = Callable[[SolidDoserMotionContext], Tuple[bool, str]]
ScannerActionFn = Callable[[ScannerContext], Tuple[bool, str]]
BalanceActionFn = Callable[[BalanceContext], Tuple[bool, str]]

_STIR_AXIS_KEY = "stirring"
_INDEXING_AXIS_KEY = motion_cfg.INDEXING_AXIS_KEY
_FIELD_LABEL_WIDTH = 28
_TARGET_INPUT_MIN_WIDTH = 56
_VELOCITY_INPUT_MIN_WIDTH = 52
_AXIS_STATUS_MIN_WIDTH = 120
# 6 列按钮区：等比拉伸填满行宽，各行同列竖直对齐
_AXIS_BTN_COLS = 6
_AXIS_BTN_MIN_WIDTH = 52
_AXIS_BTN_SPACING = 6

_STYLESHEET = """
SolidDoserMotionDebugTabWidget {
    background: #f1f5f9;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QFrame#AxisRow {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #f1f5f9;
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
QLabel#Field {
    font-size: 11px;
    color: #64748b;
}
QLabel#Name {
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
}
QLabel#Status {
    font-size: 11px;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 4px 8px;
}
QLabel#Result {
    font-size: 12px;
    color: #334155;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 6px 8px;
}
QLineEdit {
    font-size: 12px;
    padding: 4px 6px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
    min-height: 28px;
    max-height: 28px;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
}
QPushButton {
    font-size: 12px;
    padding: 4px 12px;
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
    background: #fff1f2;
    border-color: #fecdd3;
    color: #be123c;
}
QPushButton#DangerBtn:hover {
    background: #ffe4e6;
}
QPushButton#AxisBtn {
    padding: 4px 4px;
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


def _make_btn(text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
    btn = QPushButton(text)
    if primary:
        btn.setObjectName("PrimaryBtn")
    elif danger:
        btn.setObjectName("DangerBtn")
    btn.setMinimumWidth(64)
    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return btn


def _make_axis_btn(text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
    """运动轴按钮：同行等比拉伸，各行同列对齐。"""
    btn = _make_btn(text, primary=primary, danger=danger)
    if not primary and not danger:
        btn.setObjectName("AxisBtn")
    btn.setMinimumWidth(_AXIS_BTN_MIN_WIDTH)
    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return btn


def _add_axis_btn_slot(layout: QHBoxLayout, widget: Optional[QWidget]) -> None:
    if widget is None:
        placeholder = QWidget()
        placeholder.setMinimumWidth(_AXIS_BTN_MIN_WIDTH)
        placeholder.setFixedHeight(30)
        placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(placeholder, 1)
        return
    widget.setMinimumWidth(_AXIS_BTN_MIN_WIDTH)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(widget, 1)


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
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("设备调试")
        title.setObjectName("Title")
        header.addWidget(title)
        hint = QLabel(
            f"PLC {motion_cfg.PLC_HOST}:{motion_cfg.PLC_PORT}  ·  "
            f"扫码 {scanner_cfg.SCANNER_HOST}:{scanner_cfg.SCANNER_PORT}  ·  "
            f"天平 {serial_cfg.SERIAL_SERVER_HOST}:{serial_cfg.SERIAL_SERVER_PORT}"
        )
        hint.setObjectName("Hint")
        header.addWidget(hint, 1)
        btn_refresh = _make_btn("刷新", primary=True)
        btn_refresh.setFixedWidth(72)
        btn_refresh.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_refresh.clicked.connect(
            lambda: self._run_global_action(motion_refresh_all, "刷新全部状态")
        )
        self._buttons.append(btn_refresh)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        self._status_label = QLabel("PLC：未绑定")
        self._status_label.setObjectName("Status")
        root.addWidget(self._status_label)

        root.addWidget(self._build_motion_card())
        root.addWidget(self._build_do_card())

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        bottom.addWidget(self._build_scanner_card(), 1)
        bottom.addWidget(self._build_balance_card(), 1)
        root.addLayout(bottom)

        self._log_label = QLabel("日志：—")
        self._log_label.setObjectName("Result")
        root.addWidget(self._log_label)
        root.addStretch(1)

    def _build_motion_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(0)

        head = QLabel("运动轴（AM600）")
        head.setObjectName("Title")
        layout.addWidget(head)

        for axis in motion_cfg.AXES:
            layout.addWidget(self._build_axis_row(axis))
        return card

    def _build_axis_row(self, axis: AxisMap) -> QWidget:
        row = QFrame()
        row.setObjectName("AxisRow")
        row.setMinimumHeight(44)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(6)

        name = QLabel(axis.label)
        name.setObjectName("Name")
        name.setFixedWidth(72)
        layout.addWidget(name)

        is_stir_axis = axis.key == _STIR_AXIS_KEY
        is_indexing_axis = axis.key == _INDEXING_AXIS_KEY

        actions_box = QWidget()
        actions = QHBoxLayout(actions_box)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(_AXIS_BTN_SPACING)

        btn_servo = _make_axis_btn("使能")
        btn_servo.clicked.connect(
            lambda _c=False, k=axis.key: self._run_axis_action(
                motion_axis_servo_on, k, f"{axis.label} 使能"
            )
        )
        self._buttons.append(btn_servo)
        _add_axis_btn_slot(actions, btn_servo)

        if is_stir_axis:
            _add_axis_btn_slot(actions, None)
        else:
            btn_home = _make_axis_btn("回零")
            btn_home.clicked.connect(
                lambda _c=False, k=axis.key: self._run_axis_action(
                    motion_axis_go_home, k, f"{axis.label} 回零"
                )
            )
            self._buttons.append(btn_home)
            _add_axis_btn_slot(actions, btn_home)

        move_label = "启动" if is_stir_axis else "定位"
        btn_move = _make_axis_btn(move_label, primary=True)
        btn_move.clicked.connect(
            lambda _c=False, k=axis.key: self._run_axis_action(
                motion_axis_move_abs, k, f"{axis.label} {move_label}"
            )
        )
        self._buttons.append(btn_move)
        _add_axis_btn_slot(actions, btn_move)

        if is_indexing_axis:
            btn_fwd = _make_axis_btn("前进")
            btn_fwd.clicked.connect(
                lambda _c=False: self._run_indexing_disc_action(
                    indexing_disc_step_forward, "分度盘前进"
                )
            )
            self._buttons.append(btn_fwd)
            _add_axis_btn_slot(actions, btn_fwd)

            btn_back = _make_axis_btn("后退")
            btn_back.clicked.connect(
                lambda _c=False: self._run_indexing_disc_action(
                    indexing_disc_step_backward, "分度盘后退"
                )
            )
            self._buttons.append(btn_back)
            _add_axis_btn_slot(actions, btn_back)
        else:
            _add_axis_btn_slot(actions, None)
            _add_axis_btn_slot(actions, None)

        btn_stop = _make_axis_btn("停止", danger=True)
        btn_stop.clicked.connect(
            lambda _c=False, k=axis.key: self._run_axis_action(
                motion_axis_stop, k, f"{axis.label} 停止"
            )
        )
        self._buttons.append(btn_stop)
        _add_axis_btn_slot(actions, btn_stop)

        layout.addWidget(actions_box, 5)

        target_box = QWidget()
        target_wrap = QHBoxLayout(target_box)
        target_wrap.setContentsMargins(0, 0, 0, 0)
        target_wrap.setSpacing(4)
        t_lab = QLabel("" if is_stir_axis else "目标")
        t_lab.setObjectName("Field")
        t_lab.setFixedWidth(_FIELD_LABEL_WIDTH)
        target_wrap.addWidget(t_lab)
        if is_stir_axis:
            placeholder = QWidget()
            placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            target_wrap.addWidget(placeholder, 1)
        else:
            target_input = QLineEdit()
            target_input.setMinimumWidth(_TARGET_INPUT_MIN_WIDTH)
            target_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            pos_validator = QDoubleValidator(axis.pos_min, axis.pos_max, 3)
            pos_validator.setNotation(QDoubleValidator.StandardNotation)
            target_input.setValidator(pos_validator)
            target_input.setPlaceholderText(axis.unit)
            target_input.editingFinished.connect(lambda k=axis.key: self._sync_axis_params(k))
            self._target_inputs[axis.key] = target_input
            target_wrap.addWidget(target_input, 1)
        layout.addWidget(target_box, 2)

        vel_box = QWidget()
        vel_wrap = QHBoxLayout(vel_box)
        vel_wrap.setContentsMargins(0, 0, 0, 0)
        vel_wrap.setSpacing(4)
        v_lab = QLabel("转速" if is_stir_axis else "速度")
        v_lab.setObjectName("Field")
        v_lab.setFixedWidth(_FIELD_LABEL_WIDTH)
        vel_input = QLineEdit()
        vel_input.setMinimumWidth(_VELOCITY_INPUT_MIN_WIDTH)
        vel_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vel_validator = (
            QDoubleValidator(-5000.0, 5000.0, 2)
            if is_stir_axis
            else QDoubleValidator(0.1, 5000.0, 2)
        )
        vel_validator.setNotation(QDoubleValidator.StandardNotation)
        vel_input.setValidator(vel_validator)
        vel_input.setPlaceholderText(f"{axis.vel_default:g}{axis.unit}/s")
        vel_input.editingFinished.connect(lambda k=axis.key: self._sync_axis_params(k))
        self._velocity_inputs[axis.key] = vel_input
        vel_wrap.addWidget(v_lab)
        vel_wrap.addWidget(vel_input, 1)
        layout.addWidget(vel_box, 2)

        status = QLabel("未读取")
        status.setObjectName("Status")
        status.setMinimumWidth(_AXIS_STATUS_MIN_WIDTH)
        status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._axis_status_labels[axis.key] = status
        layout.addWidget(status, 3)
        return row

    def _build_do_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        for do_item in motion_cfg.DO_OUTPUTS:
            layout.addWidget(self._build_do_item(do_item), 1)
        return card

    def _build_do_item(self, do_item: DoOutputMap) -> QWidget:
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        name = QLabel(do_item.label)
        name.setObjectName("Name")
        row.addWidget(name)

        status = QLabel("关闭")
        status.setObjectName("Status")
        self._do_status_labels[do_item.key] = status
        row.addWidget(status)

        btn_off = _make_btn("关闭", danger=True)
        btn_on = _make_btn("开启", primary=True)
        btn_off.clicked.connect(
            lambda _c=False, k=do_item.key, n=f"{do_item.label} 关闭": self._run_do_action(
                k, False, n
            )
        )
        btn_on.clicked.connect(
            lambda _c=False, k=do_item.key, n=f"{do_item.label} 开启": self._run_do_action(
                k, True, n
            )
        )
        self._do_off_buttons[do_item.key] = btn_off
        self._do_on_buttons[do_item.key] = btn_on
        self._buttons.extend([btn_off, btn_on])
        row.addWidget(btn_on, 1)
        row.addWidget(btn_off, 1)
        return box

    def _build_scanner_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel(f"扫码枪 · {scanner_cfg.SCANNER_MODEL}")
        title.setObjectName("Title")
        layout.addWidget(title)

        self._scanner_status_label = QLabel("状态：未测试")
        self._scanner_status_label.setObjectName("Status")
        layout.addWidget(self._scanner_status_label)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btn_test = _make_btn("连接")
        btn_scan = _make_btn("扫码", primary=True)
        btn_clear = _make_btn("清空")
        btn_test.clicked.connect(
            lambda: self._run_scanner_action(scanner_test_connection, "扫码枪连接测试")
        )
        btn_scan.clicked.connect(
            lambda: self._run_scanner_action(scanner_trigger_read, "触发扫码")
        )
        btn_clear.clicked.connect(
            lambda: self._run_scanner_action(scanner_clear_result, "清空读码结果")
        )
        self._buttons.extend([btn_test, btn_scan, btn_clear])
        btns.addWidget(btn_test, 1)
        btns.addWidget(btn_scan, 1)
        btns.addWidget(btn_clear, 1)
        layout.addLayout(btns)

        self._scanner_result_label = QLabel("读码：—")
        self._scanner_result_label.setObjectName("Result")
        layout.addWidget(self._scanner_result_label)
        return card

    def _build_balance_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel(f"天平 · {balance_cfg.BALANCE_MODEL}")
        title.setObjectName("Title")
        layout.addWidget(title)

        self._balance_status_label = QLabel("状态：未测试")
        self._balance_status_label.setObjectName("Status")
        layout.addWidget(self._balance_status_label)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        btn_test = _make_btn("连接")
        btn_read = _make_btn("读重", primary=True)
        btn_tare = _make_btn("去皮")
        btn_test.clicked.connect(
            lambda: self._run_balance_action(balance_test_connection, "天平连接测试")
        )
        btn_read.clicked.connect(
            lambda: self._run_balance_action(balance_read_weight, "读取重量")
        )
        btn_tare.clicked.connect(lambda: self._run_balance_action(balance_tare, "去皮"))
        self._buttons.extend([btn_test, btn_read, btn_tare])
        row1.addWidget(btn_test, 1)
        row1.addWidget(btn_read, 1)
        row1.addWidget(btn_tare, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        btn_zero = _make_btn("清零")
        btn_clear = _make_btn("清空")
        btn_zero.clicked.connect(lambda: self._run_balance_action(balance_zero, "清零"))
        btn_clear.clicked.connect(
            lambda: self._run_balance_action(balance_clear_result, "清空读重结果")
        )
        self._buttons.extend([btn_zero, btn_clear])
        row2.addWidget(btn_zero, 1)
        row2.addWidget(btn_clear, 1)
        row2.addStretch(1)
        layout.addLayout(row2)

        self._balance_result_label = QLabel("读重：—")
        self._balance_result_label.setObjectName("Result")
        layout.addWidget(self._balance_result_label)
        return card

    def _compact_status(self, axis_key: str) -> str:
        if self._ctx is None:
            return "未读取"
        st = self._ctx.motion.axis(axis_key)
        axis = motion_cfg.AXIS_BY_KEY[axis_key]
        if axis.key == _STIR_AXIS_KEY:
            flags = ["ON" if st.servo_enabled else "OFF", "速度轴"]
        else:
            flags = ["ON" if st.servo_enabled else "OFF", "回零" if st.homed else "未零"]
        if st.moving:
            flags.append("运动")
        if st.alarm:
            flags.append("报警")
        if axis_key == _INDEXING_AXIS_KEY:
            station = self._ctx.motion.indexing_station
            return (
                f"{' '.join(flags)}  工位{station} "
                f"{st.actual_position:g}{axis.unit}"
            )
        return f"{' '.join(flags)}  {st.actual_position:g}{axis.unit}"

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
            f"PLC：{conn} · {mode} · 最近：{motion.last_action or '—'}"
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
            history = " / ".join(st.read_history[:3]) if st.read_history else ""
            text = f"读码：{barcode}"
            if history:
                text += f"  ·  历史：{history}"
            self._scanner_result_label.setText(text)

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
            text = f"读重：{weight}"
            if st.last_raw:
                text += f"  ·  原始：{st.last_raw}"
            self._balance_result_label.setText(text)

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

    def _run_indexing_disc_action(
        self,
        fn: Callable[[SolidDoserMotionContext], Tuple[bool, str]],
        action_name: str,
    ) -> None:
        if self._ctx is None or self._thread is not None:
            return
        self._sync_axis_params(_INDEXING_AXIS_KEY)
        self._set_buttons_enabled(False)
        self._thread = _MotionActionThread(fn, self._ctx, action_name)
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
