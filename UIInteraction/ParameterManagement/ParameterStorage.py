from Common import Global
from UIInteraction.ParameterManagement.TrayModel import TrayModel
from UIInteraction.ParameterManagement.TipRackModel import TipRackModel
from UIInteraction.ParameterManagement.RobotModel import RobotState
from UIInteraction.ParameterManagement.CleaningStationModel import CleaningStationState

class ParameterStorage:
    class Reactor:
        def __init__(self,number):
            self.temp_sense_address = Global.TEMP_SENSE_ADDRESSES[number]
            self.motor_axis = Global.MOTOR_AXIS_ADDRESSES[number]
            self.number=number

            self.motor_state = False
            self.motor_speed = 0
            self.temprature = 0.0
            # unilab查询状态量
            self.reactor_id=number  # 反应器编号
            self.current_temperature= 0.0  # 当前温度
            self.arget_temperature= 0.0  # 目标温度
            self.stirring_status= False  # 搅拌状态
            self.stirring_speed= 0.0  # 搅拌转速
            self.n2_status= False  # 氮气状态
            self.air_status= False  # 空气状态
            self.status= "idle"  # 运行状态：idle, running, error
            self.error_message = ""  # 错误信息

        def set(self,number):
            self.temp_sense_address = Global.TEMP_SENSE_ADDRESSES[number]
            self.motor_axis = Global.MOTOR_AXIS_ADDRESSES[number]
            self.number = number

            self.motor_state = False
            self.motor_speed = 0
            self.temprature = 0.0



    class PostTreatmentModule:
        def __init__(self,number):
            self.pump_address = Global.PUMP_ADDRESS[number]
            self.valve_address = Global.SWITCH_VALVE_ADDRESS[number]
            self.motor_address = Global.MOTOR485_ADDRESS[number]
            self.gas_valve = Global.GAS_VALVES[number]
            self.discharge_valve = Global.DISCHARGE_VALVES[number]
            self.liquid_return_valve = Global.LIQUID_RETURN_VALVES[number]
            self.number=number

            self.motor_state_post = False
            self.motor_speed_post = 0
            self.gas_valve_state = False
            self.discharge_valve_state = False
            self.liquid_return_valve_state = False
            self.water_valve_state = False
            #unilab查询状态量
            self.post_process_id=number # 后处理编号
            self.cleaning_status= False  # 清洗状态
            self.discharge_status= False  # 排液状态
            self.transferring_status = False  # 溶液转移状态
            self.start_bottle = ""  # 当前转移起始瓶
            self.end_bottle = ""  # 当前转移终点瓶
            self.current_volume = 0.0  # 当前转移体积
            self.target_volume = 0.0  # 目标转移体积
            self.status = "idle"  # 运行状态：idle, running, error
            self.error_message = ""  # 错误信息


        def set(self,number):
            self.pump_address = Global.PUMP_ADDRESS[number]
            self.valve_address = Global.SWITCH_VALVE_ADDRESS[number]
            self.motor_address = Global.MOTOR485_ADDRESS[number]
            self.gas_valve = Global.GAS_VALVES[number]
            self.discharge_valve = Global.DISCHARGE_VALVES[number]
            self.liquid_return_valve = Global.LIQUID_RETURN_VALVES[number]
            self.number=number

            self.motor_state_post = False
            self.motor_speed_post = 0
            self.gas_valve_state = False
            self.discharge_valve_state = False
            self.liquid_return_valve_state = False

    def __init__(self):
        #存储设置参数，从inputActionManager类中的输入框得到
        self.is_reactor_connected = False  # 反应器模块连接状态
        self.is_postprocessing_connected = False  # 后处理模块连接状态
        # 控制模式：True为本地控制模式，False为远程控制模式
        self.is_local_control = True  # 默认本地控制模式
        # 系统状态：True为系统正忙（执行动作中），False为空闲
        self.is_system_busy = False  # 默认系统空闲
        # 工艺流程异步执行状态（供 UDP 等查询，与 is_system_busy 含义独立）
        self.process_execution_running = False
        self.process_execution_filename = ""
        self.process_execution_current_step = 0
        self.process_execution_total_steps = 0
        self.process_execution_current_command = ""
        # 初始化所有可能用到的变量
        self.select_port = ''  # 反应器选择的串口
        self.select_port_fixpump = ''  # 固定泵选择的串口
        self.select_port_post = ''  # 后处理模块选择的串口
        
        # 实例化所有反应器并放入列表
        self.reactors = [self.Reactor(i) for i in range(len(Global.TEMP_SENSE_ADDRESSES))]
        # 实例化所有后处理模块并放入列表
        self.posttreatmentmodules = [self.PostTreatmentModule(i) for i in range(len(Global.PUMP_ADDRESS))]

        self.reactor = self.reactors[0]
        self.posttreatmentmodule=self.posttreatmentmodules[0]
        
        
        # 第一标签页：指定模块设置
        self.set_temperature = 0.0
        self.set_motor_speed = 0
        self.set_dosage_a = 0.0
        self.set_dosage_b = 0.0
        self.set_dosage_c = 0.0
        self.set_dosage_d = 0.0
        
        # 第二标签页：后处理模块设置
        self.set_dosage_inject_a = 0.0
        self.set_dosage_inject_b = 0.0
        self.set_dosage_inject_c = 0.0
        self.set_dosage_clean_a = 0.0
        self.set_dosage_clean_b = 0.0
        self.set_post_inject_speed_a = 0.0
        self.set_post_inject_speed_b = 0.0
        self.set_post_inject_speed_c = 0.0
        self.set_post_inject_speed_clean_a = 0.0
        self.set_post_inject_speed_clean_b = 0.0
        self.set_motor_speed_post = 0

               
        # 第三标签页：三轴位置标定
        # 标定位置坐标
        self.set_calib1_x = 0.0
        self.set_calib1_y = 0.0
        self.set_calib1_z = 0.0
        self.set_calib2_x = 0.0
        self.set_calib2_y = 0.0
        self.set_calib2_z = 0.0
        self.set_calib3_x = 0.0
        self.set_calib3_y = 0.0
        self.set_calib3_z = 0.0
        self.set_calib4_x = 0.0
        self.set_calib4_y = 0.0
        self.set_calib4_z = 0.0
        # 位置设定
        self.set_x_pos = 0.0
        self.set_y_pos = 0.0
        self.set_z_pos = 0.0
        self.set_x_speed = 0.0
        self.set_y_speed = 0.0
        self.set_z_speed = 0.0

        #反应器部分显示参数
        self.get_motor_state = False
        self.get_motor_speed = 0
        self.get_temprature = 0.0
        #后处理模块部分显示参数
        self.get_motor_state_post = False
        self.get_motor_speed_post = 0
        self.get_gas_valve_state = False
        self.get_discharge_valve_state = False
        self.get_liquid_return_valve_state = False
        self.get_water_valve_state = False
        
        # 测试界面标签页
        self.set_test_dosage = 0.0  # 加液量输入框
        self.select_test_head = 0  # 加液头选择下拉框
        # 测试选择泵、泵配套氮气阀门、配套进液阀门
        self.select_test_pump = 0  # 选择的泵索引

        # SolidDoser 料盘（仓位 1–32）
        self.tray = TrayModel()
        # SolidDoser 枪头架（枪头位 1–56）
        self.tip_rack = TipRackModel()
        # SolidDoser 机器人
        self.robot = RobotState()
        # SolidDoser 清洁工位
        self.cleaning_station = CleaningStationState()
