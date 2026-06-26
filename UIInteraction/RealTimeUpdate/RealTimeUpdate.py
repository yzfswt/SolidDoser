from BusinessActions.DeviceManager import DeviceManager
from BusinessActions.DeviceManager import DeviceManager
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
import threading
import time

class RealTimeUpdate:
    def __init__(self, device_manager:DeviceManager, param_storage:ParameterStorage):
        self.device_manager = device_manager
        self.param_storage = param_storage
        
        # 线程相关属性
        self.running = False
        self.update_thread = None
        self.update_interval = 5  # 更新间隔，单位：秒
        self.start()
    
    def start(self):
        """启动更新线程"""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True  # 设置为守护线程，主线程结束时自动结束
            self.update_thread.start()
    
    def stop(self):
        """停止更新线程"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5.0)  # 等待线程结束，最多等待5秒
    
    def _update_loop(self):
        """线程的主循环，以固定间隔（0.5秒）执行update函数"""
        while self.running:
            try:
                # 执行更新操作
                self.update()
            except Exception as e:
                print(f"线程执行update函数时出错: {e}")
            
            # 等待指定的更新间隔（0.5秒）
            # 使用小步长的sleep循环，这样可以更快响应running标志的变化
            wait_start = time.time()
            while self.running and time.time() - wait_start < self.update_interval:
                time.sleep(0.01)  # 10ms的小步长
    
    def update(self):
        """执行特定的函数并获取对应值，在参数管理器中进行更新"""
        # 如果系统正忙（执行动作中），则跳过实时更新
        if self.param_storage.is_system_busy:
            return
            
        if self.param_storage.is_reactor_connected:
            try:
                motor_state = self.device_manager.current_motorzmc.get_state()
                motor_speed = self.device_manager.current_motorzmc.get_speed()
                temperature = self.device_manager.current_temp_sensor.read_temperature()

                self.param_storage.get_motor_state = motor_state
                self.param_storage.get_motor_speed = motor_speed
                self.param_storage.get_temprature = temperature

                # for i in range(len(self.device_manager.motorzmcs)):
                #     motorzmc = self.device_manager.motorzmcs[i]
                #     self.param_storage.reactors[i].motor_state = motorzmc.get_state()
                #     self.param_storage.reactors[i].motor_speed = motorzmc.get_speed()
                #
                # for i in range(len(self.device_manager.temp_sensors)):
                #     temp_sensor = self.device_manager.temp_sensors[i]
                #     self.param_storage.reactors[i].temprature = temp_sensor.read_temperature()

            except Exception as e:
                print(f"更新实时参数时出错: {e}")
                
        if self.param_storage.is_postprocessing_connected:
            try:
                gas_valve_state = self.device_manager.current_gas_valve.get_state()
                discharge_valve_state = self.device_manager.current_discharge_valve.get_state()
                liquid_return_valve_state = self.device_manager.current_liquid_return_valve.get_state()
                water_valve_state = self.device_manager.current_water_valve.get_state()

                self.param_storage.get_gas_valve_state = gas_valve_state
                self.param_storage.get_discharge_valve_state = discharge_valve_state
                self.param_storage.get_liquid_return_valve_state = liquid_return_valve_state
                self.param_storage.get_water_valve_state = water_valve_state

                # for i in range(len(self.device_manager.posttreatmentmodules)):
                #     gas_valve=self.device_manager.gas_valves[i]
                #     self.param_storage.posttreatmentmodules[i].gas_valve_state = gas_valve.get_state()
                #
                #     discharge_valve=self.device_manager.discharge_valves[i]
                #     self.param_storage.posttreatmentmodules[i].discharge_valve_state = discharge_valve.get_state()
                #
                #     liquid_return_valve=self.device_manager.liquid_return_valves[i]
                #     self.param_storage.posttreatmentmodules[i].liquid_return_valve_state = liquid_return_valve.get_state()
                #
                #     water_valve=self.device_manager.water_valves[i]
                #     self.param_storage.posttreatmentmodules[i].water_valve_state = water_valve.get_state()

            except Exception as e:
                print(f"更新实时参数时出错: {e}")