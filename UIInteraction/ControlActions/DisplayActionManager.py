from UIInteraction.UIGenerator.MainUI import MainUI
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from UIInteraction.ControlActions.ButtonActionManager import ButtonActionManager
import time
from PySide6.QtCore import QObject, Signal, QThread

class UpdateThread(QThread):
    """更新线程，用于在子线程中定期发送更新信号"""
    update_signal = Signal()  # 定义更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.update_interval = 0.1  # 100ms
    
    def run(self):
        """线程运行方法，定期发送更新信号"""
        self.running = True
        while self.running:
            # 发送更新信号
            self.update_signal.emit()
            # 等待指定的更新间隔
            time.sleep(self.update_interval)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait(1000)  # 等待线程结束，最多等待1秒

class DisplayActionManager(QObject):
    def __init__(self, main_window:MainUI, param_storage:ParameterStorage, button_manager:ButtonActionManager):
        super().__init__()
        self.main_window = main_window
        self.param_storage = param_storage
        self.button_manager = button_manager
        
        # 创建并配置更新线程
        self.update_thread = UpdateThread(self)
        # 直接将子线程的更新信号连接到update_display函数
        self.update_thread.update_signal.connect(self.update_display)
        self.update_thread.start()
    
    def start(self):
        """启动更新线程"""
        self.update_thread.start()
    
    def stop(self):
        """停止更新线程"""
        self.update_thread.stop()
    
    def update_display(self):
        """
        更新显示，根据ParameterStorage中的参数刷新UI
        这个方法会在主线程中执行，确保UI更新的线程安全
        """
        if self.param_storage.is_reactor_connected:
            # 刷新电机速度显示
            current_speed = self.param_storage.get_motor_speed
            self.main_window.label_current_speed_value.setText(str(current_speed))

            # 刷新电机状态显示
            current_state = self.param_storage.get_motor_state
            text = "已停止" if current_state else "运行中"
            self.main_window.label_status_value.setText(str(text))

            # 刷新温度显示
            current_temp = self.param_storage.get_temprature
            self.main_window.label_realtime_temp_value.setText(str(current_temp))

        if self.param_storage.is_postprocessing_connected:
            # 刷新阀门状态
            # 气体阀门
            gas_valve_state = self.param_storage.get_gas_valve_state
            self.button_manager.set_button_color_by_status(self.main_window.btn_gas_valve, gas_valve_state)
            
            # 排放阀门
            discharge_valve_state = self.param_storage.get_discharge_valve_state
            self.button_manager.set_button_color_by_status(self.main_window.btn_discharge_valve, discharge_valve_state)

            # 回液阀门
            liquid_return_valve_state = self.param_storage.get_liquid_return_valve_state
            self.button_manager.set_button_color_by_status(self.main_window.btn_liquid_return_valve, liquid_return_valve_state)

            # 水阀门
            water_valve_state = self.param_storage.get_water_valve_state
            self.button_manager.set_button_color_by_status(self.main_window.btn_water_valve, water_valve_state)

