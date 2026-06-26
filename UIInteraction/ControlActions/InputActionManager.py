from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtCore import Qt, QLocale, QThread, Signal, Slot
from UIInteraction.UIGenerator.MainUI import MainUI
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from BusinessActions.DeviceManager import DeviceManager

class InputActionManager:
    
    class UpdateThread(QThread):
        """用于更新输入变量的线程"""
        def __init__(self, parent):
            super().__init__()
            self.parent = parent
            self.running = True
            
        def run(self):
            """线程运行函数，定期更新输入变量"""
            while self.running:
                self.parent.update_input_values()
                self.msleep(500)  # 每500毫秒更新一次
                
        def stop(self):
            """停止线程"""
            self.running = False
            self.wait()
    def __init__(self, main_ui: MainUI,parameter_storage:ParameterStorage):
        self.main_ui = main_ui
        self.parameter_storage=parameter_storage
        self.set_input_validators()
        
        # 初始化存储输入变量的字典
        self.input_values = {}
        
        # 初始化comboBox的连接
        self.setup_combo_box_connections()
        
        # 创建并启动更新线程
        self.update_thread = self.UpdateThread(self)
        self.update_thread.start()
        
    def set_input_validators(self):
        """为所有输入框设置验证器"""
        # 获取所有输入框
        input_boxes = self.get_all_input_boxes()
        
        # 定义电机转速输入框列表
        motor_speed_inputs = ['line_motor_speed', 'line_motor_speed_post']
        
        # 为每个输入框设置验证器
        for key, input_box in input_boxes.items():
            if input_box is not None:
                if key in motor_speed_inputs:
                    # 电机转速设置为正整数，最大值5000
                    validator = QIntValidator(0, 5000)
                else:
                    # 其他输入框设置为正浮点数，2位小数，最大值999.99
                    validator = QDoubleValidator(0.00, 999.99, 2)
                    validator.setNotation(QDoubleValidator.StandardNotation)
                    validator.setLocale(QLocale('C'))  # 使用点号作为小数点
                
                input_box.setValidator(validator)
                
    def get_all_input_boxes(self):
        """获取MainUI中的所有输入框组件"""
        input_boxes = {}
        
        # 第一标签页：指定模块设置
        input_boxes['line_motor_speed'] = self.main_ui.line_motor_speed
        input_boxes['line_temp'] = self.main_ui.line_temp
        input_boxes['line_dosage_a'] = self.main_ui.line_dosage_a
        input_boxes['line_dosage_b'] = self.main_ui.line_dosage_b
        input_boxes['line_dosage_c'] = self.main_ui.line_dosage_c
        input_boxes['line_dosage_d'] = self.main_ui.line_dosage_d
        
        # 第二标签页：后处理模块设置
        input_boxes['line_dosage_inject_a'] = self.main_ui.line_dosage_inject_a
        input_boxes['line_dosage_inject_b'] = self.main_ui.line_dosage_inject_b
        input_boxes['line_dosage_inject_c'] = self.main_ui.line_dosage_inject_c
        input_boxes['line_dosage_clean_a'] = self.main_ui.line_dosage_clean_a
        input_boxes['line_dosage_clean_b'] = self.main_ui.line_dosage_clean_b
        input_boxes['line_post_inject_speed_a'] = self.main_ui.line_post_inject_speed_a
        input_boxes['line_post_inject_speed_b'] = self.main_ui.line_post_inject_speed_b
        input_boxes['line_post_inject_speed_c'] = self.main_ui.line_post_inject_speed_c
        input_boxes['line_post_inject_speed_clean_a'] = self.main_ui.line_post_inject_speed_clean_a
        input_boxes['line_post_inject_speed_clean_b'] = self.main_ui.line_post_inject_speed_clean_b
        input_boxes['line_motor_speed_post'] = self.main_ui.line_motor_speed_post
        
        # 第三标签页：三轴位置标定
        # 标定位置1-4的坐标输入框
        input_boxes['calib1_x'] = self.main_ui.calib1_x
        input_boxes['calib1_y'] = self.main_ui.calib1_y
        input_boxes['calib1_z'] = self.main_ui.calib1_z
        input_boxes['calib2_x'] = self.main_ui.calib2_x
        input_boxes['calib2_y'] = self.main_ui.calib2_y
        input_boxes['calib2_z'] = self.main_ui.calib2_z
        input_boxes['calib3_x'] = self.main_ui.calib3_x
        input_boxes['calib3_y'] = self.main_ui.calib3_y
        input_boxes['calib3_z'] = self.main_ui.calib3_z
        input_boxes['calib4_x'] = self.main_ui.calib4_x
        input_boxes['calib4_y'] = self.main_ui.calib4_y
        input_boxes['calib4_z'] = self.main_ui.calib4_z
        # 位置设定区域
        input_boxes['line_x_pos'] = self.main_ui.line_x_pos
        input_boxes['line_y_pos'] = self.main_ui.line_y_pos
        input_boxes['line_z_pos'] = self.main_ui.line_z_pos
        input_boxes['line_x_speed'] = self.main_ui.line_x_speed
        input_boxes['line_y_speed'] = self.main_ui.line_y_speed
        input_boxes['line_z_speed'] = self.main_ui.line_z_speed
        
        # 测试界面标签页
        input_boxes['line_dosage'] = self.main_ui.line_dosage
        
        return input_boxes
        
    def get_all_combo_boxes(self):
        """获取MainUI中的所有comboBox组件"""
        combo_boxes = {}
        
        # 第一标签页：指定模块设置
        combo_boxes['combo_port'] = self.main_ui.combo_port
        combo_boxes['combo_reactor'] = self.main_ui.combo_reactor
        
        # 第二标签页：后处理模块设置
        combo_boxes['combo_port_post'] = self.main_ui.combo_port_post
        combo_boxes['combo_post_module'] = self.main_ui.combo_post_module
        combo_boxes['combo_valve_output'] = self.main_ui.combo_valve_output
        
        # 测试界面标签页
        combo_boxes['combo_select_head'] = self.main_ui.combo_select_head

        
        return combo_boxes
        
    def setup_combo_box_connections(self):
        """设置comboBox的信号槽连接"""
        # 获取所有comboBox
        combo_boxes = self.get_all_combo_boxes()
        
        # 为每个comboBox连接currentIndexChanged信号到槽函数
        for name, combo_box in combo_boxes.items():
            if combo_box is not None:
                combo_box.currentIndexChanged.connect(lambda index, name=name: self.on_combo_box_changed(name, index))
        
        # 初始化时立即同步一次所有comboBox的值到参数管理类
        self.sync_all_combo_box_values()
        
    def on_combo_box_changed(self, combo_name: str, index: int):
        """当comboBox的选择发生变化时调用的槽函数
        
        Args:
            combo_name: comboBox的名称
            index: 选择的索引
        """
        combo_box = self.get_all_combo_boxes().get(combo_name)
        if combo_box is not None and index >= 0:
            selected_value = combo_box.currentText()
            
            # 根据comboBox的名称更新参数管理类中的对应变量
            if combo_name == 'combo_port':
                self.parameter_storage.select_port = selected_value
            elif combo_name == 'combo_reactor':
                # 设置反应器模块，更新对应的地址信息
                module_number = int(selected_value) - 1  # 假设模块编号从1开始，而数组从0开始
                self.parameter_storage.reactor = self.parameter_storage.reactors[module_number]
            elif combo_name == 'combo_port_post':
                self.parameter_storage.select_port_post = selected_value
            elif combo_name == 'combo_post_module':
                # 设置后处理模块，更新对应的地址信息
                module_number = int(selected_value) - 1  # 假设模块编号从1开始，而数组从0开始
                self.parameter_storage.posttreatmentmodule = self.parameter_storage.posttreatmentmodules[module_number]
            elif combo_name == 'combo_select_head':
                self.parameter_storage.select_test_head = int(selected_value)   # 假设模块编号从1开始，而数组从0开始
        
    def sync_all_combo_box_values(self):
        """同步所有comboBox的值到参数管理类"""
        combo_boxes = self.get_all_combo_boxes()
        
        for name, combo_box in combo_boxes.items():
            if combo_box is not None and combo_box.count() > 0:
                index = combo_box.currentIndex()
                if index >= 0:
                    self.on_combo_box_changed(name, index)
        
    def update_input_values(self):
        # 更新输入框中的值到参数管理类
        # 第一标签页：指定模块设置
        if self.main_ui.line_temp.hasAcceptableInput():
            self.parameter_storage.set_temperature = float(self.main_ui.line_temp.text())
        
        if self.main_ui.line_motor_speed.hasAcceptableInput():
            self.parameter_storage.set_motor_speed = int(self.main_ui.line_motor_speed.text())
        
        if self.main_ui.line_dosage_a.hasAcceptableInput():
            self.parameter_storage.set_dosage_a = float(self.main_ui.line_dosage_a.text())
        
        if self.main_ui.line_dosage_b.hasAcceptableInput():
            self.parameter_storage.set_dosage_b = float(self.main_ui.line_dosage_b.text())
        
        if self.main_ui.line_dosage_c.hasAcceptableInput():
            self.parameter_storage.set_dosage_c = float(self.main_ui.line_dosage_c.text())
        
        if self.main_ui.line_dosage_d.hasAcceptableInput():
            self.parameter_storage.set_dosage_d = float(self.main_ui.line_dosage_d.text())
        
        # 第二标签页：后处理模块设置
        if self.main_ui.line_dosage_inject_a.hasAcceptableInput():
            self.parameter_storage.set_dosage_inject_a = float(self.main_ui.line_dosage_inject_a.text())
        
        if self.main_ui.line_dosage_inject_b.hasAcceptableInput():
            self.parameter_storage.set_dosage_inject_b = float(self.main_ui.line_dosage_inject_b.text())
        
        if self.main_ui.line_dosage_inject_c.hasAcceptableInput():
            self.parameter_storage.set_dosage_inject_c = float(self.main_ui.line_dosage_inject_c.text())
        
        if self.main_ui.line_dosage_clean_a.hasAcceptableInput():
            self.parameter_storage.set_dosage_clean_a = float(self.main_ui.line_dosage_clean_a.text())
            
        if self.main_ui.line_dosage_clean_b.hasAcceptableInput():
            self.parameter_storage.set_dosage_clean_b = float(self.main_ui.line_dosage_clean_b.text())
        
        if self.main_ui.line_post_inject_speed_a.hasAcceptableInput():
            self.parameter_storage.set_post_inject_speed_a = float(self.main_ui.line_post_inject_speed_a.text())
        
        if self.main_ui.line_post_inject_speed_b.hasAcceptableInput():
            self.parameter_storage.set_post_inject_speed_b = float(self.main_ui.line_post_inject_speed_b.text())
        
        if self.main_ui.line_post_inject_speed_c.hasAcceptableInput():
            self.parameter_storage.set_post_inject_speed_c = float(self.main_ui.line_post_inject_speed_c.text())
        
        if self.main_ui.line_post_inject_speed_clean_a.hasAcceptableInput():
            self.parameter_storage.set_post_inject_speed_clean_a = float(self.main_ui.line_post_inject_speed_clean_a.text())
            
        if self.main_ui.line_post_inject_speed_clean_b.hasAcceptableInput():
            self.parameter_storage.set_post_inject_speed_clean_b = float(self.main_ui.line_post_inject_speed_clean_b.text())
        
        if self.main_ui.line_motor_speed_post.hasAcceptableInput():
            self.parameter_storage.set_motor_speed_post = int(self.main_ui.line_motor_speed_post.text())
        
                
        # 第三标签页：三轴位置标定
        # 标定位置坐标
        if self.main_ui.calib1_x.hasAcceptableInput():
            self.parameter_storage.set_calib1_x = float(self.main_ui.calib1_x.text())
        
        if self.main_ui.calib1_y.hasAcceptableInput():
            self.parameter_storage.set_calib1_y = float(self.main_ui.calib1_y.text())
        
        if self.main_ui.calib1_z.hasAcceptableInput():
            self.parameter_storage.set_calib1_z = float(self.main_ui.calib1_z.text())
        
        if self.main_ui.calib2_x.hasAcceptableInput():
            self.parameter_storage.set_calib2_x = float(self.main_ui.calib2_x.text())
        
        if self.main_ui.calib2_y.hasAcceptableInput():
            self.parameter_storage.set_calib2_y = float(self.main_ui.calib2_y.text())
        
        if self.main_ui.calib2_z.hasAcceptableInput():
            self.parameter_storage.set_calib2_z = float(self.main_ui.calib2_z.text())
        
        if self.main_ui.calib3_x.hasAcceptableInput():
            self.parameter_storage.set_calib3_x = float(self.main_ui.calib3_x.text())
        
        if self.main_ui.calib3_y.hasAcceptableInput():
            self.parameter_storage.set_calib3_y = float(self.main_ui.calib3_y.text())
        
        if self.main_ui.calib3_z.hasAcceptableInput():
            self.parameter_storage.set_calib3_z = float(self.main_ui.calib3_z.text())
        
        if self.main_ui.calib4_x.hasAcceptableInput():
            self.parameter_storage.set_calib4_x = float(self.main_ui.calib4_x.text())
        
        if self.main_ui.calib4_y.hasAcceptableInput():
            self.parameter_storage.set_calib4_y = float(self.main_ui.calib4_y.text())
        
        if self.main_ui.calib4_z.hasAcceptableInput():
            self.parameter_storage.set_calib4_z = float(self.main_ui.calib4_z.text())
        
        # 位置设定
        if self.main_ui.line_x_pos.hasAcceptableInput():
            self.parameter_storage.set_x_pos = float(self.main_ui.line_x_pos.text())
        
        if self.main_ui.line_y_pos.hasAcceptableInput():
            self.parameter_storage.set_y_pos = float(self.main_ui.line_y_pos.text())
        
        if self.main_ui.line_z_pos.hasAcceptableInput():
            self.parameter_storage.set_z_pos = float(self.main_ui.line_z_pos.text())
        
        if self.main_ui.line_x_speed.hasAcceptableInput():
            self.parameter_storage.set_x_speed = float(self.main_ui.line_x_speed.text())
        
        if self.main_ui.line_y_speed.hasAcceptableInput():
            self.parameter_storage.set_y_speed = float(self.main_ui.line_y_speed.text())
        
        if self.main_ui.line_z_speed.hasAcceptableInput():
            self.parameter_storage.set_z_speed = float(self.main_ui.line_z_speed.text())
        
        # 测试界面标签页
        if self.main_ui.line_dosage.hasAcceptableInput():
            self.parameter_storage.set_test_dosage = float(self.main_ui.line_dosage.text())
