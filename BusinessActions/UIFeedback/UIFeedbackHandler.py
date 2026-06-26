from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QPushButton
from UIInteraction.UIGenerator.MainUI import MainUI

class UIFeedbackHandler(QObject):
    # 定义重置UI的信号
    control_ui_signal = Signal()
    reset_ui_signal = Signal()
    control_ui_signal_post=Signal()
    reset_ui_signal_post=Signal()
    auto_settle_program_signal=Signal(int)
    reset_auto_settle_program_signal = Signal(int)
    auto_clean_program_signal=Signal(int)
    reset_auto_clean_program_signal = Signal(int)
    # 测试界面控制信号
    test_start_signal = Signal()
    test_stop_signal = Signal()

    
    def __init__(self, main_window:MainUI):
        super().__init__()
        self.main_window = main_window
        # 绑定信号到reset_ui_action_post方法
        self.control_ui_signal.connect(self.control_ui_action)
        self.reset_ui_signal.connect(self.reset_ui_action)
        self.reset_ui_signal_post.connect(self.reset_ui_action_post)
        self.control_ui_signal_post.connect(self.control_ui_action_post)
        self.auto_settle_program_signal.connect(self.Auto_SettleProgram_feedback)
        self.reset_auto_settle_program_signal.connect(self.reset_Auto_SettleProgram_feedback)
        self.auto_clean_program_signal.connect(self.Auto_CleanProgram_feedback)
        self.reset_auto_clean_program_signal.connect(self.reset_Auto_CleanProgram_feedback)
        # 绑定测试界面控制信号
        self.test_start_signal.connect(self.on_test_start)
        self.test_stop_signal.connect(self.on_test_stop)
        
        # 创建三个列表，分别指向主UI中自动化程序标签页的12个进度条、沉降按钮和清洁按钮
        self.progress_bars = [
            self.main_window.progress_module1,
            self.main_window.progress_module2,
            self.main_window.progress_module3,
            self.main_window.progress_module4,
            self.main_window.progress_module5,
            self.main_window.progress_module6,
            self.main_window.progress_module7,
            self.main_window.progress_module8,
            self.main_window.progress_module9,
            self.main_window.progress_module10,
            self.main_window.progress_module11,
            self.main_window.progress_module12
        ]
        
        self.settle_buttons = [
            self.main_window.btn_settle_module1,
            self.main_window.btn_settle_module2,
            self.main_window.btn_settle_module3,
            self.main_window.btn_settle_module4,
            self.main_window.btn_settle_module5,
            self.main_window.btn_settle_module6,
            self.main_window.btn_settle_module7,
            self.main_window.btn_settle_module8,
            self.main_window.btn_settle_module9,
            self.main_window.btn_settle_module10,
            self.main_window.btn_settle_module11,
            self.main_window.btn_settle_module12
        ]
        
        self.clean_buttons = [
            self.main_window.btn_clean_module1,
            self.main_window.btn_clean_module2,
            self.main_window.btn_clean_module3,
            self.main_window.btn_clean_module4,
            self.main_window.btn_clean_module5,
            self.main_window.btn_clean_module6,
            self.main_window.btn_clean_module7,
            self.main_window.btn_clean_module8,
            self.main_window.btn_clean_module9,
            self.main_window.btn_clean_module10,
            self.main_window.btn_clean_module11,
            self.main_window.btn_clean_module12
        ]

    def control_ui_action(self):
        """
        控制QT界面控件的行动

        功能：
        1. 将输入控件的背景色改为蓝色
        2. 禁用反应器模块标签页中的4个添加反应液的按钮
        3. 将显示溶液添加状态的label状态改为执行中
        4. 将滚动条设置为不确定样式
        """
        try:
            # # 1. 将输入的控件背景色改为蓝色
            # button.setStyleSheet("""
            #     QPushButton {
            #         background-color: #007acc;
            #         color: white;
            #         font-weight: bold;
            #         border: 2px solid #005a99;
            #         border-radius: 5px;
            #         padding: 8px 16px;
            #     }
            #     QPushButton:hover {
            #         background-color: #005a99;
            #     }
            #     QPushButton:pressed {
            #         background-color: #004477;
            #     }
            # """)

            # 2. 禁用反应器模块标签页中的4个添加反应液的按钮
            self.main_window.btn_vacuum.setEnabled(False)
            self.main_window.btn_add_solution_a.setEnabled(False)
            self.main_window.btn_add_solution_b.setEnabled(False)
            self.main_window.btn_add_solution_c.setEnabled(False)
            self.main_window.btn_add_solution_d.setEnabled(False)
            self.main_window.line_dosage_a.setEnabled(False)
            self.main_window.line_dosage_b.setEnabled(False)
            self.main_window.line_dosage_c.setEnabled(False)
            self.main_window.line_dosage_d.setEnabled(False)

            # 3. 将显示溶液添加状态的label状态改为执行中
            self.main_window.label_solution_status_value.setText('执行中')
            self.main_window.label_solution_status_value.setStyleSheet("""
                font-size: 20px;
                color: #ff6600;
                font-weight: bold;
            """)

            # 4. 将滚动条设置为不确定样式（无限循环动画）
            self.main_window.progress_bar.setRange(0, 0)  # 设置为不确定样式
            self.main_window.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 0px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #ff6600;
                    border-radius: 0px;
                }
            """)

            # print(f"UI控制操作已执行: 按钮 {button.text()} 背景色已改为蓝色，溶液添加按钮已禁用，状态已更新为执行中")

        except Exception as e:
            print(f"控制UI行动时发生错误: {e}")

    def reset_ui_action(self):
        """
        重置UI控制状态（可选的恢复函数）

        """
        try:
            # 重置按钮样式（如果提供了按钮）

            self.main_window.btn_vacuum.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_add_solution_a.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_add_solution_b.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_add_solution_c.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_add_solution_d.setStyleSheet("")  # 恢复默认样式

            # 启用后处理模块标签页中的4个添加反应液的按钮
            self.main_window.btn_vacuum.setEnabled(True)
            self.main_window.btn_add_solution_a.setEnabled(True)
            self.main_window.btn_add_solution_b.setEnabled(True)
            self.main_window.btn_add_solution_c.setEnabled(True)
            self.main_window.btn_add_solution_d.setEnabled(True)
            self.main_window.line_dosage_a.setEnabled(True)
            self.main_window.line_dosage_b.setEnabled(True)
            self.main_window.line_dosage_c.setEnabled(True)
            self.main_window.line_dosage_d.setEnabled(True)

            # 重置溶液添加状态显示
            self.main_window.label_solution_status_value.setText('未执行')
            self.main_window.label_solution_status_value.setStyleSheet("font-size: 20px;")

            # 重置进度条为正常样式
            self.main_window.progress_bar.setRange(0, 100)  # 恢复正常范围
            self.main_window.progress_bar.setValue(0)  # 设置为0
            self.main_window.progress_bar.setStyleSheet("""
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

            print("UI控制状态已重置")

        except Exception as e:
            print(f"重置UI状态时发生错误: {e}")

    def control_ui_action_post(self):
        """
        控制QT界面控件的行动
        功能：
        1. 将输入控件的背景色改为蓝色
        2. 禁用后处理模块标签页中的4个添加反应液的按钮
        3. 将显示溶液添加状态的label状态改为执行中
        4. 将滚动条设置为不确定样式
        """
        try:
            # # 1. 将输入的控件背景色改为蓝色
            # button.setStyleSheet("""
            #     QPushButton {
            #         background-color: #007acc;
            #         color: white;
            #         font-weight: bold;
            #         border: 2px solid #005a99;
            #         border-radius: 5px;
            #         padding: 8px 16px;
            #     }
            #     QPushButton:hover {
            #         background-color: #005a99;
            #     }
            #     QPushButton:pressed {
            #         background-color: #004477;
            #     }
            # """)

            # 2. 禁用后处理模块标签页中的4个添加反应液的按钮
            self.main_window.btn_inject_solution_a.setEnabled(False)
            self.main_window.btn_inject_solution_b.setEnabled(False)
            self.main_window.btn_inject_solution_c.setEnabled(False)
            self.main_window.btn_clean_step_a.setEnabled(False)
            self.main_window.btn_clean_step_b.setEnabled(False)
            self.main_window.line_dosage_inject_a.setEnabled(False)
            self.main_window.line_dosage_inject_b.setEnabled(False)
            self.main_window.line_dosage_inject_c.setEnabled(False)
            self.main_window.line_dosage_clean_a.setEnabled(False)
            self.main_window.line_dosage_clean_b.setEnabled(False)
            self.main_window.line_post_inject_speed_a.setEnabled(False)
            self.main_window.line_post_inject_speed_b.setEnabled(False)
            self.main_window.line_post_inject_speed_c.setEnabled(False)
            self.main_window.line_post_inject_speed_clean_a.setEnabled(False)
            self.main_window.line_post_inject_speed_clean_b.setEnabled(False)

            # 3. 将显示溶液添加状态的label状态改为执行中
            self.main_window.label_solution_status_value_post.setText('执行中')
            self.main_window.label_solution_status_value_post.setStyleSheet("""
                font-size: 20px;
                color: #ff6600;
                font-weight: bold;
            """)

            # 4. 将滚动条设置为不确定样式（无限循环动画）
            self.main_window.progress_bar_post.setRange(0, 0)  # 设置为不确定样式
            self.main_window.progress_bar_post.setStyleSheet("""
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 0px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #ff6600;
                    border-radius: 0px;
                }
            """)

            # print(f"UI控制操作已执行: 按钮 {button.text()} 背景色已改为蓝色，溶液添加按钮已禁用，状态已更新为执行中")

        except Exception as e:
            print(f"控制UI行动时发生错误: {e}")

    def reset_ui_action_post(self):
        """
        重置UI控制状态（可选的恢复函数）
        """
        try:
            # 重置按钮样式（如果提供了按钮）
            
            self.main_window.btn_inject_solution_a.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_inject_solution_b.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_inject_solution_c.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_clean_step_a.setStyleSheet("")  # 恢复默认样式
            self.main_window.btn_clean_step_b.setStyleSheet("") # 恢复默认样式

            # 启用后处理模块标签页中的4个添加反应液的按钮
            self.main_window.btn_inject_solution_a.setEnabled(True)
            self.main_window.btn_inject_solution_b.setEnabled(True)
            self.main_window.btn_inject_solution_c.setEnabled(True)
            self.main_window.btn_clean_step_a.setEnabled(True)
            self.main_window.btn_clean_step_b.setEnabled(True)
            self.main_window.line_dosage_inject_a.setEnabled(True)
            self.main_window.line_dosage_inject_b.setEnabled(True)
            self.main_window.line_dosage_inject_c.setEnabled(True)
            self.main_window.line_dosage_clean_a.setEnabled(True)
            self.main_window.line_dosage_clean_b.setEnabled(True)
            self.main_window.line_post_inject_speed_a.setEnabled(True)
            self.main_window.line_post_inject_speed_b.setEnabled(True)
            self.main_window.line_post_inject_speed_c.setEnabled(True)
            self.main_window.line_post_inject_speed_clean_a.setEnabled(True)
            self.main_window.line_post_inject_speed_clean_b.setEnabled(True)

            # 重置溶液添加状态显示
            self.main_window.label_solution_status_value_post.setText('未执行')
            self.main_window.label_solution_status_value_post.setStyleSheet("font-size: 20px;")

            # 重置进度条为正常样式
            self.main_window.progress_bar_post.setRange(0, 100)  # 恢复正常范围
            self.main_window.progress_bar_post.setValue(0)  # 设置为0
            self.main_window.progress_bar_post.setStyleSheet("""
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

            print("UI控制状态已重置")

        except Exception as e:
            print(f"重置UI状态时发生错误: {e}")

    def Auto_SettleProgram_feedback(self, module_id: int):
        """
        自动沉降程序反馈
        :param self: UI反馈处理器实例
        """
        self.settle_buttons[module_id].setEnabled(False)
        self.clean_buttons[module_id].setEnabled(False)
        self.settle_buttons[module_id].setText("沉降进行中")
        # 设置对应进度条为进行时状态（不确定样式）
        self.progress_bars[module_id].setRange(0, 0)  # 设置为不确定样式
        self.progress_bars[module_id].setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 0px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #ff6600;
                border-radius: 0px;
            }
        """)
    
    def reset_Auto_SettleProgram_feedback(self, module_id: int):
        """
        重置自动沉降程序反馈
        :param self: UI反馈处理器实例
        """
        self.settle_buttons[module_id].setEnabled(True)
        self.clean_buttons[module_id].setEnabled(True)
        self.settle_buttons[module_id].setText("沉降")
        # 设置对应进度条为正常样式
        self.progress_bars[module_id].setRange(0, 100)  # 恢复正常范围
        self.progress_bars[module_id].setValue(0)  # 设置为0
        self.progress_bars[module_id].setStyleSheet("""
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
        
    def Auto_CleanProgram_feedback(self, module_id: int):
        """
        自动清洁程序反馈
        处理清洁程序执行时的UI状态更新
        """
        # 禁用清洁和沉降按钮
        self.clean_buttons[module_id].setEnabled(False)
        self.settle_buttons[module_id].setEnabled(False)
        self.clean_buttons[module_id].setText("清洁进行中")
        # 设置对应进度条为进行时状态（不确定样式）
        self.progress_bars[module_id].setRange(0, 0)  # 设置为不确定样式
        self.progress_bars[module_id].setStyleSheet("""
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
        
    def reset_Auto_CleanProgram_feedback(self, module_id: int):
        """
        重置自动清洁程序反馈
        处理清洁程序完成后的UI状态恢复
        """
        # 启用清洁和沉降按钮
        self.clean_buttons[module_id].setEnabled(True)
        self.settle_buttons[module_id].setEnabled(True)
        self.clean_buttons[module_id].setText("清洁")
        # 设置对应进度条为正常样式
        self.progress_bars[module_id].setRange(0, 100)  # 恢复正常范围
        self.progress_bars[module_id].setValue(0)  # 设置为0
        self.progress_bars[module_id].setStyleSheet("""
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
    
    @Slot()
    def on_test_start(self):
        """
        测试开始时禁用测试界面所有按钮，并将进度条设置为不定形式
        """
        try:
            # 获取测试界面的所有按钮
            test_buttons = [
                # 第一列：抓取加液头按钮
                self.main_window.btn_grab_a, self.main_window.btn_grab_b, self.main_window.btn_grab_c, 
                self.main_window.btn_grab_d, self.main_window.btn_grab_e,
                # 第二列：反应器点位按钮
                self.main_window.btn_reactor_1, self.main_window.btn_reactor_2, self.main_window.btn_reactor_3, 
                self.main_window.btn_reactor_4,
                # 第三列：夹爪控制按钮
                self.main_window.btn_init_claw, self.main_window.btn_grip_claw, self.main_window.btn_release_claw,
                # 第四列：加液泵控制按钮
                self.main_window.btn_add_liquid, self.main_window.btn_reset_pump,
                # 第五列：轴控制按钮
                self.main_window.btn_axis_power_on, self.main_window.btn_axis_home, self.main_window.btn_axis_reset
            ]
            
            # 禁用所有测试界面按钮
            for button in test_buttons:
                button.setEnabled(False)
            
            # 设置进度条为不定形式
            self.main_window.test_progress_bar.setRange(0, 0)  # 设置为不确定样式
            self.main_window.test_progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #ff6600;
                    border-radius: 5px;
                }
            """)
            
            print("测试界面按钮已禁用，进度条已设置为不定形式")
        except Exception as e:
            print(f"测试开始时UI控制发生错误: {e}")
    
    @Slot()
    def on_test_stop(self):
        """
        测试结束时激活测试界面所有按钮，并将进度条重置为0
        """
        try:
            # 获取测试界面的所有按钮
            test_buttons = [
                # 第一列：抓取加液头按钮
                self.main_window.btn_grab_a, self.main_window.btn_grab_b, self.main_window.btn_grab_c, 
                self.main_window.btn_grab_d, self.main_window.btn_grab_e,
                # 第二列：反应器点位按钮
                self.main_window.btn_reactor_1, self.main_window.btn_reactor_2, self.main_window.btn_reactor_3, 
                self.main_window.btn_reactor_4,
                # 第三列：夹爪控制按钮
                self.main_window.btn_init_claw, self.main_window.btn_grip_claw, self.main_window.btn_release_claw,
                # 第四列：加液泵控制按钮
                self.main_window.btn_add_liquid, self.main_window.btn_reset_pump,
                # 第五列：轴控制按钮
                self.main_window.btn_axis_power_on, self.main_window.btn_axis_home, self.main_window.btn_axis_reset
            ]
            
            # 启用所有测试界面按钮并恢复为默认样式
            for button in test_buttons:
                button.setEnabled(True)
            
            # 重置进度条为正常样式
            self.main_window.test_progress_bar.setRange(0, 100)  # 恢复正常范围
            self.main_window.test_progress_bar.setValue(0)  # 设置为0
            self.main_window.test_progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                    border-radius: 5px;
                }
            """)
            
            print("测试界面按钮已激活，进度条已重置")
        except Exception as e:
            print(f"测试结束时UI控制发生错误: {e}")