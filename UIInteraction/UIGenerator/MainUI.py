from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLineEdit, QProgressBar, QFrame, QScrollArea, QGridLayout, QGroupBox, QTextEdit, QSizePolicy, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, QRegularExpression, QObject, QEvent, Signal, QTimer, QThread
from PySide6.QtGui import QIntValidator, QDoubleValidator, QRegularExpressionValidator, QFont, QCloseEvent
from Common.ActionLogger import get_action_logger
from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QProgressBar, QFrame, QWidget, QGroupBox, QGridLayout
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 定义溶液变量
        self.solution_a = "溶液A"
        self.solution_b = "溶液B"
        self.solution_c = "溶液C"
        self.solution_d = "溶液D"
        #定义后处理溶液变量
        self.inject_solution_a = "反应液(3→4)"
        self.inject_solution_b = "良溶剂(2→4)"
        self.inject_solution_c = "不良溶剂(1→4)"

        self.init_ui()

    def closeEvent(self, event: QCloseEvent):
        super().closeEvent(event)
        get_action_logger().persist()

    def init_ui(self):
        tab_widget = QTabWidget(self)
        tab_widget.setGeometry(0, 0, 400, 200)
        # 设置全局字体大小
        tab_widget.setStyleSheet("QWidget { font-size: 20px; }")
        tab_titles = [
            '指定模块设置', '后处理模块设置', '三轴位置标定', '自动化程序',
            '工艺流程导入', '测试界面', '料盘设置', '枪头架设置', '机器人调试',
            '清洁工位调试',
        ]
        self.tray_tab_widget = None
        self.tip_rack_tab_widget = None
        self.robot_debug_tab_widget = None
        self.cleaning_station_debug_tab_widget = None
        for idx, title in enumerate(tab_titles):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            if idx == 4:
                # 工艺流程导入标签页
                # 顶部按钮布局
                button_layout = QHBoxLayout()
                self.btn_import_process = QPushButton('导入工艺文件')
                self.btn_execute_process = QPushButton('执行工艺流程')
                # 设置按钮样式和大小
                button_layout.addWidget(self.btn_import_process)
                button_layout.addWidget(self.btn_execute_process)
                layout.addLayout(button_layout)
                
                # 添加分隔线
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameStyle(QFrame.HLine | QFrame.Sunken)
                layout.addWidget(separator)
                
                # 中间列表区域
                list_label = QLabel('工艺步骤列表')
                list_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(list_label)
                
                # 创建滚动区域来放置步骤列表
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                # 增加滚动区域的最小高度
                scroll_area.setMinimumHeight(600)
                
                steps_container = QWidget()
                self.steps_layout = QVBoxLayout(steps_container)
                # 创建空的表格，等待导入工艺数据
                self.table_process = QTableWidget(0, 2)  # 0行2列的空表
                self.table_process.setHorizontalHeaderLabels(['函数名', '参数'])
                
                # 设置表格的列宽
                self.table_process.setColumnWidth(0, 200)  # 函数名列宽度
                self.table_process.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 参数列自动伸展
                
                # 设置表格的行高
                self.table_process.verticalHeader().setDefaultSectionSize(40)
                
                # 设置表格字体
                self.table_process.setFont(QFont("SimSun", 12))
                
                # 设置表格样式
                self.table_process.setStyleSheet("""
                    QTableWidget {
                        border: 1px solid #d0d0d0;
                        border-radius: 5px;
                        gridline-color: #e0e0e0;
                    }
                    QTableWidget::header {
                        background-color: #f5f5f5;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QTableWidget::item {
                        padding: 5px;
                    }
                    QTableWidget::item:selected {
                        background-color: #4a90e2;
                        color: white;
                    }
                """)
                
                # 设置表格的编辑模式和选择模式
                self.table_process.setEditTriggers(QAbstractItemView.NoEditTriggers)
                self.table_process.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table_process.setSelectionMode(QAbstractItemView.SingleSelection)
                
                # 添加表格到布局
                self.steps_layout.addWidget(self.table_process)
                
                # 设置滚动区域
                scroll_area.setWidget(steps_container)
                layout.addWidget(scroll_area, 1)  # 1表示伸展因子
                
                # 添加分隔线
                separator2 = QFrame()
                separator2.setFrameShape(QFrame.HLine)
                separator2.setFrameStyle(QFrame.HLine | QFrame.Sunken)
                layout.addWidget(separator2)
                
                # 底部进度条和状态信息
                progress_layout = QVBoxLayout()
                
                # 进度条
                progress_info_layout = QHBoxLayout()
                self.label_progress = QLabel('执行进度: 0/0')
                self.progress_bar = QProgressBar()
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                progress_info_layout.addWidget(self.label_progress)
                progress_info_layout.addWidget(self.progress_bar, 1)
                
                # 耗时信息
                time_info_layout = QHBoxLayout()
                self.label_time = QLabel('总耗时: 00:00:00')
                time_info_layout.addWidget(self.label_time)
                
                progress_layout.addLayout(progress_info_layout)
                progress_layout.addLayout(time_info_layout)
                layout.addLayout(progress_layout)
            elif idx == 5:
                # 测试界面标签页
                # 创建一个主水平布局来放置四列
                main_horizontal_layout = QHBoxLayout()
                
                # 设置统一的按钮样式
                button_style = """
                    QPushButton {
                        background-color: #f0f0f0;
                        border: 1px solid #c0c0c0;
                        border-radius: 0px;
                        font-size: 20px;
                        padding: 10px;
                        min-width: 80px;
                        min-height: 40px;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                    QPushButton:pressed {
                        background-color: #d0d0d0;
                    }
                """
                
                # 第一列：抓取加液头 (5个按钮：A/B/C/D/E)
                col1_layout = QVBoxLayout()
                col1_label = QLabel('抓取加液头')
                col1_label.setAlignment(Qt.AlignCenter)
                col1_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col1_layout.addWidget(col1_label)
                
                # 创建抓取加液头按钮
                self.btn_grab_a = QPushButton('A')
                self.btn_grab_b = QPushButton('B')
                self.btn_grab_c = QPushButton('C')
                self.btn_grab_d = QPushButton('D')
                self.btn_grab_e = QPushButton('E')
                
                # 应用样式并添加按钮
                for btn in [self.btn_grab_a, self.btn_grab_b, 
                           self.btn_grab_c, self.btn_grab_d, 
                           self.btn_grab_e]:
                    btn.setStyleSheet(button_style)
                    col1_layout.addWidget(btn)
                    col1_layout.addSpacing(5)  # 添加间距
                
                # 第二列：反应器点位 (4个按钮：1/2/3/4)
                col2_layout = QVBoxLayout()
                col2_label = QLabel('反应器点位')
                col2_label.setAlignment(Qt.AlignCenter)
                col2_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col2_layout.addWidget(col2_label)
                
                # 创建反应器点位按钮
                self.btn_reactor_1 = QPushButton('1')
                self.btn_reactor_2 = QPushButton('2')
                self.btn_reactor_3 = QPushButton('3')
                self.btn_reactor_4 = QPushButton('4')
                self.btn_reactor_5 = QPushButton('5')
                self.btn_reactor_6 = QPushButton('6')
                self.btn_reactor_7 = QPushButton('7')
                self.btn_reactor_8 = QPushButton('8')
                
                # 应用样式并添加按钮
                for btn in [self.btn_reactor_1, self.btn_reactor_2, 
                           self.btn_reactor_3, self.btn_reactor_4,
                           self.btn_reactor_5, self.btn_reactor_6,
                           self.btn_reactor_7, self.btn_reactor_8]:
                    btn.setStyleSheet(button_style)
                    col2_layout.addWidget(btn)
                    col2_layout.addSpacing(5)  # 添加间距
                
                # 第三列：夹爪控制 (3个按钮：初始化/夹取/松开)
                col3_layout = QVBoxLayout()
                col3_label = QLabel('夹爪控制')
                col3_label.setAlignment(Qt.AlignCenter)
                col3_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col3_layout.addWidget(col3_label)
                
                # 创建夹爪控制按钮
                self.btn_init_claw = QPushButton('初始化')
                self.btn_grip_claw = QPushButton('夹取')
                self.btn_release_claw = QPushButton('松开')
                
                # 为夹爪控制按钮设置不同的背景色
                init_style = button_style.replace("background-color: #f0f0f0;", "background-color: #2196f3;")
                init_style = init_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #1976d2;")
                init_style = init_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #1976d2;")
                init_style = init_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #1565c0;")
                
                grip_style = button_style.replace("background-color: #f0f0f0;", "background-color: #4caf50;")
                grip_style = grip_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #388e3c;")
                grip_style = grip_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #388e3c;")
                grip_style = grip_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #2e7d32;")
                
                release_style = button_style.replace("background-color: #f0f0f0;", "background-color: #f44336;")
                release_style = release_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #d32f2f;")
                release_style = release_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #d32f2f;")
                release_style = release_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #b71c1c;")
                
                # 应用样式并添加按钮
                self.btn_init_claw.setStyleSheet(init_style)
                self.btn_grip_claw.setStyleSheet(grip_style)
                self.btn_release_claw.setStyleSheet(release_style)
                
                col3_layout.addWidget(self.btn_init_claw)
                col3_layout.addSpacing(5)
                col3_layout.addWidget(self.btn_grip_claw)
                col3_layout.addSpacing(5)
                col3_layout.addWidget(self.btn_release_claw)
                
                # 第四列：加液泵控制 (加液/复位按钮，带浮点数输入框和A-E下拉框)
                col4_layout = QVBoxLayout()
                col4_label = QLabel('加液泵控制')
                col4_label.setAlignment(Qt.AlignCenter)
                col4_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col4_layout.addWidget(col4_label)
                
                # 加液量输入
                dosage_layout = QHBoxLayout()
                dosage_label = QLabel('加液量(ml):')
                dosage_label.setMinimumWidth(100)
                self.line_dosage = QLineEdit()
                self.line_dosage.setStyleSheet("font-size: 20px; padding: 5px;")
                dosage_layout.addWidget(dosage_label)
                dosage_layout.addWidget(self.line_dosage)
                col4_layout.addLayout(dosage_layout)
                col4_layout.addSpacing(5)
                
                # 选择加液头
                head_layout = QHBoxLayout()
                head_label = QLabel('选择加液头:')
                head_label.setMinimumWidth(100)
                self.combo_select_head = QComboBox()
                self.combo_select_head.addItems(['1', '2', '3', '4', '5'])
                self.combo_select_head.setStyleSheet("font-size: 20px; padding: 5px;")
                head_layout.addWidget(head_label)
                head_layout.addWidget(self.combo_select_head)
                col4_layout.addLayout(head_layout)
                col4_layout.addSpacing(10)
                
                # 加液和复位按钮
                pump_buttons_layout = QVBoxLayout()
                self.btn_add_liquid = QPushButton('加液')
                self.btn_reset_pump = QPushButton('复位')
                
                # 为加液和复位按钮设置不同的背景色
                add_style = button_style.replace("background-color: #f0f0f0;", "background-color: #00bcd4;")
                add_style = add_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #00acc1;")
                add_style = add_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #00acc1;")
                add_style = add_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #0097a7;")
                
                reset_style = button_style.replace("background-color: #f0f0f0;", "background-color: #ff9800;")
                reset_style = reset_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #f57c00;")
                reset_style = reset_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #f57c00;")
                reset_style = reset_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #ef6c00;")
                
                self.btn_add_liquid.setStyleSheet(add_style)
                self.btn_reset_pump.setStyleSheet(reset_style)
                
                pump_buttons_layout.addWidget(self.btn_add_liquid)
                pump_buttons_layout.addSpacing(5)
                pump_buttons_layout.addWidget(self.btn_reset_pump)
                col4_layout.addLayout(pump_buttons_layout)
                
                # 第五列：轴控制 (3个按钮：轴上电/轴回原点/轴复位)
                col5_layout = QVBoxLayout()
                col5_label = QLabel('轴控制')
                col5_label.setAlignment(Qt.AlignCenter)
                col5_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col5_layout.addWidget(col5_label)
                
                # 创建轴控制按钮
                self.btn_axis_power_on = QPushButton('轴上电')
                self.btn_axis_home = QPushButton('轴回原点')
                self.btn_axis_reset = QPushButton('轴复位')
                
                # 为轴控制按钮设置不同的背景色
                power_style = button_style.replace("background-color: #f0f0f0;", "background-color: #9c27b0;")
                power_style = power_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #7b1fa2;")
                power_style = power_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #7b1fa2;")
                power_style = power_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #6a1b9a;")
                
                home_style = button_style.replace("background-color: #f0f0f0;", "background-color: #ff9800;")
                home_style = home_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #f57c00;")
                home_style = home_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #f57c00;")
                home_style = home_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #ef6c00;")
                
                reset_style = button_style.replace("background-color: #f0f0f0;", "background-color: #ff5722;")
                reset_style = reset_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #e64a19;")
                reset_style = reset_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #e64a19;")
                reset_style = reset_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #d84315;")
                
                # 应用样式并添加按钮
                self.btn_axis_power_on.setStyleSheet(power_style)
                self.btn_axis_home.setStyleSheet(home_style)
                self.btn_axis_reset.setStyleSheet(reset_style)
                
                col5_layout.addWidget(self.btn_axis_power_on)
                col5_layout.addSpacing(5)
                col5_layout.addWidget(self.btn_axis_home)
                col5_layout.addSpacing(5)
                col5_layout.addWidget(self.btn_axis_reset)
                
                # 第六列：反应器气阀控制 (8个按钮：反应器1-4 气阀开/关)
                col6_layout = QVBoxLayout()
                col6_label = QLabel('反应器气阀控制')
                col6_label.setAlignment(Qt.AlignCenter)
                col6_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                col6_layout.addWidget(col6_label)
                
                # 创建气阀控制的水平布局
                valve_layout = QHBoxLayout()
                
                # 气阀开子列
                valve_open_layout = QVBoxLayout()
                valve_open_label = QLabel('气阀开')
                valve_open_label.setAlignment(Qt.AlignCenter)
                valve_open_label.setStyleSheet("margin-bottom: 5px;")
                valve_open_layout.addWidget(valve_open_label)
                
                # 创建气阀开按钮
                self.btn_valve_open_1 = QPushButton('反应器1')
                self.btn_valve_open_2 = QPushButton('反应器2')
                self.btn_valve_open_3 = QPushButton('反应器3')
                self.btn_valve_open_4 = QPushButton('反应器4')
                self.btn_valve_open_5 = QPushButton('反应器5')
                self.btn_valve_open_6 = QPushButton('反应器6')
                self.btn_valve_open_7 = QPushButton('反应器7')
                self.btn_valve_open_8 = QPushButton('反应器8')
                
                # 气阀关子列
                valve_close_layout = QVBoxLayout()
                valve_close_label = QLabel('气阀关')
                valve_close_label.setAlignment(Qt.AlignCenter)
                valve_close_label.setStyleSheet("margin-bottom: 5px;")
                valve_close_layout.addWidget(valve_close_label)
                
                # 创建气阀关按钮
                self.btn_valve_close_1 = QPushButton('反应器1')
                self.btn_valve_close_2 = QPushButton('反应器2')
                self.btn_valve_close_3 = QPushButton('反应器3')
                self.btn_valve_close_4 = QPushButton('反应器4')
                self.btn_valve_close_5 = QPushButton('反应器5')
                self.btn_valve_close_6 = QPushButton('反应器6')
                self.btn_valve_close_7 = QPushButton('反应器7')
                self.btn_valve_close_8 = QPushButton('反应器8')
                
                # 为气阀开按钮设置绿色样式
                valve_open_style = button_style.replace("background-color: #f0f0f0;", "background-color: #4caf50;")
                valve_open_style = valve_open_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #388e3c;")
                valve_open_style = valve_open_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #388e3c;")
                valve_open_style = valve_open_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #2e7d32;")
                
                # 为气阀关按钮设置红色样式
                valve_close_style = button_style.replace("background-color: #f0f0f0;", "background-color: #f44336;")
                valve_close_style = valve_close_style.replace("border: 1px solid #c0c0c0;", "border: 1px solid #d32f2f;")
                valve_close_style = valve_close_style.replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #d32f2f;")
                valve_close_style = valve_close_style.replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #b71c1c;")
                
                # 应用样式并添加气阀开按钮
                for btn in [self.btn_valve_open_1, self.btn_valve_open_2, self.btn_valve_open_3, self.btn_valve_open_4,
                            self.btn_valve_open_5, self.btn_valve_open_6, self.btn_valve_open_7, self.btn_valve_open_8]:
                    btn.setStyleSheet(valve_open_style)
                    valve_open_layout.addWidget(btn)
                    valve_open_layout.addSpacing(5)
                
                # 应用样式并添加气阀关按钮
                for btn in [self.btn_valve_close_1, self.btn_valve_close_2, self.btn_valve_close_3, self.btn_valve_close_4,
                            self.btn_valve_close_5, self.btn_valve_close_6, self.btn_valve_close_7, self.btn_valve_close_8]:
                    btn.setStyleSheet(valve_close_style)
                    valve_close_layout.addWidget(btn)
                    valve_close_layout.addSpacing(5)
                
                # 将气阀开/关子列添加到气阀控制水平布局
                valve_layout.addLayout(valve_open_layout)
                valve_layout.addSpacing(10)
                valve_layout.addLayout(valve_close_layout)
                col6_layout.addLayout(valve_layout)
                
                # 将六列添加到主水平布局
                main_horizontal_layout.addLayout(col1_layout)
                main_horizontal_layout.addSpacing(20)
                main_horizontal_layout.addLayout(col2_layout)
                main_horizontal_layout.addSpacing(20)
                main_horizontal_layout.addLayout(col3_layout)
                main_horizontal_layout.addSpacing(20)
                main_horizontal_layout.addLayout(col4_layout)
                main_horizontal_layout.addSpacing(20)
                main_horizontal_layout.addLayout(col5_layout)
                main_horizontal_layout.addSpacing(20)
                main_horizontal_layout.addLayout(col6_layout)
                
                # 添加到主布局
                layout.addLayout(main_horizontal_layout)
                
                # 添加控制模式切换按钮
                layout.addSpacing(20)  # 添加间距
                mode_switch_layout = QHBoxLayout()
                mode_switch_layout.setAlignment(Qt.AlignCenter)
                
                self.label_control_mode = QLabel('控制模式:')
                self.label_control_mode.setStyleSheet("font-weight: bold; font-size: 20px;")
                
                self.btn_mode_switch = QPushButton('本地控制模式')
                self.btn_mode_switch.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-size: 20px;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                """)
                
                mode_switch_layout.addWidget(self.label_control_mode)
                mode_switch_layout.addWidget(self.btn_mode_switch)
                layout.addLayout(mode_switch_layout)
                
                # 添加多步动作、待机位置和仿真模式按钮
                layout.addSpacing(20)  # 添加间距
                action_buttons_layout = QHBoxLayout()
                
                # 测试多步动作按钮
                self.btn_test_multi_step = QPushButton('测试多步动作')
                self.btn_test_multi_step.setStyleSheet(button_style.replace("background-color: #f0f0f0;", "background-color: #795548;").replace("border: 1px solid #c0c0c0;", "border: 1px solid #5d4037;").replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #5d4037;").replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #4e342e;"))
                action_buttons_layout.addWidget(self.btn_test_multi_step)
                action_buttons_layout.addSpacing(20)
                
                # 回到待机位置按钮
                self.btn_return_standby = QPushButton('回到待机位置')
                self.btn_return_standby.setStyleSheet(button_style.replace("background-color: #f0f0f0;", "background-color: #3f51b5;").replace("border: 1px solid #c0c0c0;", "border: 1px solid #303f9f;").replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #303f9f;").replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #283593;"))
                action_buttons_layout.addWidget(self.btn_return_standby)
                action_buttons_layout.addSpacing(20)
                
                # 仿真模式按钮
                self.btn_simulation_mode = QPushButton('仿真模式: 关闭')
                self.btn_simulation_mode.setStyleSheet(button_style.replace("background-color: #f0f0f0;", "background-color: #ff9800;").replace("border: 1px solid #c0c0c0;", "border: 1px solid #f57c00;").replace("QPushButton:hover {\n                        background-color: #e0e0e0;", "QPushButton:hover {\n                        background-color: #f57c00;").replace("QPushButton:pressed {\n                        background-color: #d0d0d0;", "QPushButton:pressed {\n                        background-color: #ef6c00;"))
                action_buttons_layout.addWidget(self.btn_simulation_mode)
                
                # 设置按钮大小
                self.btn_test_multi_step.setMinimumWidth(150)
                self.btn_return_standby.setMinimumWidth(150)
                self.btn_simulation_mode.setMinimumWidth(150)
                
                # 将按钮布局添加到主布局
                layout.addLayout(action_buttons_layout)
                
                # 添加进度条
                layout.addSpacing(20)  # 添加间距
                progress_layout = QVBoxLayout()
                progress_label = QLabel('执行进度')
                progress_label.setAlignment(Qt.AlignCenter)
                progress_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
                progress_layout.addWidget(progress_label)
                
                self.test_progress_bar = QProgressBar()
                self.test_progress_bar.setRange(0, 100)
                self.test_progress_bar.setValue(0)
                self.test_progress_bar.setTextVisible(True)
                self.test_progress_bar.setStyleSheet(
                    """QProgressBar {
                        background-color: #f0f0f0;
                        border-radius: 10px;
                        text-align: center;
                        height: 25px;
                        font-size: 14px;
                        color: #333;
                    }
                    QProgressBar::chunk {
                        background-color: #4CAF50;
                        border-radius: 10px;
                    }"""
                )
                progress_layout.addWidget(self.test_progress_bar)
                layout.addLayout(progress_layout)
            elif idx == 0:
                # 指定模块设置tab，添加按钮和串口选择
                top_layout = QHBoxLayout()
                self.btn_connect = QPushButton('连接反应器装置')
                self.btn_disconnect = QPushButton('断开反应器装置')
                self.label_port = QLabel('串口选择')
                self.label_port.setAlignment(Qt.AlignCenter)
                self.combo_port = QComboBox()
                self.btn_refresh_port = QPushButton('刷新串口')
                top_layout.addWidget(self.btn_connect)
                top_layout.addWidget(self.btn_disconnect)
                top_layout.addWidget(self.label_port)
                top_layout.addWidget(self.combo_port)
                top_layout.addWidget(self.btn_refresh_port)
                layout.addLayout(top_layout)

                # 第二行：反应器模块选择和电机控制
                second_layout = QHBoxLayout()
                self.label_reactor = QLabel('反应器模块选择')
                self.label_reactor.setAlignment(Qt.AlignCenter)
                self.combo_reactor = QComboBox()
                # 添加1-25的模块选项
                for i in range(1, 26):
                    self.combo_reactor.addItem(f'{i}')
                self.btn_start_motor = QPushButton('启动电机搅拌/设置速度')
                self.btn_stop_motor = QPushButton('停止电机搅拌')

                second_layout.addWidget(self.label_reactor)
                second_layout.addWidget(self.combo_reactor)
                second_layout.addWidget(self.btn_start_motor)
                second_layout.addWidget(self.btn_stop_motor)
                layout.addLayout(second_layout)

                # 第三行：电机搅拌速度设置和温度设置合并为一行
                third_layout = QHBoxLayout()

                # 左侧：电机搅拌速度设置
                speed_group_layout = QHBoxLayout()
                self.label_speed = QLabel('电机搅拌速度设置')
                self.line_motor_speed = QLineEdit()
                # # 设置电机转速只允许正整数输入
                # speed_validator = QIntValidator(1, 99999)
                # self.line_speed.setValidator(speed_validator)
                self.label_rpm = QLabel('RPM')

                speed_group_layout.addWidget(self.label_speed)
                speed_group_layout.addWidget(self.line_motor_speed)
                speed_group_layout.addWidget(self.label_rpm)

                # 创建第一个竖直分隔线
                separator1 = QFrame()
                separator1.setFrameShape(QFrame.VLine)
                separator1.setFrameStyle(QFrame.VLine | QFrame.Sunken)
                separator1.setLineWidth(1)

                # 右侧：温度设置
                temp_group_layout = QHBoxLayout()
                self.btn_temp_set = QPushButton('温度设置')
                self.line_temp = QLineEdit()
                # 设置温度允许负数和浮点数输入
                # temp_validator = QDoubleValidator(-999.99, 999.99, 2)
                # self.line_temp.setValidator(temp_validator)
                self.label_celsius = QLabel('℃')

                temp_group_layout.addWidget(self.btn_temp_set)
                temp_group_layout.addWidget(self.line_temp)
                temp_group_layout.addWidget(self.label_celsius)

                # 将左右两组添加到主布局，设置相等的stretch因子使宽度一致
                third_layout.addLayout(speed_group_layout, 1)
                third_layout.addWidget(separator1)
                third_layout.addLayout(temp_group_layout, 1)
                layout.addLayout(third_layout)

                # 第四行：电机运行状态显示和实时温度显示合并为一行
                fourth_layout = QHBoxLayout()

                # 左侧：电机运行状态显示
                status_group_layout = QHBoxLayout()
                self.label_status_title = QLabel('运行状态：')
                self.label_status_title.setStyleSheet("font-size: 20px;")
                self.label_status_value = QLabel('运动/停止')
                self.label_status_value.setStyleSheet("font-size: 20px;")
                self.label_current_speed_title = QLabel('当前转速：')
                self.label_current_speed_title.setStyleSheet("font-size: 20px;")
                self.label_current_speed_value = QLabel('转速')
                self.label_current_speed_value.setStyleSheet("font-size: 20px;")

                status_group_layout.addWidget(self.label_status_title)
                status_group_layout.addWidget(self.label_status_value)
                status_group_layout.addWidget(self.label_current_speed_title)
                status_group_layout.addWidget(self.label_current_speed_value)

                # 创建第二个竖直分隔线
                separator2 = QFrame()
                separator2.setFrameShape(QFrame.VLine)
                separator2.setFrameStyle(QFrame.VLine | QFrame.Sunken)
                separator2.setLineWidth(1)

                # 右侧：实时温度显示
                temp_display_group_layout = QHBoxLayout()
                self.label_realtime_temp_title = QLabel('实时温度')
                self.label_realtime_temp_title.setStyleSheet("font-size: 20px;")
                self.label_realtime_temp_value = QLabel('温度/℃')
                self.label_realtime_temp_value.setStyleSheet("font-size: 20px;")

                temp_display_group_layout.addWidget(self.label_realtime_temp_title)
                temp_display_group_layout.addWidget(self.label_realtime_temp_value)

                # 将左右两组添加到主布局，设置相等的stretch因子使宽度一致
                fourth_layout.addLayout(status_group_layout, 1)
                fourth_layout.addWidget(separator2)
                fourth_layout.addLayout(temp_display_group_layout, 1)
                layout.addLayout(fourth_layout)

                # 第五行：抽真空
                fifth_layout = QHBoxLayout()
                self.btn_vacuum = QPushButton('抽真空')
                self.btn_vacuum.setStyleSheet("font-size: 20px;")
                fifth_layout.addWidget(self.btn_vacuum)
                layout.addLayout(fifth_layout)

                # 第六行：添加溶液
                sixth_layout = QHBoxLayout()
                self.btn_add_solution_a = QPushButton(f'添加{self.solution_a}')
                self.btn_add_solution_b = QPushButton(f'添加{self.solution_b}')
                self.btn_add_solution_c = QPushButton(f'添加{self.solution_c}')
                self.btn_add_solution_d = QPushButton(f'添加{self.solution_d}')

                sixth_layout.addWidget(self.btn_add_solution_a)
                sixth_layout.addWidget(self.btn_add_solution_b)
                sixth_layout.addWidget(self.btn_add_solution_c)
                sixth_layout.addWidget(self.btn_add_solution_d)
                layout.addLayout(sixth_layout)

                # 第七行：添加剂量设置
                seventh_layout = QHBoxLayout()
                self.label_dosage_a = QLabel('添加剂量')
                self.line_dosage_a = QLineEdit()
                # 设置剂量允许非负浮点数输入
                # dosage_validator = QDoubleValidator(0.0, 9999.99, 2)
                # self.line_dosage_a.setValidator(dosage_validator)
                self.label_ml_a = QLabel('ml')
                self.label_dosage_b = QLabel('添加剂量')
                self.line_dosage_b = QLineEdit()
                # self.line_dosage_b.setValidator(dosage_validator)
                self.label_ml_b = QLabel('ml')
                self.label_dosage_c = QLabel('添加剂量')
                self.line_dosage_c = QLineEdit()
                # self.line_dosage_c.setValidator(dosage_validator)
                self.label_ml_c = QLabel('ml')
                self.label_dosage_d = QLabel('添加剂量')
                self.line_dosage_d = QLineEdit()
                # self.line_dosage_d.setValidator(dosage_validator)
                self.label_ml_d = QLabel('ml')

                seventh_layout.addWidget(QLabel(''))  # 对应抽真空按钮位置的空白
                seventh_layout.addWidget(self.label_dosage_a)
                seventh_layout.addWidget(self.line_dosage_a)
                seventh_layout.addWidget(self.label_ml_a)
                seventh_layout.addWidget(self.label_dosage_b)
                seventh_layout.addWidget(self.line_dosage_b)
                seventh_layout.addWidget(self.label_ml_b)
                seventh_layout.addWidget(self.label_dosage_c)
                seventh_layout.addWidget(self.line_dosage_c)
                seventh_layout.addWidget(self.label_ml_c)
                seventh_layout.addWidget(self.label_dosage_d)
                seventh_layout.addWidget(self.line_dosage_d)
                seventh_layout.addWidget(self.label_ml_d)
                layout.addLayout(seventh_layout)
            

                # # 第八行：注入速度设置
                # eighth_layout = QHBoxLayout()
                # self.label_inject_speed_a = QLabel('注入速度')
                # self.line_inject_speed_a = QLineEdit()
                # # 设置注入速度允许非负浮点数输入
                # # speed_validator_inject = QDoubleValidator(0.0, 9.99, 2)
                # # self.line_inject_speed_a.setValidator(speed_validator_inject)
                # self.label_ml_s_a = QLabel('ml/s')
                # self.label_inject_speed_b = QLabel('注入速度')
                # self.line_inject_speed_b = QLineEdit()
                # # self.line_inject_speed_b.setValidator(speed_validator_inject)
                # self.label_ml_s_b = QLabel('ml/s')
                # self.label_inject_speed_c = QLabel('注入速度')
                # self.line_inject_speed_c = QLineEdit()
                # # self.line_inject_speed_c.setValidator(speed_validator_inject)
                # self.label_ml_s_c = QLabel('ml/s')
                # self.label_inject_speed_d = QLabel('注入速度')
                # self.line_inject_speed_d = QLineEdit()
                # # self.line_inject_speed_d.setValidator(speed_validator_inject)
                # self.label_ml_s_d = QLabel('ml/s')
                #
                # eighth_layout.addWidget(QLabel(''))  # 对应抽真空按钮位置的空白
                # eighth_layout.addWidget(self.label_inject_speed_a)
                # eighth_layout.addWidget(self.line_inject_speed_a)
                # eighth_layout.addWidget(self.label_ml_s_a)
                # eighth_layout.addWidget(self.label_inject_speed_b)
                # eighth_layout.addWidget(self.line_inject_speed_b)
                # eighth_layout.addWidget(self.label_ml_s_b)
                # eighth_layout.addWidget(self.label_inject_speed_c)
                # eighth_layout.addWidget(self.line_inject_speed_c)
                # eighth_layout.addWidget(self.label_ml_s_c)
                # eighth_layout.addWidget(self.label_inject_speed_d)
                # eighth_layout.addWidget(self.line_inject_speed_d)
                # eighth_layout.addWidget(self.label_ml_s_d)
                # layout.addLayout(eighth_layout)

                # 第九行：溶液添加状态显示
                ninth_layout = QHBoxLayout()
                self.label_solution_status_title = QLabel('溶液添加状态：')
                self.label_solution_status_title.setStyleSheet("font-size: 20px;")
                self.label_solution_status_value = QLabel('执行中/未执行')
                self.label_solution_status_value.setStyleSheet("font-size: 20px;")
                self.progress_bar = QProgressBar()
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)

                ninth_layout.addWidget(self.label_solution_status_title)
                ninth_layout.addWidget(self.label_solution_status_value)
                ninth_layout.addWidget(self.progress_bar)
                layout.addLayout(ninth_layout)
            elif idx == 1:
                # 后处理模块设置tab
                # 第一行：连接/断开后处理模块按钮和串口选择
                post_top_layout = QHBoxLayout()
                self.btn_connect_post = QPushButton('连接后处理模块')
                self.btn_disconnect_post = QPushButton('断开后处理模块')

                # 添加急停按键，设置为红底白字
                self.btn_emergency_stop = QPushButton('急停')
                self.btn_emergency_stop.setStyleSheet("""
                    QPushButton {
                        background-color: #d32f2f;
                        color: white;
                        font-weight: bold;
                        font-size: 20px;
                        border: 2px solid #b71c1c;
                        border-radius: 5px;
                        padding: 8px 16px;
                    }
                    QPushButton:hover {
                        background-color: #b71c1c;
                        border: 2px solid #8c1919;
                    }
                    QPushButton:pressed {
                        background-color: #8c1919;
                    }
                """)

                self.label_port_post = QLabel('串口选择')
                self.label_port_post.setAlignment(Qt.AlignCenter)
                self.combo_port_post = QComboBox()
                self.btn_refresh_port_post = QPushButton('刷新串口')

                post_top_layout.addWidget(self.btn_connect_post)
                post_top_layout.addWidget(self.btn_disconnect_post)
                post_top_layout.addWidget(self.btn_emergency_stop)
                post_top_layout.addWidget(self.label_port_post)
                post_top_layout.addWidget(self.combo_port_post)
                post_top_layout.addWidget(self.btn_refresh_port_post)
                layout.addLayout(post_top_layout)

                # 第二行：选择后处理模块
                post_second_layout = QHBoxLayout()
                self.label_output_serial_number = QLabel('')
                self.label_post_module = QLabel('选择后处理模块')
                self.label_post_module.setAlignment(Qt.AlignCenter)
                self.combo_post_module = QComboBox()
                # 添加1-12的模块选项
                for i in range(1, 13):
                    self.combo_post_module.addItem(f'{i}')
                self.label_valve_output = QLabel('出液口选择')
                self.combo_valve_output = QComboBox()
                self.combo_valve_output.addItems(['加水瓶','反应瓶','沉降瓶'])
                post_second_layout.addWidget(self.label_post_module)
                post_second_layout.addWidget(self.combo_post_module)
                post_second_layout.addWidget(self.label_valve_output)
                post_second_layout.addWidget(self.combo_valve_output)

                layout.addLayout(post_second_layout)

                # 第三行：三列布局
                post_third_layout = QHBoxLayout()

                # 左侧一列：后处理溶液注入按钮
                left_column_layout = QVBoxLayout()
                left_column_layout.setSpacing(10)  # 设置控件间距
                left_column_layout.setAlignment(Qt.AlignTop)  # 顶部对齐
                self.label_inject_title = QLabel('溶液注入')
                self.label_inject_title.setAlignment(Qt.AlignCenter)
                self.btn_inject_solution_a = QPushButton(f'添加{self.inject_solution_a}')

                # 添加剂量和注入速度设置（同一行）
                dosage_speed_layout_a = QHBoxLayout()
                self.label_dosage_inject_a = QLabel('添加剂量')
                self.line_dosage_inject_a = QLineEdit()
                # dosage_validator_inject = QDoubleValidator(0.0, 9999.99, 2)
                # self.line_dosage_inject_a.setValidator(dosage_validator_inject)
                self.label_ml_inject_a = QLabel('ml')
                self.label_speed_inject_a = QLabel('注入速度')
                self.line_post_inject_speed_a = QLineEdit()
                # speed_validator_inject_a = QDoubleValidator(0.0, 999.99, 2)
                # self.line_post_inject_speed_a.setValidator(speed_validator_inject_a)
                self.label_ml_s_inject_a = QLabel('ml/s')

                dosage_speed_layout_a.addWidget(self.label_dosage_inject_a)
                dosage_speed_layout_a.addWidget(self.line_dosage_inject_a)
                dosage_speed_layout_a.addWidget(self.label_ml_inject_a)
                dosage_speed_layout_a.addWidget(self.label_speed_inject_a)
                dosage_speed_layout_a.addWidget(self.line_post_inject_speed_a)
                dosage_speed_layout_a.addWidget(self.label_ml_s_inject_a)

                self.btn_inject_solution_b = QPushButton(f'添加{self.inject_solution_b}')

                # 添加剂量和注入速度设置（B溶液）
                dosage_speed_layout_b = QHBoxLayout()
                self.label_dosage_inject_b = QLabel('添加剂量')
                self.line_dosage_inject_b = QLineEdit()
                # self.line_dosage_inject_b.setValidator(dosage_validator_inject)
                self.label_ml_inject_b = QLabel('ml')
                self.label_speed_inject_b = QLabel('注入速度')
                self.line_post_inject_speed_b = QLineEdit()
                # speed_validator_inject_b = QDoubleValidator(0.0, 999.99, 2)
                # self.line_post_inject_speed_b.setValidator(speed_validator_inject_b)
                self.label_ml_s_inject_b = QLabel('ml/s')

                dosage_speed_layout_b.addWidget(self.label_dosage_inject_b)
                dosage_speed_layout_b.addWidget(self.line_dosage_inject_b)
                dosage_speed_layout_b.addWidget(self.label_ml_inject_b)
                dosage_speed_layout_b.addWidget(self.label_speed_inject_b)
                dosage_speed_layout_b.addWidget(self.line_post_inject_speed_b)
                dosage_speed_layout_b.addWidget(self.label_ml_s_inject_b)

                self.btn_inject_solution_c = QPushButton(f'添加{self.inject_solution_c}')

                # 添加剂量和注入速度设置（C溶液）
                dosage_speed_layout_c = QHBoxLayout()
                self.label_dosage_inject_c = QLabel('添加剂量')
                self.line_dosage_inject_c = QLineEdit()
                # self.line_dosage_inject_c.setValidator(dosage_validator_inject)
                self.label_ml_inject_c = QLabel('ml')
                self.label_speed_inject_c = QLabel('注入速度')
                self.line_post_inject_speed_c = QLineEdit()
                # speed_validator_inject_c = QDoubleValidator(0.0, 999.99, 2)
                # self.line_post_inject_speed_c.setValidator(speed_validator_inject_c)
                self.label_ml_s_inject_c = QLabel('ml/s')

                dosage_speed_layout_c.addWidget(self.label_dosage_inject_c)
                dosage_speed_layout_c.addWidget(self.line_dosage_inject_c)
                dosage_speed_layout_c.addWidget(self.label_ml_inject_c)
                dosage_speed_layout_c.addWidget(self.label_speed_inject_c)
                dosage_speed_layout_c.addWidget(self.line_post_inject_speed_c)
                dosage_speed_layout_c.addWidget(self.label_ml_s_inject_c)

                # 清洁步骤A按钮
                self.btn_clean_step_a = QPushButton('清洁步骤A(2→3)')

                # 添加剂量和注入速度设置（清洁步骤A）
                dosage_speed_layout_clean_a = QHBoxLayout()
                self.label_dosage_clean_a = QLabel('添加剂量')
                self.line_dosage_clean_a = QLineEdit()
                self.label_ml_clean_a = QLabel('ml')
                self.label_speed_clean_a = QLabel('注入速度')
                self.line_post_inject_speed_clean_a = QLineEdit()
                self.label_ml_s_clean_a = QLabel('ml/s')

                dosage_speed_layout_clean_a.addWidget(self.label_dosage_clean_a)
                dosage_speed_layout_clean_a.addWidget(self.line_dosage_clean_a)
                dosage_speed_layout_clean_a.addWidget(self.label_ml_clean_a)
                dosage_speed_layout_clean_a.addWidget(self.label_speed_clean_a)
                dosage_speed_layout_clean_a.addWidget(self.line_post_inject_speed_clean_a)
                dosage_speed_layout_clean_a.addWidget(self.label_ml_s_clean_a)
                
                # 清洁步骤B按钮
                self.btn_clean_step_b = QPushButton('清洁步骤B(3→4)')

                # 添加剂量和注入速度设置（清洁步骤B）
                dosage_speed_layout_clean_b = QHBoxLayout()
                self.label_dosage_clean_b = QLabel('添加剂量')
                self.line_dosage_clean_b = QLineEdit()
                self.label_ml_clean_b = QLabel('ml')
                self.label_speed_clean_b = QLabel('注入速度')
                self.line_post_inject_speed_clean_b = QLineEdit()
                self.label_ml_s_clean_b = QLabel('ml/s')

                dosage_speed_layout_clean_b.addWidget(self.label_dosage_clean_b)
                dosage_speed_layout_clean_b.addWidget(self.line_dosage_clean_b)
                dosage_speed_layout_clean_b.addWidget(self.label_ml_clean_b)
                dosage_speed_layout_clean_b.addWidget(self.label_speed_clean_b)
                dosage_speed_layout_clean_b.addWidget(self.line_post_inject_speed_clean_b)
                dosage_speed_layout_clean_b.addWidget(self.label_ml_s_clean_b)

                left_column_layout.addWidget(self.label_inject_title)
                left_column_layout.addStretch()  # 添加弹性空间
                left_column_layout.addWidget(self.btn_inject_solution_a)
                left_column_layout.addLayout(dosage_speed_layout_a)
                left_column_layout.addStretch()
                left_column_layout.addWidget(self.btn_inject_solution_b)
                left_column_layout.addLayout(dosage_speed_layout_b)
                left_column_layout.addStretch()
                left_column_layout.addWidget(self.btn_inject_solution_c)
                left_column_layout.addLayout(dosage_speed_layout_c)
                left_column_layout.addStretch()
                left_column_layout.addWidget(self.btn_clean_step_a)
                left_column_layout.addLayout(dosage_speed_layout_clean_a)
                left_column_layout.addStretch()
                left_column_layout.addWidget(self.btn_clean_step_b)
                left_column_layout.addLayout(dosage_speed_layout_clean_b)
                left_column_layout.addStretch()  # 底部弹性空间

                # 中间一列：搅拌控制按钮
                middle_column_layout = QVBoxLayout()
                middle_column_layout.setSpacing(10)
                middle_column_layout.setAlignment(Qt.AlignTop)
                self.label_stirring_title = QLabel('搅拌控制')
                self.label_stirring_title.setAlignment(Qt.AlignCenter)
                self.btn_start_motor_post = QPushButton('启动搅拌')
                self.btn_stop_motor_post = QPushButton('停止搅拌')

                middle_column_layout.addWidget(self.label_stirring_title)
                middle_column_layout.addStretch()
                middle_column_layout.addWidget(self.btn_start_motor_post)
                middle_column_layout.addStretch()
                middle_column_layout.addWidget(self.btn_stop_motor_post)
                middle_column_layout.addStretch()
                
                # 底部搅拌电机控制按钮
                self.btn_start_bottom_motor = QPushButton('启动底部搅拌')
                self.btn_stop_bottom_motor = QPushButton('停止底部搅拌')
                
                middle_column_layout.addWidget(self.btn_start_bottom_motor)
                middle_column_layout.addStretch()
                middle_column_layout.addWidget(self.btn_stop_bottom_motor)
                middle_column_layout.addStretch()

                # 转速设置
                speed_layout = QHBoxLayout()
                self.label_speed_set = QLabel('转速设置')
                self.line_motor_speed_post = QLineEdit()
                # 设置转速只允许正整数输入
                # speed_validator_post = QIntValidator(1, 99999)
                # self.line_speed_set.setValidator(speed_validator_post)
                self.label_rpm_post = QLabel('RPM')

                speed_layout.addWidget(self.label_speed_set)
                speed_layout.addWidget(self.line_motor_speed_post)
                speed_layout.addWidget(self.label_rpm_post)
                middle_column_layout.addLayout(speed_layout)
                middle_column_layout.addStretch()

                # 运行状态显示
                status_layout = QHBoxLayout()
                self.label_status_title_post = QLabel('运行状态')
                self.label_status_value_post = QLabel('运动/停止')

                status_layout.addWidget(self.label_status_title_post)
                status_layout.addWidget(self.label_status_value_post)
                middle_column_layout.addLayout(status_layout)
                middle_column_layout.addStretch()

                # 右侧一列：阀门控制按钮
                right_column_layout = QVBoxLayout()
                right_column_layout.setSpacing(10)
                right_column_layout.setAlignment(Qt.AlignTop)
                self.label_valve_title = QLabel('阀门控制')
                self.label_valve_title.setAlignment(Qt.AlignCenter)
                self.btn_gas_valve = QPushButton('通气')
                self.btn_liquid_return_valve = QPushButton('两通阀')
                self.btn_discharge_valve = QPushButton('三通阀')
                self.btn_water_valve = QPushButton('水阀')

                # 设置阀门控制按钮的默认颜色为红色
                valve_button_style = "QPushButton { background-color: red; color: black; }"
                self.btn_gas_valve.setStyleSheet(valve_button_style)
                self.btn_liquid_return_valve.setStyleSheet(valve_button_style)
                self.btn_discharge_valve.setStyleSheet(valve_button_style)
                self.btn_water_valve.setStyleSheet(valve_button_style)

                right_column_layout.addWidget(self.label_valve_title)
                right_column_layout.addStretch()
                right_column_layout.addWidget(self.btn_gas_valve)
                right_column_layout.addStretch()
                right_column_layout.addWidget(self.btn_liquid_return_valve)
                right_column_layout.addStretch()
                right_column_layout.addWidget(self.btn_discharge_valve)
                right_column_layout.addStretch()
                right_column_layout.addWidget(self.btn_water_valve)
                right_column_layout.addStretch()

                # 创建第一个竖直分隔线
                separator1 = QFrame()
                separator1.setFrameShape(QFrame.VLine)
                separator1.setFrameStyle(QFrame.VLine | QFrame.Sunken)
                separator1.setLineWidth(1)

                # 创建第二个竖直分隔线
                separator2 = QFrame()
                separator2.setFrameShape(QFrame.VLine)
                separator2.setFrameStyle(QFrame.VLine | QFrame.Sunken)
                separator2.setLineWidth(1)

                # 将三列和分隔线添加到水平布局中，设置相等的stretch因子使宽度一致
                post_third_layout.addLayout(left_column_layout, 1)
                post_third_layout.addWidget(separator1)
                post_third_layout.addLayout(middle_column_layout, 1)
                post_third_layout.addWidget(separator2)
                post_third_layout.addLayout(right_column_layout, 1)
                layout.addLayout(post_third_layout)

                # 第四行：溶液添加状态显示
                post_fourth_layout = QHBoxLayout()
                self.label_solution_status_title_post = QLabel('溶液添加状态')
                self.label_solution_status_title_post.setStyleSheet("font-size: 20px;")
                self.label_solution_status_value_post = QLabel('执行中/未执行')
                self.label_solution_status_value_post.setStyleSheet("font-size: 20px;")
                self.progress_bar_post = QProgressBar()
                self.progress_bar_post.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)

                post_fourth_layout.addWidget(self.label_solution_status_title_post)
                post_fourth_layout.addWidget(self.label_solution_status_value_post)
                post_fourth_layout.addWidget(self.progress_bar_post)
                layout.addLayout(post_fourth_layout)
            elif idx == 2:  # 索引2对应"三轴位置标定"标签页

                # 第一行：左上方和右上方布局（使用QHBoxLayout）
                top_row_layout = QHBoxLayout()

                # 1. 左上方布局：实时位置及限位显示
                position_status_layout = QVBoxLayout()
                position_group_box = QGroupBox("实时位置与限位状态")
                position_group_box.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")

                # 创建网格布局显示三轴信息
                pos_grid = QGridLayout()

                # 添加标题
                pos_grid.addWidget(QLabel("轴"), 0, 0, Qt.AlignCenter)
                pos_grid.addWidget(QLabel("当前位置 (mm)"), 0, 1, Qt.AlignCenter)
                pos_grid.addWidget(QLabel("正限位"), 0, 2, Qt.AlignCenter)
                pos_grid.addWidget(QLabel("负限位"), 0, 3, Qt.AlignCenter)

                # X轴信息
                pos_grid.addWidget(QLabel("X轴"), 1, 0, Qt.AlignCenter)
                self.label_x_pos = QLabel("0.00")
                self.label_x_pos.setStyleSheet("font-weight: bold; color: #2c3e50;")
                pos_grid.addWidget(self.label_x_pos, 1, 1, Qt.AlignCenter)
                self.label_x_positive_limit = QLabel("正常")
                self.label_x_positive_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_x_positive_limit, 1, 2, Qt.AlignCenter)
                self.label_x_negative_limit = QLabel("正常")
                self.label_x_negative_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_x_negative_limit, 1, 3, Qt.AlignCenter)

                # Y轴信息
                pos_grid.addWidget(QLabel("Y轴"), 2, 0, Qt.AlignCenter)
                self.label_y_pos = QLabel("0.00")
                self.label_y_pos.setStyleSheet("font-weight: bold; color: #2c3e50;")
                pos_grid.addWidget(self.label_y_pos, 2, 1, Qt.AlignCenter)
                self.label_y_positive_limit = QLabel("正常")
                self.label_y_positive_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_y_positive_limit, 2, 2, Qt.AlignCenter)
                self.label_y_negative_limit = QLabel("正常")
                self.label_y_negative_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_y_negative_limit, 2, 3, Qt.AlignCenter)

                # Z轴信息
                pos_grid.addWidget(QLabel("Z轴"), 3, 0, Qt.AlignCenter)
                self.label_z_pos = QLabel("0.00")
                self.label_z_pos.setStyleSheet("font-weight: bold; color: #2c3e50;")
                pos_grid.addWidget(self.label_z_pos, 3, 1, Qt.AlignCenter)
                self.label_z_positive_limit = QLabel("正常")
                self.label_z_positive_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_z_positive_limit, 3, 2, Qt.AlignCenter)
                self.label_z_negative_limit = QLabel("正常")
                self.label_z_negative_limit.setStyleSheet("color: green;")
                pos_grid.addWidget(self.label_z_negative_limit, 3, 3, Qt.AlignCenter)

                # 设置列宽比例
                for i in range(4):
                    pos_grid.setColumnStretch(i, 1)

                position_group_box.setLayout(pos_grid)
                position_status_layout.addWidget(position_group_box)
                top_row_layout.addLayout(position_status_layout, 1)  # 占1份宽度

                # 2. 右上方布局：急停、复位按钮
                control_buttons_layout = QVBoxLayout()
                control_group_box = QGroupBox("控制按钮")
                control_group_box.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")

                # 内部布局
                buttons_vbox = QVBoxLayout()

                # 大按钮：急停和复位
                big_buttons_hbox = QHBoxLayout()

                # 急停按钮（红底白字）
                self.btn_emergency = QPushButton("急停")
                self.btn_emergency.setStyleSheet("""
                    QPushButton {
                        background-color: #d32f2f;
                        color: white;
                        font-size: 18px;
                        font-weight: bold;
                        height: 60px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #b71c1c;
                    }
                """)
                big_buttons_hbox.addWidget(self.btn_emergency)

                # 复位按钮（黄底黑字）
                self.btn_reset_all = QPushButton("复位")
                self.btn_reset_all.setStyleSheet("""
                    QPushButton {
                        background-color: #ffc107;
                        color: black;
                        font-size: 18px;
                        font-weight: bold;
                        height: 60px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #ffb300;
                    }
                """)
                big_buttons_hbox.addWidget(self.btn_reset_all)

                buttons_vbox.addLayout(big_buttons_hbox)
                buttons_vbox.addSpacing(10)  # 增加间距

                # 小按钮：各轴复位
                axis_reset_hbox = QHBoxLayout()

                self.btn_reset_x = QPushButton("X轴复位")
                self.btn_reset_y = QPushButton("Y轴复位")
                self.btn_reset_z = QPushButton("Z轴复位")

                # 设置小按钮样式
                reset_btn_style = """
                    QPushButton {
                        background-color: #2196f3;
                        color: white;
                        font-size: 14px;
                        height: 40px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #1976d2;
                    }
                """
                self.btn_reset_x.setStyleSheet(reset_btn_style)
                self.btn_reset_y.setStyleSheet(reset_btn_style)
                self.btn_reset_z.setStyleSheet(reset_btn_style)

                axis_reset_hbox.addWidget(self.btn_reset_x)
                axis_reset_hbox.addWidget(self.btn_reset_y)
                axis_reset_hbox.addWidget(self.btn_reset_z)

                buttons_vbox.addLayout(axis_reset_hbox)
                buttons_vbox.addStretch()  # 拉伸填充空间

                control_group_box.setLayout(buttons_vbox)
                control_buttons_layout.addWidget(control_group_box)
                top_row_layout.addLayout(control_buttons_layout, 1)  # 占1份宽度

                layout.addLayout(top_row_layout)
                layout.addSpacing(10)

                # 第二行：点动控制（左）和位置标定（右）水平布局
                motion_and_calibration_layout = QHBoxLayout()

                # 左侧：点动控制布局
                jog_control_group = QGroupBox("点动控制")
                jog_control_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
                jog_layout = QVBoxLayout()  # 改为垂直布局容纳XY和Z轴点动控制

                # XY轴点动控制（上下左右布局）
                xy_jog_layout = QGridLayout()

                # Y+ (上)
                self.btn_jog_y_plus = QPushButton("Y+")
                self.btn_jog_y_plus.setStyleSheet("height: 40px; font-size: 14px;")
                xy_jog_layout.addWidget(self.btn_jog_y_plus, 0, 1)

                # X- (左)
                self.btn_jog_x_minus = QPushButton("X-")
                self.btn_jog_x_minus.setStyleSheet("height: 40px; font-size: 14px;")
                xy_jog_layout.addWidget(self.btn_jog_x_minus, 1, 0)

                # 中间占位
                xy_jog_layout.addWidget(QLabel(""), 1, 1)

                # X+ (右)
                self.btn_jog_x_plus = QPushButton("X+")
                self.btn_jog_x_plus.setStyleSheet("height: 40px; font-size: 14px;")
                xy_jog_layout.addWidget(self.btn_jog_x_plus, 1, 2)

                # Y- (下)
                self.btn_jog_y_minus = QPushButton("Y-")
                self.btn_jog_y_minus.setStyleSheet("height: 40px; font-size: 14px;")
                xy_jog_layout.addWidget(self.btn_jog_y_minus, 2, 1)

                # 设置网格比例
                for i in range(3):
                    xy_jog_layout.setRowStretch(i, 1)
                    xy_jog_layout.setColumnStretch(i, 1)

                # Z轴点动控制（单独上下布局）
                z_jog_layout = QVBoxLayout()
                z_jog_layout.setSpacing(10)

                self.btn_jog_z_plus = QPushButton("Z+")
                self.btn_jog_z_plus.setStyleSheet("height: 40px; font-size: 14px;")
                self.btn_jog_z_minus = QPushButton("Z-")
                self.btn_jog_z_minus.setStyleSheet("height: 40px; font-size: 14px;")

                z_jog_layout.addWidget(self.btn_jog_z_plus)
                z_jog_layout.addWidget(self.btn_jog_z_minus)

                # 将XY和Z轴点动控制添加到点动主布局
                jog_layout.addLayout(xy_jog_layout)
                jog_layout.addSpacing(15)
                jog_layout.addLayout(z_jog_layout)
                jog_layout.addStretch()

                jog_control_group.setLayout(jog_layout)
                motion_and_calibration_layout.addWidget(jog_control_group, 3)  # 点动控制占3份宽度

                # 添加分隔线
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
                separator.setLineWidth(1)
                motion_and_calibration_layout.addWidget(separator)

                # 右侧：位置标定区域
                calibration_group = QGroupBox("位置标定")
                calibration_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
                calibration_layout = QVBoxLayout()

                # 创建网格布局放置标定位置信息
                calibration_grid = QGridLayout()

                # 标题行
                calibration_grid.addWidget(QLabel("位置名称"), 0, 0, Qt.AlignCenter)
                calibration_grid.addWidget(QLabel("X轴坐标 (mm)"), 0, 1, Qt.AlignCenter)
                calibration_grid.addWidget(QLabel("Y轴坐标 (mm)"), 0, 2, Qt.AlignCenter)
                calibration_grid.addWidget(QLabel("Z轴坐标 (mm)"), 0, 3, Qt.AlignCenter)
                calibration_grid.addWidget(QLabel("操作"), 0, 4, Qt.AlignCenter)

                # 设置标题样式
                for col in range(5):
                    item = calibration_grid.itemAtPosition(0, col)
                    if item:
                        label = item.widget()
                        label.setStyleSheet("font-weight: bold;")

                # 标定位置1
                calibration_grid.addWidget(QLabel("标定位置1"), 1, 0, Qt.AlignCenter)
                self.calib1_x = QLineEdit()
                # self.calib1_x.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib1_x, 1, 1)
                self.calib1_y = QLineEdit()
                # self.calib1_y.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib1_y, 1, 2)
                self.calib1_z = QLineEdit()
                # self.calib1_z.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib1_z, 1, 3)
                self.btn_calib1 = QPushButton("动作")
                calibration_grid.addWidget(self.btn_calib1, 1, 4)

                # 标定位置2
                calibration_grid.addWidget(QLabel("标定位置2"), 2, 0, Qt.AlignCenter)
                self.calib2_x = QLineEdit()
                # self.calib2_x.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib2_x, 2, 1)
                self.calib2_y = QLineEdit()
                # self.calib2_y.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib2_y, 2, 2)
                self.calib2_z = QLineEdit()
                # self.calib2_z.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib2_z, 2, 3)
                self.btn_calib2 = QPushButton("动作")
                calibration_grid.addWidget(self.btn_calib2, 2, 4)

                # 标定位置3
                calibration_grid.addWidget(QLabel("标定位置3"), 3, 0, Qt.AlignCenter)
                self.calib3_x = QLineEdit()
                # self.calib3_x.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib3_x, 3, 1)
                self.calib3_y = QLineEdit()
                # self.calib3_y.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib3_y, 3, 2)
                self.calib3_z = QLineEdit()
                # self.calib3_z.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib3_z, 3, 3)
                self.btn_calib3 = QPushButton("动作")
                calibration_grid.addWidget(self.btn_calib3, 3, 4)

                # 标定位置4
                calibration_grid.addWidget(QLabel("标定位置4"), 4, 0, Qt.AlignCenter)
                self.calib4_x = QLineEdit()
                # self.calib4_x.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib4_x, 4, 1)
                self.calib4_y = QLineEdit()
                # self.calib4_y.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib4_y, 4, 2)
                self.calib4_z = QLineEdit()
                # self.calib4_z.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                calibration_grid.addWidget(self.calib4_z, 4, 3)
                self.btn_calib4 = QPushButton("动作")
                calibration_grid.addWidget(self.btn_calib4, 4, 4)

                # 设置列宽比例
                calibration_grid.setColumnStretch(0, 1)
                calibration_grid.setColumnStretch(1, 2)
                calibration_grid.setColumnStretch(2, 2)
                calibration_grid.setColumnStretch(3, 2)
                calibration_grid.setColumnStretch(4, 1)

                calibration_layout.addLayout(calibration_grid)
                calibration_group.setLayout(calibration_layout)
                motion_and_calibration_layout.addWidget(calibration_group, 5)  # 位置标定占5份宽度

                # 将点动控制和位置标定的组合布局添加到主布局
                layout.addLayout(motion_and_calibration_layout)
                layout.addSpacing(10)

                # 第三行：位置设定布局
                position_set_group = QGroupBox("位置设定")
                position_set_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
                position_set_layout = QVBoxLayout()

                # 创建一个网格布局来放置三个轴的设置
                axis_settings_grid = QGridLayout()

                # 添加标题行
                axis_settings_grid.addWidget(QLabel("轴"), 0, 0, Qt.AlignCenter)
                axis_settings_grid.addWidget(QLabel("绝对位置 (mm)"), 0, 1, Qt.AlignCenter)
                axis_settings_grid.addWidget(QLabel("移动速度 (mm/s)"), 0, 2, Qt.AlignCenter)
                axis_settings_grid.addWidget(QLabel("操作"), 0, 3, Qt.AlignCenter)

                # X轴设置
                axis_settings_grid.addWidget(QLabel("X轴"), 1, 0, Qt.AlignCenter)
                self.line_x_pos = QLineEdit()
                # self.line_x_pos.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                axis_settings_grid.addWidget(self.line_x_pos, 1, 1)
                self.line_x_speed = QLineEdit()
                # self.line_x_speed.setValidator(QDoubleValidator(0.1, 100.0, 1))
                self.line_x_speed.setText("5.0")  # 默认速度
                axis_settings_grid.addWidget(self.line_x_speed, 1, 2)
                self.btn_move_x = QPushButton("移动X轴")
                axis_settings_grid.addWidget(self.btn_move_x, 1, 3)

                # Y轴设置
                axis_settings_grid.addWidget(QLabel("Y轴"), 2, 0, Qt.AlignCenter)
                self.line_y_pos = QLineEdit()
                # self.line_y_pos.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                axis_settings_grid.addWidget(self.line_y_pos, 2, 1)
                self.line_y_speed = QLineEdit()
                # self.line_y_speed.setValidator(QDoubleValidator(0.1, 100.0, 1))
                self.line_y_speed.setText("5.0")  # 默认速度
                axis_settings_grid.addWidget(self.line_y_speed, 2, 2)
                self.btn_move_y = QPushButton("移动Y轴")
                axis_settings_grid.addWidget(self.btn_move_y, 2, 3)

                # Z轴设置
                axis_settings_grid.addWidget(QLabel("Z轴"), 3, 0, Qt.AlignCenter)
                self.line_z_pos = QLineEdit()
                # self.line_z_pos.setValidator(QDoubleValidator(-9999.99, 9999.99, 2))
                axis_settings_grid.addWidget(self.line_z_pos, 3, 1)
                self.line_z_speed = QLineEdit()
                # self.line_z_speed.setValidator(QDoubleValidator(0.1, 100.0, 1))
                self.line_z_speed.setText("5.0")  # 默认速度
                axis_settings_grid.addWidget(self.line_z_speed, 3, 2)
                self.btn_move_z = QPushButton("移动Z轴")
                axis_settings_grid.addWidget(self.btn_move_z, 3, 3)

                # 设置列宽比例
                axis_settings_grid.setColumnStretch(0, 1)
                axis_settings_grid.setColumnStretch(1, 2)
                axis_settings_grid.setColumnStretch(2, 2)
                axis_settings_grid.setColumnStretch(3, 1)

                position_set_layout.addLayout(axis_settings_grid)
                position_set_layout.addSpacing(10)

                # 整体动作按钮
                self.btn_move_all = QPushButton("三轴联动")
                self.btn_move_all.setStyleSheet("""
                    QPushButton {
                        background-color: #4caf50;
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                        height: 40px;
                    }
                    QPushButton:hover {
                        background-color: #388e3c;
                    }
                """)
                position_set_layout.addWidget(self.btn_move_all)

                position_set_group.setLayout(position_set_layout)
                layout.addWidget(position_set_group)

                # 设置主布局的拉伸因子
                layout.setStretch(0, 1)  # 第一行：实时位置和控制按钮
                layout.setStretch(1, 0)  # 间距
                layout.setStretch(2, 3)  # 第二行：点动控制和位置标定（占比最大）
                layout.setStretch(3, 0)  # 间距
                layout.setStretch(4, 2)  # 第三行：位置设定
            elif idx == 3:  # 索引3对应"自动化程序"标签页
                # 创建标题行
                title_row_layout = QHBoxLayout()
                # 设置布局紧凑模式，减小间距
                title_row_layout.setSpacing(5)
                title_row_layout.setContentsMargins(0, 0, 0, 0)
                
                self.label_serial = QLabel('序号')
                self.label_serial.setAlignment(Qt.AlignCenter)
                self.label_serial.setFixedHeight(20)  # 固定高度为20px
                
                self.label_status = QLabel('执行状态')
                self.label_status.setAlignment(Qt.AlignCenter)
                self.label_status.setFixedHeight(20)  # 固定高度为20px
                
                self.label_drive = QLabel('驱动按钮')
                self.label_drive.setAlignment(Qt.AlignCenter)
                self.label_drive.setFixedHeight(20)  # 固定高度为20px
                
                title_row_layout.addWidget(self.label_serial, 1)
                title_row_layout.addWidget(self.label_status, 2)
                title_row_layout.addWidget(self.label_drive, 2)
                layout.addLayout(title_row_layout)
                
                # 创建第一个后处理模块行
                module1_layout = QHBoxLayout()
                self.label_module1 = QLabel('后处理模块1')
                self.label_module1.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module1 = QProgressBar()
                self.progress_module1.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module1_layout = QHBoxLayout()
                self.btn_settle_module1 = QPushButton('沉降')
                self.btn_clean_module1 = QPushButton('清洁')
                buttons_module1_layout.addWidget(self.btn_settle_module1)
                buttons_module1_layout.addWidget(self.btn_clean_module1)
                
                module1_layout.addWidget(self.label_module1, 1)
                module1_layout.addWidget(self.progress_module1, 2)
                module1_layout.addLayout(buttons_module1_layout, 2)
                layout.addLayout(module1_layout)
                
                # 创建第二个后处理模块行
                module2_layout = QHBoxLayout()
                self.label_module2 = QLabel('后处理模块2')
                self.label_module2.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module2 = QProgressBar()
                self.progress_module2.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module2_layout = QHBoxLayout()
                self.btn_settle_module2 = QPushButton('沉降')
                self.btn_clean_module2 = QPushButton('清洁')
                buttons_module2_layout.addWidget(self.btn_settle_module2)
                buttons_module2_layout.addWidget(self.btn_clean_module2)
                
                module2_layout.addWidget(self.label_module2, 1)
                module2_layout.addWidget(self.progress_module2, 2)
                module2_layout.addLayout(buttons_module2_layout, 2)
                layout.addLayout(module2_layout)
                
                # 创建第三个后处理模块行
                module3_layout = QHBoxLayout()
                self.label_module3 = QLabel('后处理模块3')
                self.label_module3.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module3 = QProgressBar()
                self.progress_module3.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module3_layout = QHBoxLayout()
                self.btn_settle_module3 = QPushButton('沉降')
                self.btn_clean_module3 = QPushButton('清洁')
                buttons_module3_layout.addWidget(self.btn_settle_module3)
                buttons_module3_layout.addWidget(self.btn_clean_module3)
                
                module3_layout.addWidget(self.label_module3, 1)
                module3_layout.addWidget(self.progress_module3, 2)
                module3_layout.addLayout(buttons_module3_layout, 2)
                layout.addLayout(module3_layout)
                
                # 创建第四个后处理模块行
                module4_layout = QHBoxLayout()
                self.label_module4 = QLabel('后处理模块4')
                self.label_module4.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module4 = QProgressBar()
                self.progress_module4.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module4_layout = QHBoxLayout()
                self.btn_settle_module4 = QPushButton('沉降')
                self.btn_clean_module4 = QPushButton('清洁')
                buttons_module4_layout.addWidget(self.btn_settle_module4)
                buttons_module4_layout.addWidget(self.btn_clean_module4)
                
                module4_layout.addWidget(self.label_module4, 1)
                module4_layout.addWidget(self.progress_module4, 2)
                module4_layout.addLayout(buttons_module4_layout, 2)
                layout.addLayout(module4_layout)
                
                # 创建第五个后处理模块行
                module5_layout = QHBoxLayout()
                self.label_module5 = QLabel('后处理模块5')
                self.label_module5.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module5 = QProgressBar()
                self.progress_module5.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module5_layout = QHBoxLayout()
                self.btn_settle_module5 = QPushButton('沉降')
                self.btn_clean_module5 = QPushButton('清洁')
                buttons_module5_layout.addWidget(self.btn_settle_module5)
                buttons_module5_layout.addWidget(self.btn_clean_module5)
                
                module5_layout.addWidget(self.label_module5, 1)
                module5_layout.addWidget(self.progress_module5, 2)
                module5_layout.addLayout(buttons_module5_layout, 2)
                layout.addLayout(module5_layout)
                
                # 创建第六个后处理模块行
                module6_layout = QHBoxLayout()
                self.label_module6 = QLabel('后处理模块6')
                self.label_module6.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module6 = QProgressBar()
                self.progress_module6.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module6_layout = QHBoxLayout()
                self.btn_settle_module6 = QPushButton('沉降')
                self.btn_clean_module6 = QPushButton('清洁')
                buttons_module6_layout.addWidget(self.btn_settle_module6)
                buttons_module6_layout.addWidget(self.btn_clean_module6)
                
                module6_layout.addWidget(self.label_module6, 1)
                module6_layout.addWidget(self.progress_module6, 2)
                module6_layout.addLayout(buttons_module6_layout, 2)
                layout.addLayout(module6_layout)
                
                # 创建第七个后处理模块行
                module7_layout = QHBoxLayout()
                self.label_module7 = QLabel('后处理模块7')
                self.label_module7.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module7 = QProgressBar()
                self.progress_module7.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module7_layout = QHBoxLayout()
                self.btn_settle_module7 = QPushButton('沉降')
                self.btn_clean_module7 = QPushButton('清洁')
                buttons_module7_layout.addWidget(self.btn_settle_module7)
                buttons_module7_layout.addWidget(self.btn_clean_module7)
                
                module7_layout.addWidget(self.label_module7, 1)
                module7_layout.addWidget(self.progress_module7, 2)
                module7_layout.addLayout(buttons_module7_layout, 2)
                layout.addLayout(module7_layout)
                
                # 创建第八个后处理模块行
                module8_layout = QHBoxLayout()
                self.label_module8 = QLabel('后处理模块8')
                self.label_module8.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module8 = QProgressBar()
                self.progress_module8.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module8_layout = QHBoxLayout()
                self.btn_settle_module8 = QPushButton('沉降')
                self.btn_clean_module8 = QPushButton('清洁')
                buttons_module8_layout.addWidget(self.btn_settle_module8)
                buttons_module8_layout.addWidget(self.btn_clean_module8)
                
                module8_layout.addWidget(self.label_module8, 1)
                module8_layout.addWidget(self.progress_module8, 2)
                module8_layout.addLayout(buttons_module8_layout, 2)
                layout.addLayout(module8_layout)
                
                # 创建第九个后处理模块行
                module9_layout = QHBoxLayout()
                self.label_module9 = QLabel('后处理模块9')
                self.label_module9.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module9 = QProgressBar()
                self.progress_module9.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module9_layout = QHBoxLayout()
                self.btn_settle_module9 = QPushButton('沉降')
                self.btn_clean_module9 = QPushButton('清洁')
                buttons_module9_layout.addWidget(self.btn_settle_module9)
                buttons_module9_layout.addWidget(self.btn_clean_module9)
                
                module9_layout.addWidget(self.label_module9, 1)
                module9_layout.addWidget(self.progress_module9, 2)
                module9_layout.addLayout(buttons_module9_layout, 2)
                layout.addLayout(module9_layout)
                
                # 创建第十个后处理模块行
                module10_layout = QHBoxLayout()
                self.label_module10 = QLabel('后处理模块10')
                self.label_module10.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module10 = QProgressBar()
                self.progress_module10.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module10_layout = QHBoxLayout()
                self.btn_settle_module10 = QPushButton('沉降')
                self.btn_clean_module10 = QPushButton('清洁')
                buttons_module10_layout.addWidget(self.btn_settle_module10)
                buttons_module10_layout.addWidget(self.btn_clean_module10)
                
                module10_layout.addWidget(self.label_module10, 1)
                module10_layout.addWidget(self.progress_module10, 2)
                module10_layout.addLayout(buttons_module10_layout, 2)
                layout.addLayout(module10_layout)
                
                # 创建第十一个后处理模块行
                module11_layout = QHBoxLayout()
                self.label_module11 = QLabel('后处理模块11')
                self.label_module11.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module11 = QProgressBar()
                self.progress_module11.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module11_layout = QHBoxLayout()
                self.btn_settle_module11 = QPushButton('沉降')
                self.btn_clean_module11 = QPushButton('清洁')
                buttons_module11_layout.addWidget(self.btn_settle_module11)
                buttons_module11_layout.addWidget(self.btn_clean_module11)
                
                module11_layout.addWidget(self.label_module11, 1)
                module11_layout.addWidget(self.progress_module11, 2)
                module11_layout.addLayout(buttons_module11_layout, 2)
                layout.addLayout(module11_layout)
                
                # 创建第十二个后处理模块行
                module12_layout = QHBoxLayout()
                self.label_module12 = QLabel('后处理模块12')
                self.label_module12.setAlignment(Qt.AlignCenter)
                
                # 创建进度条
                self.progress_module12 = QProgressBar()
                self.progress_module12.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 0px;
                        text-align: center;
                        background-color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #0078d4;
                        border-radius: 0px;
                    }
                """)
                
                # 创建按钮容器
                buttons_module12_layout = QHBoxLayout()
                self.btn_settle_module12 = QPushButton('沉降')
                self.btn_clean_module12 = QPushButton('清洁')
                buttons_module12_layout.addWidget(self.btn_settle_module12)
                buttons_module12_layout.addWidget(self.btn_clean_module12)
                
                module12_layout.addWidget(self.label_module12, 1)
                module12_layout.addWidget(self.progress_module12, 2)
                module12_layout.addLayout(buttons_module12_layout, 2)
                layout.addLayout(module12_layout)

            elif idx == 6:
                from UIInteraction.UIGenerator.TrayTabWidget import TrayTabWidget

                self.tray_tab_widget = TrayTabWidget()
                layout.addWidget(self.tray_tab_widget)

            elif idx == 7:
                from UIInteraction.UIGenerator.TipRackTabWidget import TipRackTabWidget

                self.tip_rack_tab_widget = TipRackTabWidget()
                layout.addWidget(self.tip_rack_tab_widget)

            elif idx == 8:
                from UIInteraction.UIGenerator.RobotDebugTabWidget import RobotDebugTabWidget

                self.robot_debug_tab_widget = RobotDebugTabWidget()
                layout.addWidget(self.robot_debug_tab_widget)
            elif idx == 9:
                from UIInteraction.UIGenerator.CleaningStationDebugTabWidget import (
                    CleaningStationDebugTabWidget,
                )

                self.cleaning_station_debug_tab_widget = CleaningStationDebugTabWidget()
                layout.addWidget(self.cleaning_station_debug_tab_widget)
            
            tab_widget.addTab(tab, title)
        self.setCentralWidget(tab_widget)

    def bind_tray_model(self, tray_model) -> None:
        """绑定料盘数据模型（在 ParameterStorage 创建后调用）。"""
        if self.tray_tab_widget is not None:
            self.tray_tab_widget.bind_tray_model(tray_model)

    def bind_tip_rack_model(self, tip_rack_model) -> None:
        """绑定枪头架数据模型（在 ParameterStorage 创建后调用）。"""
        if self.tip_rack_tab_widget is not None:
            self.tip_rack_tab_widget.bind_tip_rack_model(tip_rack_model)

    def bind_robot_debug(self, param_storage) -> None:
        """绑定机器人调试（在 ParameterStorage 创建后调用）。"""
        if self.robot_debug_tab_widget is not None:
            self.robot_debug_tab_widget.bind_parameter_storage(param_storage)

    def bind_cleaning_station_debug(self, param_storage) -> None:
        """绑定清洁工位调试（在 ParameterStorage 创建后调用）。"""
        if self.cleaning_station_debug_tab_widget is not None:
            self.cleaning_station_debug_tab_widget.bind_parameter_storage(param_storage)