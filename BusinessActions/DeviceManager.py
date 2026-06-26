from Common.Global import *
from Drivers.EthernetDevices.ZMC import ZMC
from Drivers.SerialDevices.Motor485_ZhangDaTou import Motor_Bottom
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from Drivers.EthernetDevices.inovance_three_axis.inovance_three_axis import Inovance_Three_Axis
from Drivers.SerialDevices.Common_Serial import Common_Serial
from Drivers.EthernetDevices.MotorZmc import MotorZmc
from Drivers.EthernetDevices.SRND_16_IO import SRND_16_IO
from Drivers.SerialDevices.PumpController import FixPump, Pump
from Drivers.SerialDevices.SwitchValveController import SwitchValve
from Drivers.SerialDevices.Motor485_iDM42 import Motor
from Drivers.SerialDevices.TemperatureController import TemperatureController
from Drivers.EthernetDevices.Valve import Valve
from PySide6.QtCore import QThread, QTimer

class Solution_Add_Moudule:
    def __init__(self,number):
        self.fixpump=None
        self.gas_valve= None
        self.input_valve= None
        self.number=number

class DeviceManager:
    def __init__(self,parameter_storage:ParameterStorage):
        self.parameter_storage = parameter_storage
        #定义串口实例
        self.serial_port = None

        #定义后处理模块串口实例
        self.serial_port_post=None
        #正运动板卡控制实例
        self.zmc=None
        # IO控制实例
        self.io_control = None
        self.io_control_fixpump = None
        
        # 仿真模式输出变量
        self.simulation_mode = False

        

        #反应器部分所需用的实例
        self.temp_sensors=[]
        self.motorzmcs=[]
        #定量泵的实例的序号不与模块的序号相关，其序号只与加入的液体有关
        self.fixpumps=[]#加液模块所需要的定量泵实例
        self.fixpump_gas_valves=[]#加液模块所需要的通氮气阀门实例
        self.fixpump_input_valves=[]#加液模块所需要的进液阀门实例
        self.reactor_N2_valves=[]#N2通液阀门实例
        self.reactor_Air_valves=[]#Air通液阀门实例
        #三轴模块
        self.three_axis=None

        #后处理模块部分所需要用到的实例
        self.pumps=[]
        self.switch_valves=[]
        self.motors485=[]
        self.motors485_bottom=[]
        self.gas_valves=[]
        self.discharge_valves=[]
        self.liquid_return_valves=[]
        self.water_valves=[]

        self.current_temp_sensor=None
        self.current_motorzmc=None
        self.current_pump = None
        self.current_switch_valve = None
        self.current_motor485 = None
        self.current_motor485_bottom = None
        # 后处理模块阀门状态
        self.current_gas_valve = None  # 气体阀门点位
        self.current_discharge_valve = None  # 排放阀门点位
        self.current_liquid_return_valve = None #回液阀点位
        self.current_water_valve = None  # 水阀点位
        
        # 创建并启动参数监控线程
        self.parameter_monitor_thread = ParameterMonitorThread(self)
        self.parameter_monitor_thread.start()
    
    # # 测试用串口连接函数
    # def connect_test_serial_port(self):
    #     self.test_serial_port = Common_Serial(self.parameter_storage.select_test_port)

    # def connect_test_io_control(self):
    #     self.test_io_control = SRND_16_IO(address="192.168.1.7:23", slave_id=1, device_name="test")

    # def connect_test_fixpump(self):
    #     test_fixpump = FixPump(self.test_serial_port, 0x61)
    #     test_fixpump.reset()
    #     self.fixpumps.append(test_fixpump)
    #     gas_valve = Valve(self.test_io_control, 1)
    #     self.fixpump_gas_valves.append(gas_valve)
    #     input_valve = Valve(self.test_io_control, 0)
    #     self.fixpump_input_valves.append(input_valve)

    def connect_zmc(self):
        self.zmc=ZMC(ZMOTION_ADDRESS)

    def connect_serial_port(self):
        port = (self.parameter_storage.select_port or "").strip()
        if not port:
            print("未选择反应器串口，请先在下拉框中选择 COM 口")
            return False
        self.serial_port = Common_Serial(port)
        return True

    def connect_serila_port_fixpump(self):
        port = (self.parameter_storage.select_port_fixpump or "").strip()
        if not port:
            print("未选择定量泵串口")
            return False
        self.serial_port_fixpump = Common_Serial(port)
        return True

    def connect_serial_port_post(self):
        port = (self.parameter_storage.select_port_post or "").strip()
        if not port:
            print("未选择后处理串口，请先在下拉框中选择 COM 口")
            return False
        self.serial_port_post = Common_Serial(port)
        return True

    def connect_io_control(self):
        self.io_control = SRND_16_IO(address=SRND_IO_ADDRESS, slave_id=1, device_name="test")

    def connect_io_control_fixpump(self):
        self.io_control_fixpump = SRND_16_IO(address=SRND_IO_ADDRESS_2,slave_id=1, device_name="test")
    
    def connect_all_reactor_devices(self):
        for address in MOTOR_AXIS_ADDRESSES:
            if address != "":
                motorzmc = MotorZmc(self.zmc,address)
                self.motorzmcs.append(motorzmc)
        for address in TEMP_SENSE_ADDRESSES:
            if address != "":
                temp_sensor = TemperatureController(self.serial_port,address)
                self.temp_sensors.append(temp_sensor)

    def connect_all_fixpump_devices(self):
        for address in FIX_PUMP_ADDRESS:
            if address != "":
                fixpump = FixPump(self.serial_port, address)
                self.fixpumps.append(fixpump)
        for address in FIX_PUMP_GAS_VALVES:
            if address != "":
                gas_valve = Valve(self.io_control_fixpump, address)
                self.fixpump_gas_valves.append(gas_valve)
        for address in FIX_PUMP_INPUT_VALVES:
            if address != "":
                input_valve = Valve(self.io_control_fixpump, address)
                self.fixpump_input_valves.append(input_valve)
        for address in REACTOR_N2_VALVES:
            if address != "":
                N2_valve = Valve(self.io_control_fixpump, address)
                self.reactor_N2_valves.append(N2_valve)
        for address in REACTOR_AIR_VALVES:
            if address != "":
                Air_valve = Valve(self.io_control_fixpump, address)
                self.reactor_Air_valves.append(Air_valve)
        print("加液模块连接成功")

    def connect_three_axis_modules(self):
        self.three_axis = Inovance_Three_Axis(address="192.168.1.20", port="502")
        print("三轴模块连接成功")

    def connect_all_post_devices(self):
        for address in PUMP_ADDRESS:
            if address != "":
                pump = Pump(self.serial_port_post, int(address))
                self.pumps.append(pump)
        for address in SWITCH_VALVE_ADDRESS:
            if address != "":
                valve = SwitchValve(self.serial_port_post, int(address))
                self.switch_valves.append(valve)
        for address in MOTOR485_ADDRESS:
            if address != "":
                motor = Motor(self.serial_port_post, int(address))
                self.motors485.append(motor)
        for address in MOTOR485_BOTTOM_ADDRESS:
            if address != "":
                motor = Motor_Bottom(self.serial_port_post, int(address))
                self.motors485_bottom.append(motor)
        for address in GAS_VALVES:
            if address != "":
                gas_valve = Valve(self.io_control, int(address))
                self.gas_valves.append(gas_valve)
        for address in DISCHARGE_VALVES:
            if address != "":
                discharge_valve = Valve(self.io_control, int(address))
                self.discharge_valves.append(discharge_valve)
        for address in LIQUID_RETURN_VALVES:
            if address != "":
                liquid_return_valve = Valve(self.io_control, int(address))
                self.liquid_return_valves.append(liquid_return_valve)
        for address in WATER_VALVES:
            if address != "":
                water_valve = Valve(self.io_control, int(address))
                self.water_valves.append(water_valve)
    
    def disconnect_all_reactor_devices(self):
        self.parameter_storage.is_reactor_connected=False
        self.current_motorzmc=None
        self.current_temp_sensor=None
        self.motorzmcs=[]
        self.temp_sensors=[]
        if self.zmc:
            self.zmc.Close()
            self.zmc=None
            print("正运动连接卡已关闭")
        if self.serial_port:
            self.serial_port.ser.close()
            self.serial_port=None
            print("反应器串口已关闭")
    
    def disconnect_all_post_devices(self):
        self.parameter_storage.is_postprocessing_connected=False
        self.current_pump=None
        self.current_switch_valve=None
        self.current_motor485=None
        self.current_gas_valve=None
        self.current_discharge_valve=None
        self.current_liquid_return_valve=None
        self.current_water_valve=None
        self.pumps=[]
        self.switch_valves=[]
        self.motors485=[]
        self.motors485_bottom=[]
        self.gas_valves=[]
        self.discharge_valves=[]
        self.liquid_return_valves=[]
        self.water_valves=[]
        if self.serial_port_post:
            self.serial_port_post.close()
            self.serial_port_post=None
            print("后处理模块串口已关闭")

    def connnect_reactor_moudle(self):
        self.connect_zmc()#连接反应器底部搅拌电机
        if not self.connect_serial_port():#连接温度控制器和定量泵的串口
            return
        self.connect_all_reactor_devices()#实例化电机和温度控制器
        self.connect_io_control_fixpump()#连接控制N2和定量泵的板卡
        self.connect_all_fixpump_devices()#实例化定量泵及对应阀
        self.connect_three_axis_modules()#实例化三轴模块
        self.parameter_storage.is_reactor_connected=True

    def connect_post_module(self):
        if not self.connect_serial_port_post():
            return
        self.connect_io_control()
        self.connect_all_post_devices()
        self.parameter_storage.is_postprocessing_connected=True

    def stop_monitor_thread(self):
        """停止参数监控线程"""
        if hasattr(self, 'parameter_monitor_thread'):
            self.parameter_monitor_thread.stop()
    
    def toggle_simulation_mode(self):
        """切换仿真模式状态"""
        self.simulation_mode = not self.simulation_mode
        print(f"仿真模式已{'开启' if self.simulation_mode else '关闭'}")
        return self.simulation_mode


class ParameterMonitorThread(QThread):
    
    def __init__(self, device_manager:DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self.running = True
    
    def run(self):
        while self.running:
            self.check_and_update_parameters()
            # 每500ms检查一次参数变化
            self.msleep(500)
    
    def stop(self):
        self.running = False
        self.wait()
    
    def check_and_update_parameters(self):
        # 单独检查反应器串口连接状态
        if self.device_manager.serial_port:
            # 直接读取reactor变量的number值并赋值
            if hasattr(self.device_manager.parameter_storage, 'reactor') and hasattr(self.device_manager.parameter_storage.reactor, 'number'):
                try:
                    # 直接读取reactor变量的number值，转换为0-based索引
                    reactor_index = int(self.device_manager.parameter_storage.reactor.number)
                    if reactor_index >= 0 and reactor_index < len(self.device_manager.temp_sensors):
                        self.device_manager.current_temp_sensor = self.device_manager.temp_sensors[reactor_index]
                    if reactor_index >= 0 and reactor_index < len(self.device_manager.motorzmcs):
                        self.device_manager.current_motorzmc = self.device_manager.motorzmcs[reactor_index]
                except (ValueError, TypeError):
                    pass
        
        # 单独检查后处理模块串口连接状态
        if self.device_manager.serial_port_post:
            # 直接读取post_module变量的number值并赋值
            if hasattr(self.device_manager.parameter_storage, 'posttreatmentmodule') and hasattr(self.device_manager.parameter_storage.posttreatmentmodule, 'number'):
                try:
                    # 直接读取post_module变量的number值，转换为0-based索引
                    post_module_index = int(self.device_manager.parameter_storage.posttreatmentmodule.number)
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.pumps):
                        self.device_manager.current_pump = self.device_manager.pumps[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.switch_valves):
                        self.device_manager.current_switch_valve = self.device_manager.switch_valves[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.motors485):
                        self.device_manager.current_motor485 = self.device_manager.motors485[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.motors485_bottom):
                        self.device_manager.current_motor485_bottom = self.device_manager.motors485_bottom[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.gas_valves):
                        self.device_manager.current_gas_valve = self.device_manager.gas_valves[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.discharge_valves):
                        self.device_manager.current_discharge_valve = self.device_manager.discharge_valves[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.liquid_return_valves):
                        self.device_manager.current_liquid_return_valve = self.device_manager.liquid_return_valves[post_module_index]
                    if post_module_index >= 0 and post_module_index < len(self.device_manager.water_valves):
                        self.device_manager.current_water_valve = self.device_manager.water_valves[post_module_index]
                except (ValueError, TypeError):
                    pass
