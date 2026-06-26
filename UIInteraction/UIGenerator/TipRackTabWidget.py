"""枪头架设置标签页：操作员勾选各位置有无枪头。"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Common.TipRackGeometry import (
    GRID_COLS,
    GRID_ROWS,
    RACK_A_ORIGIN_X,
    RACK_A_ORIGIN_Y,
    RACK_A_ORIGIN_Z,
    RACK_A_TIP_MAX,
    RACK_A_TIP_MIN,
    RACK_B_ORIGIN_X,
    RACK_B_ORIGIN_Y,
    RACK_B_ORIGIN_Z,
    RACK_B_TIP_MAX,
    RACK_B_TIP_MIN,
    TIP_SPACING_X,
    TIP_SPACING_Y,
    calc_tip_coord,
)
from UIInteraction.ParameterManagement.TipRackModel import TipRackModel


class _TipCell(QWidget):
    """单个枪头位：勾选表示有枪头，不勾表示无枪头。"""

    def __init__(self, tip_id: int, on_changed, on_select, parent=None):
        super().__init__(parent)
        self.tip_id = tip_id
        self._on_changed = on_changed
        self._on_select = on_select
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.label_id = QLabel(f"#{tip_id}")
        self.label_id.setAlignment(Qt.AlignCenter)
        self.label_id.setStyleSheet("font-weight: bold;")

        self.chk_has = QCheckBox("有枪头")
        self.chk_has.setToolTip("勾选：该位有枪头；不勾选：该位无枪头")

        layout.addWidget(self.label_id)
        layout.addWidget(self.chk_has)

        self.chk_has.stateChanged.connect(self._emit_change)
        self._apply_style(has_tip=False)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._on_select(self.tip_id)

    def _emit_change(self, *_args) -> None:
        if self._syncing:
            return
        has = self.chk_has.isChecked()
        self._apply_style(has_tip=has)
        self._on_changed(self.tip_id, has)

    def _apply_style(self, has_tip: bool) -> None:
        if has_tip:
            bg, border = "#e8f5e9", "#2e7d32"
        else:
            bg, border = "#ffebee", "#c62828"
        self.setStyleSheet(
            f"_TipCell {{ background-color: {bg}; border: 1px solid {border}; border-radius: 4px; }}"
        )

    def load_state(self, has_tip: bool) -> None:
        self._syncing = True
        self.chk_has.setChecked(has_tip)
        self._apply_style(has_tip=has_tip)
        self._syncing = False


class TipRackTabWidget(QWidget):
    """枪头架 A / B，各 4×7；操作员逐格勾选有无枪头。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: Optional[TipRackModel] = None
        self._cells: Dict[int, _TipCell] = {}
        self._info_label: Optional[QLabel] = None
        self._summary_label: Optional[QLabel] = None
        self._build_ui()

    def bind_tip_rack_model(self, model: TipRackModel) -> None:
        self._model = model
        for tip_id, cell in self._cells.items():
            cell.load_state(model.get_slot(tip_id).has_tip)
        self._update_summary()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        hint = QLabel(
            "请为每个枪头位勾选是否有枪头：勾选「有枪头」= 有，不勾选 = 无。"
            "枪头架 A 位 1–28，原点 (200,200,200)；B 位 29–56，原点 (400,400,400)；"
            f"间距 {TIP_SPACING_X:g}×{TIP_SPACING_Y:g} mm。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 14px;")
        root.addWidget(hint)

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("批量设置："))
        btn_all_on = QPushButton("全部有枪头")
        btn_all_off = QPushButton("全部无枪头")
        btn_a_on = QPushButton("A 架全部有")
        btn_a_off = QPushButton("A 架全部无")
        btn_b_on = QPushButton("B 架全部有")
        btn_b_off = QPushButton("B 架全部无")
        btn_all_on.clicked.connect(lambda: self._set_all(True))
        btn_all_off.clicked.connect(lambda: self._set_all(False))
        btn_a_on.clicked.connect(
            lambda: self._set_range(RACK_A_TIP_MIN, RACK_A_TIP_MAX, True)
        )
        btn_a_off.clicked.connect(
            lambda: self._set_range(RACK_A_TIP_MIN, RACK_A_TIP_MAX, False)
        )
        btn_b_on.clicked.connect(
            lambda: self._set_range(RACK_B_TIP_MIN, RACK_B_TIP_MAX, True)
        )
        btn_b_off.clicked.connect(
            lambda: self._set_range(RACK_B_TIP_MIN, RACK_B_TIP_MAX, False)
        )
        for btn in (
            btn_all_on, btn_all_off, btn_a_on, btn_a_off, btn_b_on, btn_b_off
        ):
            batch_row.addWidget(btn)
        batch_row.addStretch()
        root.addLayout(batch_row)

        self._summary_label = QLabel("统计：有枪头 0 / 56，无枪头 56 / 56")
        self._summary_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(self._summary_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)
        scroll_layout.addWidget(
            self._build_rack_group("枪头架 A", RACK_A_TIP_MIN, RACK_A_TIP_MAX)
        )
        scroll_layout.addWidget(
            self._build_rack_group("枪头架 B", RACK_B_TIP_MIN, RACK_B_TIP_MAX)
        )
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        self._info_label = QLabel("点击某一格可查看该位坐标与有无枪头状态。")
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(
            "font-size: 14px; padding: 8px; background: #fafafa; border: 1px solid #e0e0e0;"
        )
        root.addWidget(self._info_label)

        legend = QLabel(
            "■ 绿色 = 有枪头　■ 浅红 = 无枪头　|　"
            f"A 原点 ({RACK_A_ORIGIN_X:g}, {RACK_A_ORIGIN_Y:g}, {RACK_A_ORIGIN_Z:g})　"
            f"B 原点 ({RACK_B_ORIGIN_X:g}, {RACK_B_ORIGIN_Y:g}, {RACK_B_ORIGIN_Z:g})"
        )
        legend.setStyleSheet("font-size: 13px; color: #666;")
        root.addWidget(legend)

    def _build_rack_group(self, title: str, tip_min: int, tip_max: int) -> QGroupBox:
        group = QGroupBox(title)
        outer = QVBoxLayout(group)

        col_headers = QHBoxLayout()
        col_headers.addSpacing(36)
        for c in range(GRID_COLS):
            lbl = QLabel(f"X{c + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 12px; color: #888;")
            col_headers.addWidget(lbl, 1)
        outer.addLayout(col_headers)

        body = QGridLayout()
        body.setSpacing(6)
        tip_id = tip_min
        for row in range(GRID_ROWS):
            row_lbl = QLabel(f"Y{row + 1}")
            row_lbl.setStyleSheet("font-size: 12px; color: #888;")
            body.addWidget(row_lbl, row, 0)
            for col in range(GRID_COLS):
                cell = _TipCell(tip_id, self._on_tip_changed, self._show_tip_info)
                self._cells[tip_id] = cell
                body.addWidget(cell, row, col + 1)
                tip_id += 1
        outer.addLayout(body)
        return group

    def _set_all(self, has_tip: bool) -> None:
        self._set_range(RACK_A_TIP_MIN, RACK_B_TIP_MAX, has_tip)

    def _set_range(self, tip_min: int, tip_max: int, has_tip: bool) -> None:
        if self._model is not None:
            self._model.set_range_has_tip(tip_min, tip_max, has_tip)
        for tip_id in range(tip_min, tip_max + 1):
            if tip_id in self._cells:
                self._cells[tip_id].load_state(has_tip)
        self._update_summary()

    def _on_tip_changed(self, tip_id: int, has_tip: bool) -> None:
        if self._model is not None:
            self._model.set_has_tip(tip_id, has_tip)
        self._show_tip_info(tip_id)
        self._update_summary()

    def _show_tip_info(self, tip_id: int) -> None:
        c = calc_tip_coord(tip_id)
        has = (
            self._model.get_slot(tip_id).has_tip
            if self._model is not None
            else False
        )
        status = "有枪头" if has else "无枪头"

        self._info_label.setText(
            f"枪头位 #{tip_id}（架 {c.rack_part}，Y{c.row + 1} × X{c.col + 1}）  "
            f"坐标 X={c.x:g}, Y={c.y:g}, Z={c.z:g}  |  状态：{status}"
        )

    def _update_summary(self) -> None:
        if self._model is None:
            return
        with_tip = self._model.available_count()
        without = 56 - with_tip
        self._summary_label.setText(
            f"统计：有枪头 {with_tip} / 56，无枪头 {without} / 56"
        )
        self.setToolTip(self._summary_label.text())
