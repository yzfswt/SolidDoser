"""机器人调试界面：单步动作按钮。"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from BusinessActions.Robot.robot_actions import ROBOT_ACTIONS, ActionResult
from BusinessActions.Robot.robot_context import RobotContext
from Drivers.Axis5 import axis5_config as axis5_cfg
from Drivers.Axis5.axis5_driver import get_axis5_driver
from Drivers.ElectricGripper import gripper_config as gripper_cfg
from Drivers.ElectricActuator import pgc_config as pgc_cfg
from Drivers.Pipette import pipette_config as pipette_cfg
from Drivers.SerialServer import zlan5212di_config as serial_cfg
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage


class _RobotActionThread(QThread):
    finished = Signal(bool, str, str)

    def __init__(self, fn: Callable[[RobotContext], ActionResult], ctx: RobotContext, action_name: str):
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


class RobotDebugTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctx: Optional[RobotContext] = None
        self._thread: Optional[_RobotActionThread] = None
        self._buttons: List[QPushButton] = []
        self._status_label: Optional[QLabel] = None
        self._log_view: Optional[QTextEdit] = None
        self._axis5_target_input: Optional[QLineEdit] = None
        self._axis5_velocity_input: Optional[QLineEdit] = None
        self._axis5_status_label: Optional[QLabel] = None
        self._axis5_stop_btn: Optional[QPushButton] = None
        self._robot_stop_btn: Optional[QPushButton] = None
        self._pipette_volume_input: Optional[QLineEdit] = None
        self._pgc_extend_target_input: Optional[QLineEdit] = None
        self._pgc_push_segment_input: Optional[QLineEdit] = None
        self._pgc_thrust_input: Optional[QLineEdit] = None
        self._pgc_retract_target_input: Optional[QLineEdit] = None
        self._pgc_status_label: Optional[QLabel] = None
        self._gripper_force_input: Optional[QLineEdit] = None
        self._gripper_extend_target_input: Optional[QLineEdit] = None
        self._gripper_push_segment_input: Optional[QLineEdit] = None
        self._gripper_retract_target_input: Optional[QLineEdit] = None
        self._gripper_status_label: Optional[QLabel] = None
        self._tool_detect_label: Optional[QLabel] = None
        self._build_ui()

    def bind_parameter_storage(self, param_storage: ParameterStorage) -> None:
        self._ctx = RobotContext(param_storage)
        if self._axis5_target_input is not None:
            self._axis5_target_input.setText(
                f"{param_storage.robot.axis5_target_mm:g}"
            )
        if self._axis5_velocity_input is not None:
            self._axis5_velocity_input.setText(
                f"{param_storage.robot.axis5_velocity_mm_s:g}"
            )
        if self._pipette_volume_input is not None:
            self._pipette_volume_input.setText(
                str(param_storage.robot.pipette_volume_ul)
            )
        r = param_storage.robot
        if self._pgc_extend_target_input is not None:
            self._pgc_extend_target_input.setText(f"{r.pgc_extend_target_mm:g}")
        if self._pgc_push_segment_input is not None:
            self._pgc_push_segment_input.setText(f"{r.pgc_extend_push_segment_mm:g}")
        if self._pgc_thrust_input is not None:
            self._pgc_thrust_input.setText(str(r.pgc_extend_thrust_percent))
        if self._pgc_retract_target_input is not None:
            self._pgc_retract_target_input.setText(f"{r.pgc_retract_target_mm:g}")
        if self._gripper_force_input is not None:
            self._gripper_force_input.setText(str(r.gripper_force_percent))
        if self._gripper_extend_target_input is not None:
            self._gripper_extend_target_input.setText(f"{r.gripper_extend_target_mm:g}")
        if self._gripper_push_segment_input is not None:
            self._gripper_push_segment_input.setText(f"{r.gripper_extend_push_segment_mm:g}")
        if self._gripper_retract_target_input is not None:
            self._gripper_retract_target_input.setText(f"{r.gripper_retract_target_mm:g}")
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(8, 8, 8, 8)

        hint = QLabel(
            "机器人调试：移液枪/电爪/电缸经 ZLAN5212DI 串口服务器 RS485 已接入即可在对应组直接测试；"
            "「工具检测」按 RS485 地址识别末端工具（电爪=1、电缸=2、移液枪=3）。"
            "「装取」组用于完整流程（取放工具、枪头）。"
            "取物料、ATR 操作前请先在料盘/枪头架界面配置状态。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 14px;")
        root.addWidget(hint)

        tool_row = QHBoxLayout()
        btn_detect = QPushButton("工具检测")
        btn_detect.setMinimumHeight(44)
        btn_detect.setStyleSheet("font-weight: bold;")
        btn_detect.clicked.connect(lambda: self._run_action("detect_tool"))
        self._buttons.append(btn_detect)
        tool_row.addWidget(btn_detect)

        self._tool_detect_label = QLabel(
            f"地址映射：电爪 {gripper_cfg.MODBUS_SLAVE_ID} | "
            f"电缸 {pgc_cfg.MODBUS_SLAVE_ID} | "
            f"移液枪 {pipette_cfg.PIPETTE_DEVICE_ADDRESS} | "
            f"无工具 = 均无应答"
        )
        self._tool_detect_label.setWordWrap(True)
        self._tool_detect_label.setStyleSheet("color: #555; font-size: 13px;")
        tool_row.addWidget(self._tool_detect_label, 1)
        root.addLayout(tool_row)

        self._status_label = QLabel("状态：未连接参数")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            "font-size: 14px; padding: 8px; background: #e3f2fd; border: 1px solid #90caf9;"
        )
        root.addWidget(self._status_label)

        stop_row = QHBoxLayout()
        self._robot_stop_btn = QPushButton("停止")
        self._robot_stop_btn.setMinimumHeight(48)
        self._robot_stop_btn.setMinimumWidth(120)
        self._robot_stop_btn.setStyleSheet(
            "font-weight: bold; font-size: 16px; background: #c62828; color: white;"
        )
        self._robot_stop_btn.clicked.connect(lambda: self._run_action("robot_stop"))
        stop_row.addWidget(self._robot_stop_btn)
        stop_hint = QLabel(
            "执行任意动作期间可点击：取消 Studio 等待、停止第五轴，"
            "并在 Hitbot SDK 已连接时停止机械臂运动。"
        )
        stop_hint.setWordWrap(True)
        stop_hint.setStyleSheet("color: #555; font-size: 13px;")
        stop_row.addWidget(stop_hint, 1)
        root.addLayout(stop_row)

        groups_top = QHBoxLayout()
        groups_top.setSpacing(10)
        groups_top.setAlignment(Qt.AlignmentFlag.AlignTop)
        groups_bottom = QHBoxLayout()
        groups_bottom.setSpacing(10)
        groups_bottom.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_titles = {"移液枪装取", "移液枪", "电缸装取", "电缸"}

        tool_defs: List[Tuple[str, List[str]]] = [
            (
                "移液枪装取",
                ["pick_pipette", "place_pipette", "pick_tip", "place_tip"],
            ),
            (
                "移液枪",
                [
                    "pipette_init",
                    "pipette_aspirate",
                    "pipette_dispense",
                    "pipette_eject_tip",
                ],
            ),
            (
                "电缸装取",
                [
                    "pick_electric_actuator",
                    "place_electric_actuator",
                    "use_electric_actuator",
                    "clean_electric_actuator",
                ],
            ),
            (
                "电缸",
                [
                    "electric_actuator_enable",
                    "electric_actuator_disable",
                    "electric_actuator_stroke_init",
                    "electric_actuator_extend",
                    "electric_actuator_retract",
                    "electric_actuator_home",
                    "electric_actuator_clear_alarm",
                    "electric_actuator_refresh_status",
                ],  # 顺序：使能 → 初始化 → 回零/伸出/缩回
            ),
            (
                "电爪装取",
                ["pick_gripper", "place_gripper", "use_gripper"],
            ),
            (
                "电爪",
                [
                    "gripper_init",
                    "gripper_home",
                    "gripper_extend",
                    "gripper_retract",
                    "gripper_refresh_status",
                ],
            ),
            (
                "物料 / ATR",
                ["pick_material", "pick_atr", "place_atr", "clean_atr"],
            ),
        ]

        for title, keys in tool_defs:
            if title == "移液枪":
                group = self._build_pipette_group(keys)
            elif title == "电缸":
                group = self._build_pgc_group(keys)
            elif title == "电爪":
                group = self._build_gripper_group(keys)
            else:
                group = self._build_action_group(title, keys)
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            if title in top_titles:
                groups_top.addWidget(group, 1)
            else:
                groups_bottom.addWidget(group, 1)

        scroll_body = QWidget()
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addLayout(groups_top)
        scroll_layout.addLayout(groups_bottom)
        scroll_layout.addWidget(self._build_axis5_group())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_body)
        root.addWidget(scroll, 1)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("动作执行日志…")
        self._log_view.setMaximumHeight(160)
        root.addWidget(self._log_view)

    @staticmethod
    def _configure_group_layout(layout: QVBoxLayout) -> None:
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

    @staticmethod
    def _make_button_grid(*, columns: int = 2) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        return grid

    @staticmethod
    def _add_param_field(
        grid: QGridLayout,
        *,
        row: int,
        column: int,
        label: str,
        placeholder: str,
        validator,
        on_change: Callable[[], None],
    ) -> QLineEdit:
        grid.addWidget(QLabel(label), row, column * 2)
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        if validator is not None:
            field.setValidator(validator)
        field.editingFinished.connect(on_change)
        grid.addWidget(field, row, column * 2 + 1)
        return field

    @staticmethod
    def _add_action_button(
        grid: QGridLayout,
        *,
        key: str,
        row: int,
        column: int,
        buttons: List[QPushButton],
        click_handler: Callable[[str], None],
        bold: bool = False,
        row_span: int = 1,
        column_span: int = 1,
    ) -> QPushButton:
        label, _fn = ROBOT_ACTIONS[key]
        btn = QPushButton(label)
        btn.setMinimumHeight(44)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if bold:
            btn.setStyleSheet("font-weight: bold;")
        btn.clicked.connect(lambda _checked=False, k=key: click_handler(k))
        buttons.append(btn)
        grid.addWidget(btn, row, column, row_span, column_span)
        return btn

    def _build_pipette_group(self, action_keys: List[str]) -> QGroupBox:
        group = QGroupBox("移液枪")
        layout = QVBoxLayout(group)
        self._configure_group_layout(layout)

        desc = QLabel(
            f"ST5000P：经 ZLAN5212DI 串口服务器（{serial_cfg.SERIAL_SERVER_HOST}:"
            f"{serial_cfg.SERIAL_SERVER_PORT} PORT1）RS485 透传。"
            "物理接入后可直接「初始化/取液/排液/退枪头」，无需先点「取移液枪」「取枪头」。体积单位 µL。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("体积 (µL)："))
        self._pipette_volume_input = QLineEdit()
        self._pipette_volume_input.setPlaceholderText("100")
        validator = QIntValidator(1, 99999)
        self._pipette_volume_input.setValidator(validator)
        self._pipette_volume_input.editingFinished.connect(self._sync_pipette_volume)
        volume_row.addWidget(self._pipette_volume_input, 1)
        layout.addLayout(volume_row)

        grid = self._make_button_grid()
        for i, key in enumerate(action_keys):
            self._add_action_button(
                grid,
                key=key,
                row=i // 2,
                column=i % 2,
                buttons=self._buttons,
                click_handler=self._on_pipette_action_clicked,
            )
        layout.addLayout(grid)

        return group

    def _sync_pipette_volume(self) -> None:
        if self._ctx is None or self._pipette_volume_input is None:
            return
        text = self._pipette_volume_input.text().strip()
        try:
            self._ctx.robot.pipette_volume_ul = int(text) if text else 100
        except ValueError:
            pass

    def _on_pipette_action_clicked(self, action_key: str) -> None:
        if action_key in ("pipette_aspirate", "pipette_dispense"):
            self._sync_pipette_volume()
        self._run_action(action_key)

    def _build_pgc_group(self, action_keys: List[str]) -> QGroupBox:
        group = QGroupBox("电缸")
        layout = QVBoxLayout(group)
        self._configure_group_layout(layout)

        desc = QLabel(
            "MCEA-3G-01-030-C-W-F：Modbus ID=2，经 ZLAN5212DI RS485。"
            "须先：使能 → 初始化；之后可回零、伸出、缩回等（回零非必须前置步骤）。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        self._pgc_status_label = QLabel("电缸状态：未读取")
        self._pgc_status_label.setWordWrap(True)
        self._pgc_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._pgc_status_label)

        mm_validator = QDoubleValidator(0.0, 30.0, 2)
        mm_validator.setNotation(QDoubleValidator.StandardNotation)
        retract_validator = QDoubleValidator(0.0, 30.0, 2)
        retract_validator.setNotation(QDoubleValidator.StandardNotation)

        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(8)
        param_grid.setVerticalSpacing(6)
        self._pgc_extend_target_input = self._add_param_field(
            param_grid,
            row=0,
            column=0,
            label="目标 (mm)：",
            placeholder="30",
            validator=mm_validator,
            on_change=self._sync_pgc_params,
        )
        self._pgc_push_segment_input = self._add_param_field(
            param_grid,
            row=0,
            column=1,
            label="推压段 (mm)：",
            placeholder="0",
            validator=mm_validator,
            on_change=self._sync_pgc_params,
        )
        self._pgc_thrust_input = self._add_param_field(
            param_grid,
            row=1,
            column=0,
            label="推力 (%)：",
            placeholder="50",
            validator=QIntValidator(1, 100),
            on_change=self._sync_pgc_params,
        )
        self._pgc_retract_target_input = self._add_param_field(
            param_grid,
            row=1,
            column=1,
            label="缩回 (mm)：",
            placeholder="0",
            validator=retract_validator,
            on_change=self._sync_pgc_params,
        )
        layout.addLayout(param_grid)

        grid = self._make_button_grid()
        for i, key in enumerate(action_keys):
            self._add_action_button(
                grid,
                key=key,
                row=i // 2,
                column=i % 2,
                buttons=self._buttons,
                click_handler=self._on_pgc_action_clicked,
            )
        layout.addLayout(grid)

        return group

    def _sync_pgc_params(self) -> None:
        if self._ctx is None:
            return
        r = self._ctx.robot
        if self._pgc_extend_target_input is not None:
            text = self._pgc_extend_target_input.text().strip()
            try:
                r.pgc_extend_target_mm = float(text) if text else 30.0
            except ValueError:
                pass
        if self._pgc_push_segment_input is not None:
            text = self._pgc_push_segment_input.text().strip()
            try:
                r.pgc_extend_push_segment_mm = float(text) if text else 0.0
            except ValueError:
                pass
        if self._pgc_thrust_input is not None:
            text = self._pgc_thrust_input.text().strip()
            try:
                r.pgc_extend_thrust_percent = int(text) if text else 50
            except ValueError:
                pass
        if self._pgc_retract_target_input is not None:
            text = self._pgc_retract_target_input.text().strip()
            try:
                r.pgc_retract_target_mm = float(text) if text else 0.0
            except ValueError:
                pass

    def _on_pgc_action_clicked(self, action_key: str) -> None:
        self._sync_pgc_params()
        self._run_action(action_key)

    def _build_gripper_group(self, action_keys: List[str]) -> QGroupBox:
        group = QGroupBox("电爪")
        layout = QVBoxLayout(group)
        self._configure_group_layout(layout)

        desc = QLabel(
            "PGC-300-60-W-S，Modbus ID=1，经 ZLAN5212DI RS485。"
            "顺序：初始化 → 打开 → 关闭（力控夹持）。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        self._gripper_status_label = QLabel("电爪状态：未读取")
        self._gripper_status_label.setWordWrap(True)
        self._gripper_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._gripper_status_label)

        mm_validator = QDoubleValidator(0.0, 60.0, 2)
        mm_validator.setNotation(QDoubleValidator.StandardNotation)

        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(8)
        param_grid.setVerticalSpacing(6)
        self._gripper_force_input = self._add_param_field(
            param_grid,
            row=0,
            column=0,
            label="夹持力 (%)：",
            placeholder="30",
            validator=QIntValidator(20, 100),
            on_change=self._sync_gripper_params,
        )
        self._gripper_extend_target_input = self._add_param_field(
            param_grid,
            row=0,
            column=1,
            label="打开 (mm)：",
            placeholder="60",
            validator=mm_validator,
            on_change=self._sync_gripper_params,
        )
        self._gripper_push_segment_input = self._add_param_field(
            param_grid,
            row=1,
            column=0,
            label="推压段 (mm)：",
            placeholder="60",
            validator=mm_validator,
            on_change=self._sync_gripper_params,
        )
        self._gripper_retract_target_input = self._add_param_field(
            param_grid,
            row=1,
            column=1,
            label="关闭 (mm)：",
            placeholder="0",
            validator=mm_validator,
            on_change=self._sync_gripper_params,
        )
        layout.addLayout(param_grid)

        grid = self._make_button_grid()
        for i, key in enumerate(action_keys):
            self._add_action_button(
                grid,
                key=key,
                row=i // 2,
                column=i % 2,
                buttons=self._buttons,
                click_handler=self._on_gripper_action_clicked,
            )
        layout.addLayout(grid)

        return group

    def _sync_gripper_params(self) -> None:
        if self._ctx is None:
            return
        r = self._ctx.robot
        if self._gripper_force_input is not None:
            text = self._gripper_force_input.text().strip()
            try:
                r.gripper_force_percent = int(text) if text else 30
            except ValueError:
                pass
        if self._gripper_extend_target_input is not None:
            text = self._gripper_extend_target_input.text().strip()
            try:
                r.gripper_extend_target_mm = float(text) if text else 60.0
            except ValueError:
                pass
        if self._gripper_push_segment_input is not None:
            text = self._gripper_push_segment_input.text().strip()
            try:
                r.gripper_extend_push_segment_mm = float(text) if text else 60.0
            except ValueError:
                pass
        if self._gripper_retract_target_input is not None:
            text = self._gripper_retract_target_input.text().strip()
            try:
                r.gripper_retract_target_mm = float(text) if text else 0.0
            except ValueError:
                pass

    def _on_gripper_action_clicked(self, action_key: str) -> None:
        self._sync_gripper_params()
        self._run_action(action_key)

    def _update_pgc_status_label(self) -> None:
        if self._ctx is None or self._pgc_status_label is None:
            return
        r = self._ctx.robot
        self._pgc_status_label.setText(f"电缸状态：{r.pgc_status_summary}")

    def _update_gripper_status_label(self) -> None:
        if self._ctx is None or self._gripper_status_label is None:
            return
        r = self._ctx.robot
        self._gripper_status_label.setText(f"电爪状态：{r.gripper_status_summary}")

    def _build_axis5_group(self) -> QGroupBox:
        group = QGroupBox("第五轴（滑台）")
        layout = QVBoxLayout(group)
        self._configure_group_layout(layout)

        desc = QLabel(
            "Easy521 + SV630（EtherCAT），上位机 Modbus TCP 写 PLC 的 M/D，"
            "PLC 内执行 MC_Power / MC_Home / MC_MoveAbsolute。"
            "调试顺序：使能 → 回零 → 绝对定位。"
            f"点表见 Dependencies/Easy521-0808TN/FTIR_AXIS5_PLC_INTERFACE.md。"
            f" PLC {axis5_cfg.PLC_HOST}:{axis5_cfg.PLC_PORT}。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(desc)

        self._axis5_status_label = QLabel("第五轴状态：未读取")
        self._axis5_status_label.setWordWrap(True)
        self._axis5_status_label.setStyleSheet(
            "font-size: 13px; padding: 6px; background: #f5f5f5; border: 1px solid #ddd;"
        )
        layout.addWidget(self._axis5_status_label)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("绝对位置 (mm)："))
        self._axis5_target_input = QLineEdit()
        self._axis5_target_input.setPlaceholderText("0")
        target_validator = QDoubleValidator(
            axis5_cfg.AXIS5_MIN_MM, axis5_cfg.AXIS5_MAX_MM, 3
        )
        target_validator.setNotation(QDoubleValidator.StandardNotation)
        self._axis5_target_input.setValidator(target_validator)
        self._axis5_target_input.editingFinished.connect(self._sync_axis5_params)
        target_row.addWidget(self._axis5_target_input, 1)
        layout.addLayout(target_row)

        velocity_row = QHBoxLayout()
        velocity_row.addWidget(QLabel("速度 (mm/s)："))
        self._axis5_velocity_input = QLineEdit()
        self._axis5_velocity_input.setPlaceholderText("50")
        velocity_validator = QDoubleValidator(0.1, 500.0, 2)
        velocity_validator.setNotation(QDoubleValidator.StandardNotation)
        self._axis5_velocity_input.setValidator(velocity_validator)
        self._axis5_velocity_input.editingFinished.connect(self._sync_axis5_params)
        velocity_row.addWidget(self._axis5_velocity_input, 1)
        layout.addLayout(velocity_row)

        grid = self._make_button_grid()
        primary_keys = (
            "axis5_servo_on",
            "axis5_go_home",
            "axis5_move_to_target",
            "axis5_stop",
        )
        for i, key in enumerate(primary_keys):
            btn = self._add_action_button(
                grid,
                key=key,
                row=0,
                column=i,
                buttons=self._buttons,
                click_handler=self._on_axis5_action_clicked,
                bold=key in ("axis5_servo_on", "axis5_go_home"),
            )
            if key == "axis5_stop":
                self._axis5_stop_btn = btn
        self._add_action_button(
            grid,
            key="axis5_refresh_status",
            row=1,
            column=0,
            column_span=2,
            buttons=self._buttons,
            click_handler=self._on_axis5_action_clicked,
        )
        layout.addLayout(grid)

        return group

    def _sync_axis5_params(self) -> None:
        if self._ctx is None:
            return
        r = self._ctx.robot
        if self._axis5_target_input is not None:
            text = self._axis5_target_input.text().strip()
            try:
                r.axis5_target_mm = float(text) if text else 0.0
            except ValueError:
                pass
        if self._axis5_velocity_input is not None:
            text = self._axis5_velocity_input.text().strip()
            try:
                r.axis5_velocity_mm_s = (
                    float(text) if text else axis5_cfg.AXIS5_DEFAULT_VELOCITY_MM_S
                )
            except ValueError:
                pass

    def _on_axis5_action_clicked(self, action_key: str) -> None:
        self._sync_axis5_params()
        self._run_action(action_key)

    def _update_axis5_status_label(self) -> None:
        if self._ctx is None or self._axis5_status_label is None:
            return
        r = self._ctx.robot
        self._axis5_status_label.setText(f"第五轴状态：{r.axis5_status_summary}")

    def _build_action_group(self, title: str, action_keys: List[str]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        self._configure_group_layout(layout)
        grid = self._make_button_grid()
        for i, key in enumerate(action_keys):
            self._add_action_button(
                grid,
                key=key,
                row=i // 2,
                column=i % 2,
                buttons=self._buttons,
                click_handler=self._run_action,
            )
        layout.addLayout(grid)
        return group

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)
        # 长动作执行期间仍允许急停
        if not enabled:
            if self._axis5_stop_btn is not None:
                self._axis5_stop_btn.setEnabled(True)
            if self._robot_stop_btn is not None:
                self._robot_stop_btn.setEnabled(True)

    def _bind_motion_cancel(self) -> None:
        if self._ctx is None:
            return
        get_axis5_driver().set_motion_cancel_check(
            lambda: self._ctx.motion_cancel_requested
        )

    def _clear_motion_cancel(self) -> None:
        if self._ctx is not None:
            self._ctx.motion_cancel_requested = False
        get_axis5_driver().set_motion_cancel_check(None)

    def _run_stop_during_busy(self, action_key: str) -> None:
        if self._ctx is None:
            return
        self._ctx.motion_cancel_requested = True
        label, fn = ROBOT_ACTIONS[action_key]
        self._append_log(f">>> 开始：{label}")
        try:
            ok, msg = fn(self._ctx)
            flag = "成功" if ok else "失败"
            self._append_log(f"[{flag}] {label}：{msg}")
        except Exception as exc:
            self._append_log(f"[失败] {label}：{exc}")
        self._refresh_status()
        self._update_pgc_status_label()
        self._update_gripper_status_label()
        self._update_axis5_status_label()

    def _run_action(self, action_key: str) -> None:
        if self._ctx is None:
            QMessageBox.warning(self, "机器人调试", "参数未绑定，请重新启动程序。")
            return
        if self._thread is not None and self._thread.isRunning():
            if action_key in ("robot_stop", "axis5_stop"):
                self._run_stop_during_busy(action_key)
                return
            QMessageBox.information(self, "机器人调试", "正在执行动作，请稍候。")
            return

        label, fn = ROBOT_ACTIONS[action_key]
        self._append_log(f">>> 开始：{label}")
        self._clear_motion_cancel()
        self._bind_motion_cancel()
        self._set_buttons_enabled(False)

        self._thread = _RobotActionThread(fn, self._ctx, label)
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
        self._update_pgc_status_label()
        self._update_gripper_status_label()
        self._update_axis5_status_label()

    def _append_log(self, line: str) -> None:
        if self._log_view is None:
            return
        self._log_view.append(line)

    def _refresh_status(self) -> None:
        if self._ctx is None or self._status_label is None:
            return
        r = self._ctx.robot
        tip = "有" if r.pipette_has_tip else "无"
        axis5_power = "已使能" if r.axis5_servo_enabled else "未使能"
        homed = "已回零" if r.axis5_homed else "未回零"
        self._status_label.setText(
            f"末端工具：{r.tool_label()}  |  移液枪枪头：{tip}  |  "
            f"移液体积：{r.pipette_volume_ul} µL  |  "
            f"电缸伸出：目标 {r.pgc_extend_target_mm:g} mm / 推压段 {r.pgc_extend_push_segment_mm:g} mm / "
            f"推力 {r.pgc_extend_thrust_percent}%  |  缩回 {r.pgc_retract_target_mm:g} mm  |  "
            f"电缸：{'已使能' if r.pgc_enabled else '未使能'} / "
            f"{'行程已标定' if r.pgc_stroke_initialized else '行程未标定'} / "
            f"{'已回零' if r.pgc_homed else '未回零'} / "
            f"位置 {r.pgc_position_mm:g} mm  |  "
            f"电爪：打开 {r.gripper_extend_target_mm:g} mm / 关闭 {r.gripper_retract_target_mm:g} mm / "
            f"夹持力 {r.gripper_force_percent}%  |  "
            f"电爪：{'已初始化' if r.gripper_homed else '未初始化'} / "
            f"位置 {r.gripper_position_mm:g} mm  |  "
            f"第五轴：{axis5_power} / {homed} / {r.axis5_current_mm:g} mm（目标 {r.axis5_target_mm:g} mm，"
            f"{'运动中' if r.axis5_moving else '静止'}）  |  "
            f"ATR：{r.atr_location.value}  |  "
            f"上次：{r.last_action or '—'}（{'成功' if r.last_success else '失败'}）"
        )
