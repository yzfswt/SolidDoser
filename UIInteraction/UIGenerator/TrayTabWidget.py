"""料盘设置标签页：32 仓位有料/物料类型配置。"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from Common.TrayGeometry import (
    MaterialType,
    TRAY_A_SLOT_MAX,
    TRAY_A_SLOT_MIN,
    TRAY_B_SLOT_MAX,
    TRAY_B_SLOT_MIN,
    TRAY_A_ORIGIN_X,
    TRAY_A_ORIGIN_Y,
    TRAY_A_ORIGIN_Z,
    TRAY_B_ORIGIN_X,
    TRAY_B_ORIGIN_Y,
    TRAY_B_ORIGIN_Z,
    SLOT_SPACING_X,
    SLOT_SPACING_Y,
    calc_slot_coord,
)
from UIInteraction.ParameterManagement.TrayModel import TrayModel


class _SlotCell(QWidget):
    """单个仓位控件。"""

    def __init__(self, slot_id: int, on_changed, on_select, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self._on_changed = on_changed
        self._on_select = on_select
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.label_id = QLabel(f"#{slot_id}")
        self.label_id.setAlignment(Qt.AlignCenter)
        self.label_id.setStyleSheet("font-weight: bold;")

        self.chk_has = QCheckBox("有料")
        self.combo_type = QComboBox()
        self.combo_type.addItems(["固体", "液体"])

        layout.addWidget(self.label_id)
        layout.addWidget(self.chk_has)
        layout.addWidget(self.combo_type)

        self.chk_has.stateChanged.connect(self._emit_change)
        self.combo_type.currentIndexChanged.connect(self._emit_change)

        self._apply_style(empty=True)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._on_select(self.slot_id)

    def _emit_change(self, *_args) -> None:
        if self._syncing:
            return
        has = self.chk_has.isChecked()
        mt = (
            MaterialType.from_label(self.combo_type.currentText())
            if has
            else MaterialType.NONE
        )
        self._apply_style(empty=not has, material_type=mt)
        self._on_changed(self.slot_id, has, mt)

    def _apply_style(
        self,
        empty: bool,
        material_type: MaterialType = MaterialType.NONE,
    ) -> None:
        if empty:
            bg, border = "#f5f5f5", "#cccccc"
        elif material_type == MaterialType.LIQUID:
            bg, border = "#e3f2fd", "#1976d2"
        else:
            bg, border = "#fff3e0", "#ef6c00"
        self.setStyleSheet(
            f"_SlotCell {{ background-color: {bg}; border: 1px solid {border}; border-radius: 4px; }}"
        )
        self.combo_type.setEnabled(not empty)

    def load_state(self, has_material: bool, material_type: MaterialType) -> None:
        self._syncing = True
        self.chk_has.setChecked(has_material)
        if material_type == MaterialType.LIQUID:
            self.combo_type.setCurrentText("液体")
        else:
            self.combo_type.setCurrentText("固体")
        self._apply_style(
            empty=not has_material,
            material_type=material_type if has_material else MaterialType.NONE,
        )
        self._syncing = False


class TrayTabWidget(QWidget):
    """料盘 A / B 双 4×4 矩阵配置界面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray_model: Optional[TrayModel] = None
        self._cells: Dict[int, _SlotCell] = {}
        self._info_label: Optional[QLabel] = None
        self._build_ui()

    def bind_tray_model(self, tray_model: TrayModel) -> None:
        self._tray_model = tray_model
        for slot_id, cell in self._cells.items():
            s = tray_model.get_slot(slot_id)
            cell.load_state(s.has_material, s.effective_material_type())
        self._update_summary()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        hint = QLabel(
            "料盘 A：仓位 1–16，原点 (0, 0, 0)；"
            "料盘 B：仓位 17–32，原点 (500, 500, 500)；"
            f"间距 {SLOT_SPACING_X:g}×{SLOT_SPACING_Y:g} mm（行优先 4×4）。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 14px;")
        root.addWidget(hint)

        trays_row = QHBoxLayout()
        trays_row.addWidget(self._build_tray_group("料盘 A", TRAY_A_SLOT_MIN, TRAY_A_SLOT_MAX))
        trays_row.addWidget(self._build_tray_group("料盘 B", TRAY_B_SLOT_MIN, TRAY_B_SLOT_MAX))
        root.addLayout(trays_row)

        self._info_label = QLabel("请点击仓位查看坐标；勾选「有料」并选择固体/液体。")
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(
            "font-size: 14px; padding: 8px; background: #fafafa; border: 1px solid #e0e0e0;"
        )
        root.addWidget(self._info_label)

        origin = QLabel(
            f"A 原点: ({TRAY_A_ORIGIN_X:g}, {TRAY_A_ORIGIN_Y:g}, {TRAY_A_ORIGIN_Z:g})  |  "
            f"B 原点: ({TRAY_B_ORIGIN_X:g}, {TRAY_B_ORIGIN_Y:g}, {TRAY_B_ORIGIN_Z:g})"
        )
        origin.setStyleSheet("font-size: 13px; color: #666;")
        root.addWidget(origin)

    def _build_tray_group(self, title: str, slot_min: int, slot_max: int) -> QGroupBox:
        group = QGroupBox(title)
        grid = QGridLayout(group)
        grid.setSpacing(6)

        slot_id = slot_min
        for row in range(4):
            for col in range(4):
                cell = _SlotCell(
                    slot_id, self._on_slot_changed, self._show_slot_info
                )
                self._cells[slot_id] = cell
                grid.addWidget(cell, row, col)
                slot_id += 1
        return group

    def _on_slot_changed(
        self, slot_id: int, has_material: bool, material_type: MaterialType
    ) -> None:
        if self._tray_model is not None:
            self._tray_model.set_slot(slot_id, has_material, material_type)
        self._show_slot_info(slot_id)
        self._update_summary()

    def _show_slot_info(self, slot_id: int) -> None:
        c = calc_slot_coord(slot_id)
        if self._tray_model is None:
            mat = "—"
            has = False
        else:
            s = self._tray_model.get_slot(slot_id)
            has = s.has_material
            mat = s.effective_material_type().to_label()

        self._info_label.setText(
            f"仓位 #{slot_id}（料盘 {c.tray_part}，行 {c.row + 1} 列 {c.col + 1}）  "
            f"坐标 X={c.x:g}, Y={c.y:g}, Z={c.z:g}  |  "
            f"有料: {'是' if has else '否'}  类型: {mat}"
        )

    def _update_summary(self) -> None:
        if self._tray_model is None:
            return
        n = self._tray_model.occupied_count()
        solids = sum(
            1
            for s in self._tray_model.slots.values()
            if s.has_material and s.material_type == MaterialType.SOLID
        )
        liquids = sum(
            1
            for s in self._tray_model.slots.values()
            if s.has_material and s.material_type == MaterialType.LIQUID
        )
        # 保留 info 行首的选中信息，仅在无选中时更新统计——此处简化为追加统计到窗口标题区不可用，用 tooltip
        self.setToolTip(f"已占位: {n}/32（固体 {solids}，液体 {liquids}）")
