from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont

from Common.ActionLogger import get_action_logger

_APP_STYLE = """
QMainWindow {
    background: #f8fafc;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
    top: -1px;
}
QTabBar::tab {
                        font-size: 14px;
    padding: 8px 20px;
    margin-right: 4px;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    background: #eef2f7;
    color: #475569;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
    font-weight: 600;
}
                    QPushButton {
    font-size: 13px;
    padding: 8px 16px;
    min-height: 32px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #ffffff;
    color: #334155;
                    }
                    QPushButton:hover {
    background: #f1f5f9;
}
QPushButton#PrimaryAction {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#PrimaryAction:hover {
    background: #1d4ed8;
}
QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
}
QFrame#Divider {
    color: #e2e8f0;
}
                    QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
                        text-align: center;
    background: #ffffff;
    min-height: 22px;
    font-size: 12px;
                    }
                    QProgressBar::chunk {
    background: #2563eb;
                        border-radius: 5px;
}
QTableWidget {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #eef2f7;
    background: #ffffff;
    font-size: 12px;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #1e3a8a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #64748b;
    font-weight: 600;
    font-size: 12px;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
}
"""


class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.solid_doser_motion_debug_tab_widget = None
        self.setMinimumSize(980, 800)
        self.resize(1040, 880)
        self.init_ui()

    def closeEvent(self, event: QCloseEvent):
        super().closeEvent(event)
        get_action_logger().persist()

    def init_ui(self):
        self.setStyleSheet(_APP_STYLE)
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        tabs = QTabWidget()

        tab_titles = ["流程导入", "调试"]
        for idx, title in enumerate(tab_titles):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(10)
            if idx == 0:
                self._build_process_tab(layout)
            elif idx == 1:
                from UIInteraction.UIGenerator.SolidDoserMotionDebugTabWidget import (
                    SolidDoserMotionDebugTabWidget,
                )

                self.solid_doser_motion_debug_tab_widget = SolidDoserMotionDebugTabWidget()
                layout.addWidget(self.solid_doser_motion_debug_tab_widget)
            tabs.addTab(tab, title)

        root_layout.addWidget(tabs)
        self.setCentralWidget(central)

    def _build_process_tab(self, layout: QVBoxLayout) -> None:
        title = QLabel("工艺流程")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.btn_import_process = QPushButton("导入工艺文件")
        self.btn_execute_process = QPushButton("执行工艺流程")
        self.btn_execute_process.setObjectName("PrimaryAction")
        button_layout.addWidget(self.btn_import_process)
        button_layout.addWidget(self.btn_execute_process)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

                separator = QFrame()
        separator.setObjectName("Divider")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        layout.addWidget(separator)

        self.table_process = QTableWidget(0, 2)
        self.table_process.setHorizontalHeaderLabels(["函数名", "参数"])
        self.table_process.setColumnWidth(0, 180)
        self.table_process.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_process.verticalHeader().setDefaultSectionSize(32)
        self.table_process.verticalHeader().setVisible(False)
        self.table_process.setFont(QFont("Microsoft YaHei UI", 10))
        self.table_process.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_process.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_process.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_process.setAlternatingRowColors(True)
        layout.addWidget(self.table_process, 1)

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(12)
        self.label_progress = QLabel("执行进度: 0/0")
        self.label_progress.setStyleSheet("font-size: 12px; color: #475569;")
        self.progress_bar = QProgressBar()
        self.label_time = QLabel("总耗时: 00:00:00")
        self.label_time.setStyleSheet("font-size: 12px; color: #64748b;")
        progress_layout.addWidget(self.label_progress)
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.label_time)
        layout.addLayout(progress_layout)

    def bind_solid_doser_motion_debug(self, param_storage) -> None:
        if self.solid_doser_motion_debug_tab_widget is not None:
            self.solid_doser_motion_debug_tab_widget.bind_parameter_storage(param_storage)
