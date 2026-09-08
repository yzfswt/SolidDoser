"""SolidDoser 自动运行界面（系统状态机入口）。"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from BusinessActions.SolidDoserSystem.system_actions import (
    system_request_abort,
    system_run_bottle_discharge,
    system_run_device_init,
    system_run_dose,
    system_run_go_datum,
    system_run_go_origin,
    system_run_initialize,
    system_run_servo_on_all,
)
from BusinessActions.SolidDoserSystem.system_context import SolidDoserSystemContext
from Drivers.SolidDoserMotion import motion_config as motion_cfg
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ParameterManagement.SolidDoserSystemModel import DoseItem

ActionFn = Callable[[SolidDoserSystemContext], Tuple[bool, str]]

# 与调试页轴按钮一致的高度/字号；宽度兼顾「试剂瓶出料」
_AUTO_BTN_MIN_WIDTH = 96
_AUTO_BTN_SPACING = 4
# 物料表条码行 / 加料清单表行统一行高
_LIST_ROW_HEIGHT = 30

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
QLabel#MaterialStation {
    font-size: 12px;
    font-weight: 600;
    color: #334155;
    min-width: 44px;
}
QLabel#MaterialCode {
    font-size: 12px;
    color: #334155;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 0px 8px;
    min-height: 30px;
    max-height: 30px;
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
QTableWidget {
    font-size: 12px;
    gridline-color: #e2e8f0;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    background: #ffffff;
}
QTableWidget::item {
    padding: 0px 6px;
}
QHeaderView::section {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    padding: 0px 6px;
    min-height: 30px;
    max-height: 30px;
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
        self._materials_title: Optional[QLabel] = None
        self._material_code_labels: Dict[int, QLabel] = {}
        self._dose_table: Optional[QTableWidget] = None
        self._dose_add_btn: Optional[QPushButton] = None
        self._dose_del_btn: Optional[QPushButton] = None
        self._action_log_handler: Optional[Callable[[str], None]] = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._refresh_status)
        self._build_ui()

    def set_action_log_handler(self, handler: Optional[Callable[[str], None]]) -> None:
        self._action_log_handler = handler

    def bind_parameter_storage(self, param_storage: ParameterStorage) -> None:
        self._ctx = SolidDoserSystemContext(param_storage)
        self._load_dose_table(param_storage.solid_doser_system.dose_items)
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
        status_layout.addWidget(self._state_label)
        status_layout.addWidget(self._flags_label)
        status_layout.addWidget(self._progress_label)
        status_layout.addWidget(self._log_label)
        root.addWidget(status_card)

        materials_card = QFrame()
        materials_card.setObjectName("Card")
        materials_layout = QVBoxLayout(materials_card)
        materials_layout.setContentsMargins(12, 12, 12, 12)
        materials_layout.setSpacing(8)
        self._materials_title = QLabel("物料表：尚未初始化")
        self._materials_title.setObjectName("Title")
        materials_layout.addWidget(self._materials_title)

        stations = list(motion_cfg.iter_indexing_stations())
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self._material_code_labels = {}
        for index, station in enumerate(stations):
            # 左右分栏后物料表较窄：工位 1～4 / 5～8 两列
            col = 0 if index < 4 else 1
            row = index if index < 4 else index - 4
            name = QLabel(f"工位{station}")
            name.setObjectName("MaterialStation")
            code = QLabel("—")
            code.setObjectName("MaterialCode")
            code.setFixedHeight(_LIST_ROW_HEIGHT)
            code.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(6)
            cell_layout.addWidget(name)
            cell_layout.addWidget(code, 1)
            grid.addWidget(cell, row, col)
            self._material_code_labels[station] = code
        materials_layout.addLayout(grid)
        materials_layout.addStretch(1)

        dose_card = QFrame()
        dose_card.setObjectName("Card")
        dose_layout = QVBoxLayout(dose_card)
        dose_layout.setContentsMargins(12, 12, 12, 12)
        dose_layout.setSpacing(8)

        dose_head = QHBoxLayout()
        dose_title = QLabel("加料清单（重量单位 mg）")
        dose_title.setObjectName("Title")
        dose_head.addWidget(dose_title)
        dose_head.addStretch(1)
        self._dose_add_btn = QPushButton("添加")
        self._dose_add_btn.setMinimumWidth(72)
        self._dose_add_btn.clicked.connect(self._on_dose_add_row)
        self._dose_del_btn = QPushButton("删除")
        self._dose_del_btn.setMinimumWidth(72)
        self._dose_del_btn.clicked.connect(self._on_dose_del_row)
        dose_head.addWidget(self._dose_add_btn)
        dose_head.addWidget(self._dose_del_btn)
        dose_layout.addLayout(dose_head)

        self._dose_table = QTableWidget(0, 2)
        self._dose_table.setHorizontalHeaderLabels(["物料条码", "重量(mg)"])
        self._dose_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._dose_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._dose_table.horizontalHeader().setFixedHeight(_LIST_ROW_HEIGHT)
        self._dose_table.verticalHeader().setVisible(False)
        self._dose_table.verticalHeader().setDefaultSectionSize(_LIST_ROW_HEIGHT)
        self._dose_table.verticalHeader().setMinimumSectionSize(_LIST_ROW_HEIGHT)
        self._dose_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._dose_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._dose_table.setMinimumHeight(140)
        dose_layout.addWidget(self._dose_table, 1)
        self._append_dose_row("", "")

        mid_row = QHBoxLayout()
        mid_row.setContentsMargins(0, 0, 0, 0)
        mid_row.setSpacing(8)
        mid_row.addWidget(materials_card, 1)
        mid_row.addWidget(dose_card, 1)
        root.addLayout(mid_row, 1)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(_AUTO_BTN_SPACING)

        actions = (
            ("设备初始化", system_run_device_init),
            ("使能", system_run_servo_on_all),
            ("回基准点", system_run_go_datum),
            ("回原点", system_run_go_origin),
            ("物料初始化", system_run_initialize),
            ("加料", system_run_dose),
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
        self._refresh_materials_table(st)

    def _refresh_materials_table(self, st) -> None:
        stations = list(motion_cfg.iter_indexing_stations())
        has_map = bool(st.station_materials)
        if self._materials_title is not None:
            if st.materials_ok:
                filled = sum(
                    1
                    for s in stations
                    if (st.station_materials.get(s) or "").strip()
                )
                self._materials_title.setText(
                    f"物料表：已初始化（有码 {filled}/{len(stations)}）"
                )
            elif has_map and st.is_busy:
                self._materials_title.setText("物料表：初始化中…")
            elif has_map:
                self._materials_title.setText("物料表：未完成 / 已作废")
            else:
                self._materials_title.setText("物料表：尚未初始化")
        for station, label in self._material_code_labels.items():
            code = ""
            if has_map:
                code = (st.station_materials.get(station) or "").strip()
            label.setText(code if code else "—")

    def _set_controls_for_idle(self, idle: bool) -> None:
        for name, btn in self._action_buttons.items():
            if name == "停止":
                btn.setEnabled(not idle)
            else:
                btn.setEnabled(idle)
        if self._dose_table is not None:
            self._dose_table.setEnabled(idle)
        if self._dose_add_btn is not None:
            self._dose_add_btn.setEnabled(idle)
        if self._dose_del_btn is not None:
            self._dose_del_btn.setEnabled(idle)

    def _append_dose_row(self, material_id: str = "", weight_text: str = "") -> None:
        if self._dose_table is None:
            return
        row = self._dose_table.rowCount()
        self._dose_table.insertRow(row)
        self._dose_table.setRowHeight(row, _LIST_ROW_HEIGHT)
        self._dose_table.setItem(row, 0, QTableWidgetItem(material_id))
        self._dose_table.setItem(row, 1, QTableWidgetItem(weight_text))

    def _load_dose_table(self, items: List[DoseItem]) -> None:
        if self._dose_table is None:
            return
        self._dose_table.setRowCount(0)
        if not items:
            self._append_dose_row("", "")
            return
        for it in items:
            w = "" if float(it.weight_mg or 0.0) <= 0 else f"{it.weight_mg:g}"
            self._append_dose_row((it.material_id or "").strip(), w)

    def _on_dose_add_row(self) -> None:
        self._append_dose_row("", "")

    def _on_dose_del_row(self) -> None:
        if self._dose_table is None:
            return
        row = self._dose_table.currentRow()
        if row < 0:
            row = self._dose_table.rowCount() - 1
        if row < 0:
            return
        self._dose_table.removeRow(row)
        if self._dose_table.rowCount() == 0:
            self._append_dose_row("", "")

    def _sync_dose_params(self) -> None:
        if self._ctx is None or self._dose_table is None:
            return
        items: List[DoseItem] = []
        for row in range(self._dose_table.rowCount()):
            code_item = self._dose_table.item(row, 0)
            weight_item = self._dose_table.item(row, 1)
            code = (code_item.text() if code_item is not None else "").strip()
            weight_text = (
                weight_item.text() if weight_item is not None else ""
            ).strip()
            if not code and not weight_text:
                continue
            try:
                weight = float(weight_text) if weight_text else 0.0
            except ValueError:
                weight = 0.0
            items.append(DoseItem(material_id=code, weight_mg=weight))
        self._ctx.system.dose_items = items

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
        prefix = "成功" if ok else "失败"
        text = f"日志：{prefix} · {action_name} · {msg}"
        if self._log_label is not None:
            self._log_label.setText(text)
        if self._action_log_handler is not None:
            self._action_log_handler(text)
