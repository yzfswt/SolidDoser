"""清洁工位调试界面。"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from BusinessActions.CleaningStation.cleaning_station_actions import (
    CLEANING_STATION_ACTIONS,
    ActionResult,
)
from BusinessActions.CleaningStation.cleaning_station_context import CleaningStationContext
from Drivers.CleaningStation.cleaning_station_driver import get_cleaning_station_driver
from Drivers.CleaningStation import cleaning_station_config as cs_cfg
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage


class _CleaningActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(
        self,
        fn: Callable[[CleaningStationContext], ActionResult],
        ctx: CleaningStationContext,
        action_name: str,
    ):
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


class CleaningStationDebugTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctx: Optional[CleaningStationContext] = None
        self._thread: Optional[_CleaningActionThread] = None
        self._buttons: List[QPushButton] = []
        self._status_label: Optional[QLabel] = None
        self._rotation_status_label: Optional[QLabel] = None
        self._lift_status_label: Optional[QLabel] = None
        self._pump_status_label: Optional[QLabel] = None
        self._log_view: Optional[QTextEdit] = None
        self._rotation_open_input: Optional[QLineEdit] = None
        self._rotation_close_input: Optional[QLineEdit] = None
        self._rotation_velocity_input: Optional[QLineEdit] = None
        self._lift_up_input: Optional[QLineEdit] = None
        self._lift_down_input: Optional[QLineEdit] = None
        self._lift_velocity_input: Optional[QLineEdit] = None
        self._lift_stop_btn: Optional[QPushButton] = None
        self._rotation_stop_btn: Optional[QPushButton] = None
        self._build_ui()

    def bind_parameter_storage(self, param_storage: ParameterStorage) -> None:
        self._ctx = CleaningStationContext(param_storage)
        self._load_motion_params_from_state()
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        hint = QLabel(
            "清洁工位：升降（大寰电缸 EtherCAT）、合盖（鸣志步进 EtherCAT）、"
            "泵阀（PLC 输出 Y0～Y4）。开盖/合盖、上升/下降位在上位机软件中定义；"
            "发令前写入 PLC 目标 D（每轴一个），PLC 执行绝对定位；命令经 Modbus 写 M 脉冲。"
            f" PLC {cs_cfg.PLC_HOST}:{cs_cfg.PLC_PORT}。"
            " 点表见 Dependencies/Easy521-0808TN/FTIR_CLEANING_STATION_PLC_INTERFACE.md。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 14px;")
        root.addWidget(hint)

        self._status_label = QLabel("状态：未绑定参数")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            "font-size: 14px; padding: 8px; background: #e8f5e9; border: 1px solid #a5d6a7;"
        )
        root.addWidget(self._status_label)

        row = QHBoxLayout()
        row.addWidget(self._build_lift_group())
        row.addWidget(self._build_rotation_group())
        row.addWidget(self._build_pump_group())
        root.addLayout(row)

        refresh_row = QHBoxLayout()
        btn_refresh = QPushButton("刷新全部状态")
        btn_refresh.setMinimumHeight(44)
        btn_refresh.clicked.connect(
            lambda: self._run_action("cleaning_refresh_all")
        )
        self._buttons.append(btn_refresh)
        refresh_row.addWidget(btn_refresh)
        refresh_row.addStretch(1)
        root.addLayout(refresh_row)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("动作执行日志…")
        self._log_view.setMaximumHeight(160)
        root.addWidget(self._log_view)

    def _build_rotation_group(self) -> QGroupBox:
        group = QGroupBox("合盖电机（鸣志步进）")
        layout = QVBoxLayout(group)

        desc = QLabel("EtherCAT 双工位：开盖位 / 合盖位。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        pos_validator = QDoubleValidator(-10000.0, 10000.0, 3)
        pos_validator.setNotation(QDoubleValidator.StandardNotation)
        vel_validator = QDoubleValidator(0.1, 500.0, 2)
        vel_validator.setNotation(QDoubleValidator.StandardNotation)

        open_row = QHBoxLayout()
        open_row.addWidget(QLabel("开盖位："))
        self._rotation_open_input = QLineEdit()
        self._rotation_open_input.setPlaceholderText(
            f"{cs_cfg.ROTATION_OPEN_POSITION_DEFAULT:g}"
        )
        self._rotation_open_input.setValidator(pos_validator)
        self._rotation_open_input.editingFinished.connect(self._sync_motion_params)
        open_row.addWidget(self._rotation_open_input, 1)
        layout.addLayout(open_row)

        close_row = QHBoxLayout()
        close_row.addWidget(QLabel("合盖位："))
        self._rotation_close_input = QLineEdit()
        self._rotation_close_input.setPlaceholderText(
            f"{cs_cfg.ROTATION_CLOSE_POSITION_DEFAULT:g}"
        )
        self._rotation_close_input.setValidator(pos_validator)
        self._rotation_close_input.editingFinished.connect(self._sync_motion_params)
        close_row.addWidget(self._rotation_close_input, 1)
        layout.addLayout(close_row)

        rot_vel_row = QHBoxLayout()
        rot_vel_row.addWidget(QLabel("速度："))
        self._rotation_velocity_input = QLineEdit()
        self._rotation_velocity_input.setPlaceholderText(
            f"{cs_cfg.ROTATION_VELOCITY_DEFAULT:g}"
        )
        self._rotation_velocity_input.setValidator(vel_validator)
        self._rotation_velocity_input.editingFinished.connect(self._sync_motion_params)
        rot_vel_row.addWidget(self._rotation_velocity_input, 1)
        layout.addLayout(rot_vel_row)

        self._rotation_status_label = QLabel("旋转：未读取")
        self._rotation_status_label.setWordWrap(True)
        self._rotation_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._rotation_status_label)

        prim_row = QHBoxLayout()
        for key in ("cleaning_rotation_servo_on", "cleaning_rotation_go_home"):
            label, _fn = CLEANING_STATION_ACTIONS[key]
            btn = QPushButton(label)
            btn.setMinimumHeight(44)
            btn.setStyleSheet("font-weight: bold;")
            btn.clicked.connect(lambda _c=False, k=key: self._run_action(k))
            self._buttons.append(btn)
            prim_row.addWidget(btn)
        layout.addLayout(prim_row)

        keys = [
            "cleaning_rotation_open",
            "cleaning_rotation_close",
            "cleaning_rotation_stop",
        ]
        grid = QGridLayout()
        for i, key in enumerate(keys):
            label, _fn = CLEANING_STATION_ACTIONS[key]
            btn = QPushButton(label)
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda _c=False, k=key: self._run_action(k))
            self._buttons.append(btn)
            if key == "cleaning_rotation_stop":
                self._rotation_stop_btn = btn
            grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(grid)
        return group

    def _build_lift_group(self) -> QGroupBox:
        group = QGroupBox("升降电机（大寰电缸）")
        layout = QVBoxLayout(group)

        desc = QLabel("EtherCAT 双工位：上升位 / 下降位。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        pos_validator = QDoubleValidator(-10000.0, 10000.0, 3)
        pos_validator.setNotation(QDoubleValidator.StandardNotation)
        vel_validator = QDoubleValidator(0.1, 500.0, 2)
        vel_validator.setNotation(QDoubleValidator.StandardNotation)

        up_row = QHBoxLayout()
        up_row.addWidget(QLabel("上升位："))
        self._lift_up_input = QLineEdit()
        self._lift_up_input.setPlaceholderText(f"{cs_cfg.LIFT_UP_POSITION_DEFAULT:g}")
        self._lift_up_input.setValidator(pos_validator)
        self._lift_up_input.editingFinished.connect(self._sync_motion_params)
        up_row.addWidget(self._lift_up_input, 1)
        layout.addLayout(up_row)

        down_row = QHBoxLayout()
        down_row.addWidget(QLabel("下降位："))
        self._lift_down_input = QLineEdit()
        self._lift_down_input.setPlaceholderText(
            f"{cs_cfg.LIFT_DOWN_POSITION_DEFAULT:g}"
        )
        self._lift_down_input.setValidator(pos_validator)
        self._lift_down_input.editingFinished.connect(self._sync_motion_params)
        down_row.addWidget(self._lift_down_input, 1)
        layout.addLayout(down_row)

        lift_vel_row = QHBoxLayout()
        lift_vel_row.addWidget(QLabel("速度："))
        self._lift_velocity_input = QLineEdit()
        self._lift_velocity_input.setPlaceholderText(
            f"{cs_cfg.LIFT_VELOCITY_DEFAULT:g}"
        )
        self._lift_velocity_input.setValidator(vel_validator)
        self._lift_velocity_input.editingFinished.connect(self._sync_motion_params)
        lift_vel_row.addWidget(self._lift_velocity_input, 1)
        layout.addLayout(lift_vel_row)

        self._lift_status_label = QLabel("升降：未读取")
        self._lift_status_label.setWordWrap(True)
        self._lift_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._lift_status_label)

        prim_row = QHBoxLayout()
        for key in ("cleaning_lift_servo_on", "cleaning_lift_go_home"):
            label, _fn = CLEANING_STATION_ACTIONS[key]
            btn = QPushButton(label)
            btn.setMinimumHeight(44)
            btn.setStyleSheet("font-weight: bold;")
            btn.clicked.connect(lambda _c=False, k=key: self._run_action(k))
            self._buttons.append(btn)
            prim_row.addWidget(btn)
        layout.addLayout(prim_row)

        keys = [
            "cleaning_lift_up",
            "cleaning_lift_down",
            "cleaning_lift_stop",
        ]
        grid = QGridLayout()
        for i, key in enumerate(keys):
            label, _fn = CLEANING_STATION_ACTIONS[key]
            btn = QPushButton(label)
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda _c=False, k=key: self._run_action(k))
            self._buttons.append(btn)
            if key == "cleaning_lift_stop":
                self._lift_stop_btn = btn
            grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(grid)
        return group

    def _build_pump_group(self) -> QGroupBox:
        group = QGroupBox("泵阀（Y0～Y4）")
        layout = QVBoxLayout(group)

        desc = QLabel(
            "隔膜气泵 Y0/Y1，隔膜液泵 Y2/Y3，废液泵 Y4。"
            " 保持输出：开=持续运行，关=停止。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        self._pump_status_label = QLabel("泵阀：未读取")
        self._pump_status_label.setWordWrap(True)
        self._pump_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._pump_status_label)

        pump_defs = [
            ("气泵 1 (Y0)", "cleaning_pump_y0_on", "cleaning_pump_y0_off"),
            ("气泵 2 (Y1)", "cleaning_pump_y1_on", "cleaning_pump_y1_off"),
            ("液泵 1 (Y2)", "cleaning_pump_y2_on", "cleaning_pump_y2_off"),
            ("液泵 2 (Y3)", "cleaning_pump_y3_on", "cleaning_pump_y3_off"),
            ("废液泵 (Y4)", "cleaning_pump_y4_on", "cleaning_pump_y4_off"),
        ]
        grid = QGridLayout()
        for row, (title, on_key, off_key) in enumerate(pump_defs):
            grid.addWidget(QLabel(title), row, 0)
            on_label, _ = CLEANING_STATION_ACTIONS[on_key]
            off_label, _ = CLEANING_STATION_ACTIONS[off_key]
            btn_on = QPushButton(on_label)
            btn_off = QPushButton(off_label)
            btn_on.setMinimumHeight(40)
            btn_off.setMinimumHeight(40)
            btn_on.clicked.connect(lambda _c=False, k=on_key: self._run_action(k))
            btn_off.clicked.connect(lambda _c=False, k=off_key: self._run_action(k))
            self._buttons.extend([btn_on, btn_off])
            grid.addWidget(btn_on, row, 1)
            grid.addWidget(btn_off, row, 2)

        layout.addLayout(grid)

        btn_all_off = QPushButton("全部泵关闭")
        btn_all_off.setMinimumHeight(44)
        btn_all_off.clicked.connect(
            lambda: self._run_action("cleaning_pumps_all_off")
        )
        self._buttons.append(btn_all_off)
        layout.addWidget(btn_all_off)
        return group

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)
        # 定位/回零等长动作期间仍允许急停
        if not enabled:
            if self._lift_stop_btn is not None:
                self._lift_stop_btn.setEnabled(True)
            if self._rotation_stop_btn is not None:
                self._rotation_stop_btn.setEnabled(True)

    def _bind_motion_cancel(self) -> None:
        if self._ctx is None:
            return
        get_cleaning_station_driver().set_motion_cancel_check(
            lambda: self._ctx.motion_cancel_requested
        )

    def _clear_motion_cancel(self) -> None:
        if self._ctx is not None:
            self._ctx.motion_cancel_requested = False
        get_cleaning_station_driver().set_motion_cancel_check(None)

    def _run_stop_during_busy(self, action_key: str) -> None:
        if self._ctx is None:
            return
        self._ctx.motion_cancel_requested = True
        label, fn = CLEANING_STATION_ACTIONS[action_key]
        self._append_log(f">>> 开始：{label}")
        try:
            ok, msg = fn(self._ctx)
            flag = "成功" if ok else "失败"
            self._append_log(f"[{flag}] {label}：{msg}")
        except Exception as exc:
            self._append_log(f"[失败] {label}：{exc}")
        self._refresh_status()

    @staticmethod
    def _read_float_input(
        field: Optional[QLineEdit], fallback: float
    ) -> float:
        if field is None:
            return fallback
        text = field.text().strip()
        if not text:
            return fallback
        try:
            return float(text)
        except ValueError:
            return fallback

    def _load_motion_params_from_state(self) -> None:
        if self._ctx is None:
            return
        s = self._ctx.station
        if self._rotation_open_input is not None:
            self._rotation_open_input.setText(f"{s.rotation_open_position:g}")
        if self._rotation_close_input is not None:
            self._rotation_close_input.setText(f"{s.rotation_close_position:g}")
        if self._rotation_velocity_input is not None:
            self._rotation_velocity_input.setText(f"{s.rotation_velocity:g}")
        if self._lift_up_input is not None:
            self._lift_up_input.setText(f"{s.lift_up_position:g}")
        if self._lift_down_input is not None:
            self._lift_down_input.setText(f"{s.lift_down_position:g}")
        if self._lift_velocity_input is not None:
            self._lift_velocity_input.setText(f"{s.lift_velocity:g}")

    def _sync_motion_params(self) -> None:
        if self._ctx is None:
            return
        s = self._ctx.station
        s.rotation_open_position = self._read_float_input(
            self._rotation_open_input, cs_cfg.ROTATION_OPEN_POSITION_DEFAULT
        )
        s.rotation_close_position = self._read_float_input(
            self._rotation_close_input, cs_cfg.ROTATION_CLOSE_POSITION_DEFAULT
        )
        s.rotation_velocity = self._read_float_input(
            self._rotation_velocity_input, cs_cfg.ROTATION_VELOCITY_DEFAULT
        )
        s.lift_up_position = self._read_float_input(
            self._lift_up_input, cs_cfg.LIFT_UP_POSITION_DEFAULT
        )
        s.lift_down_position = self._read_float_input(
            self._lift_down_input, cs_cfg.LIFT_DOWN_POSITION_DEFAULT
        )
        s.lift_velocity = self._read_float_input(
            self._lift_velocity_input, cs_cfg.LIFT_VELOCITY_DEFAULT
        )

    def _run_action(self, action_key: str) -> None:
        if self._ctx is None:
            QMessageBox.warning(self, "清洁工位", "参数未绑定，请重新启动程序。")
            return
        if self._thread is not None and self._thread.isRunning():
            if action_key in ("cleaning_lift_stop", "cleaning_rotation_stop"):
                self._run_stop_during_busy(action_key)
                return
            QMessageBox.information(self, "清洁工位", "正在执行动作，请稍候。")
            return

        self._sync_motion_params()
        self._clear_motion_cancel()
        self._bind_motion_cancel()

        label, fn = CLEANING_STATION_ACTIONS[action_key]
        self._append_log(f">>> 开始：{label}")
        self._set_buttons_enabled(False)

        self._thread = _CleaningActionThread(fn, self._ctx, label)
        self._thread.finished.connect(self._on_action_finished)
        self._thread.start()

    def _on_action_finished(self, ok: bool, msg: str, action_name: str) -> None:
        self._clear_motion_cancel()
        self._set_buttons_enabled(True)
        flag = "成功" if ok else "失败"
        if not ok and msg == "已停止":
            flag = "已中断"
        self._append_log(f"[{flag}] {action_name}：{msg}")
        self._refresh_status()
        if not ok and msg != "已停止":
            QMessageBox.warning(self, action_name, msg)

    def _append_log(self, line: str) -> None:
        if self._log_view is not None:
            self._log_view.append(line)

    def _refresh_status(self) -> None:
        if self._ctx is None:
            return
        s = self._ctx.station
        if self._rotation_status_label is not None:
            self._rotation_status_label.setText(
                f"合盖：{s.rotation_status_summary}  |  "
                f"当前 {s.rotation_actual_position:g}  "
                f"（开盖 {s.rotation_open_position:g} / 合盖 {s.rotation_close_position:g}）"
            )
        if self._lift_status_label is not None:
            self._lift_status_label.setText(
                f"升降：{s.lift_status_summary}  |  "
                f"当前 {s.lift_actual_position:g}  "
                f"（上升 {s.lift_up_position:g} / 下降 {s.lift_down_position:g}）"
            )
        if self._pump_status_label is not None:
            self._pump_status_label.setText(f"泵阀：{s.pump_summary()}")
        if self._status_label is not None:
            self._status_label.setText(
                f"升降：{s.lift_status_summary}  |  "
                f"合盖：{s.rotation_status_summary}  |  "
                f"{s.pump_summary()}  |  "
                f"上次：{s.last_action or '—'}（"
                f"{'成功' if s.last_success else '失败'}）"
            )
