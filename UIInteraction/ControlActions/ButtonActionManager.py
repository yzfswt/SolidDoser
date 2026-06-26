from UIInteraction.UIGenerator.MainUI import MainUI
import serial.tools.list_ports
from PySide6.QtWidgets import QComboBox, QMessageBox, QPushButton
from PySide6.QtCore import QThread, Signal
from BusinessActions.SingleStepActions.MotorAction import *
from BusinessActions.SingleStepActions.TemperatureControlAction import *
from BusinessActions.SingleStepActions.ValveAction import *
from BusinessActions.MultiStepActions.MultiStepActionManager import *
from BusinessActions.DeviceManager import DeviceManager
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from BusinessActions.UIFeedback.UIFeedbackHandler import UIFeedbackHandler
from ActionSequence.execute_sequence import *
from BusinessActions.SingleStepActions.AxisSingleStepAction import *
from Common.ActionLogger import get_action_logger

class ProcessExecutionThread(QThread):
    """工艺执行线程类，用于异步执行工艺流程"""
    # 定义信号
    finished = Signal(str)  # 执行完成信号，参数为状态消息
    error = Signal(str)  # 错误信号，参数为错误消息
    status = Signal(str)  # 状态信号，参数为状态消息
    # 执行进度：当前步(1-based 执行前为 0 表示已就绪)、总步数
    progress = Signal(int, int)
    interrupted = Signal()  # 用户中止执行（未走 error/finished）
    process_started = Signal(str, int)  # 工艺文件名、总步数（主线程更新查询用）
    
    def __init__(self, device_manager:DeviceManager, parent=None):
        """初始化工艺执行线程
        
        Args:
            device_manager (DeviceManager): 设备管理器实例
            parent: 父对象
        """
        super().__init__(parent)
        self.device_manager = device_manager
        self.is_running = False
    
    def run(self):
        """线程执行方法，在子线程中执行工艺流程"""
        self.is_running = True
        
        try:
            # 从数据库获取当前活跃的工艺文件
            filename, content = get_active_process_file()
            
            if not filename or not content:
                self.error.emit("没有找到可执行的工艺文件，请先导入工艺文件！")
                return
            
            self.status.emit(f"开始执行工艺文件：{filename}")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # 生成执行序列
                exec_seq = generate_execution_sequence(temp_file_path)
                
                if not exec_seq:
                    self.error.emit("工艺文件中没有有效命令！")
                    return
                
                # 处理参数
                processed_seq = process_parameters_by_function(exec_seq, self.device_manager)
                
                total = len(processed_seq)
                self.process_started.emit(filename, total)
                self.progress.emit(0, total)
                
                ok = self._execute_sequence(processed_seq)
                if ok:
                    self.progress.emit(total, total)
                    self.finished.emit(f"工艺文件执行完成：{filename}")
                elif not self.is_running:
                    self.interrupted.emit()
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        
        except Exception as e:
            error_msg = f"执行工艺文件时发生错误：{str(e)}"
            self.error.emit(error_msg)
    
    def _execute_sequence(self, sequence):
        """遍历序列，按顺序执行每个函数（在线程中运行）
        
        Returns:
            bool: 全部步骤执行成功为 True；用户停止或某步失败为 False
        """
        if not sequence:
            return True
        
        for idx, (func, args) in enumerate(sequence, 1):
            if not self.is_running:
                return False
            
            self.progress.emit(idx, len(sequence))
            self.status.emit(f"执行第 {idx}/{len(sequence)} 个命令：{func.__name__}")
            
            try:
                args_repr = str(args)
                if len(args_repr) > 200:
                    args_repr = args_repr[:200] + "..."
                get_action_logger().record(
                    f"工艺流程步骤 {idx}/{len(sequence)}: {func.__name__} 参数: {args_repr}"
                )
                func(*args)
            except Exception as e:
                self.error.emit(f"第 {idx} 个命令执行失败：{str(e)}")
                return False
        return True
    
    def stop(self):
        """停止执行"""
        self.is_running = False

class ButtonActionManager:
    """按钮控件管理器类，用于管理和处理所有按钮的事件"""
    
    def __init__(self, main_window:MainUI,device_manager:DeviceManager,param_storage:ParameterStorage,ui_feedback:UIFeedbackHandler):
        """初始化按钮控件管理器类
        
        Args:
            main_window (QMainWindow): 主窗口实例，用于访问和操作UI元素
        """
        self.main_window = main_window
        self.device_manager=device_manager
        self.param_storage=param_storage
        self.ui_feedback=ui_feedback
        self.setup_button_connections()

    def _logged_call(self, description: str, fn, *args, **kwargs):
        get_action_logger().record(description)
        return fn(*args, **kwargs)

    def _logged_run(self, description: str, fn):
        get_action_logger().record(description)
        return fn()
    
    def setup_button_connections(self):
        """
        设置所有按钮的信号槽连接
        """
        # 连接刷新串口按钮的点击信号
        self.main_window.btn_refresh_port.clicked.connect(
            lambda: self._logged_call("刷新反应器串口列表", self.refresh_serial_ports, self.main_window.combo_port)
        )
        self.main_window.btn_refresh_port_post.clicked.connect(
            lambda: self._logged_call("刷新后处理串口列表", self.refresh_serial_ports, self.main_window.combo_port_post)
        )
        
        # 连接控制模式切换按钮的点击信号
        self.main_window.btn_mode_switch.clicked.connect(
            lambda: self._logged_run("切换本地/远程控制模式", self.toggle_control_mode)
        )
       
        
        self.main_window.btn_connect.clicked.connect(
            lambda: self._logged_run("反应器模块连接", self.device_manager.connnect_reactor_moudle)
        )
        self.main_window.btn_connect_post.clicked.connect(
            lambda: self._logged_run("后处理模块连接", self.device_manager.connect_post_module)
        )
        self.main_window.btn_disconnect.clicked.connect(
            lambda: self._logged_run("反应器模块断开", self.device_manager.disconnect_all_reactor_devices)
        )
        self.main_window.btn_disconnect_post.clicked.connect(
            lambda: self._logged_run("后处理模块断开", self.device_manager.disconnect_all_post_devices)
        )
        self.main_window.btn_start_motor.clicked.connect(
            lambda: self._logged_call("反应器搅拌启动", Motor_zmc_start_stirrer, self.device_manager.current_motorzmc, self.param_storage.set_motor_speed)
        )
        self.main_window.btn_stop_motor.clicked.connect(
            lambda: self._logged_call("反应器搅拌停止", Motor_zmc_stop_stirrer, self.device_manager.current_motorzmc)
        )
        self.main_window.btn_start_bottom_motor.clicked.connect(
            lambda: self._logged_call("底部485电机启动", Motor_Bottom_start_stirrer, self.device_manager.current_motor485_bottom)
        )
        self.main_window.btn_stop_bottom_motor.clicked.connect(
            lambda: self._logged_call("底部485电机停止", Motor_Bottom_stop_stirrer, self.device_manager.current_motor485_bottom)
        )

        self.main_window.btn_temp_set.clicked.connect(
            lambda: self._logged_call("反应器温度设定", TemperatureControl_set_temperature, self.device_manager.current_temp_sensor, self.param_storage.set_temperature)
        )
        self.main_window.btn_start_motor_post.clicked.connect(
            lambda: self._logged_call("后处理搅拌启动", Motor_485_idm42_start_stirrer, self.device_manager.current_motor485, self.param_storage.set_motor_speed_post)
        )
        self.main_window.btn_stop_motor_post.clicked.connect(
            lambda: self._logged_call("后处理搅拌停止", Motor_485_idm42_stop_stirrer, self.device_manager.current_motor485)
        )
        self.main_window.btn_gas_valve.clicked.connect(
            lambda: self._logged_call("后处理气阀切换", Valve_change_state, self.device_manager.current_gas_valve)
        )
        self.main_window.btn_discharge_valve.clicked.connect(
            lambda: self._logged_call("后处理排液阀切换", Valve_change_state, self.device_manager.current_discharge_valve)
        )
        self.main_window.btn_liquid_return_valve.clicked.connect(
            lambda: self._logged_call("后处理回液阀切换", Valve_change_state, self.device_manager.current_liquid_return_valve)
        )
        self.main_window.btn_water_valve.clicked.connect(
            lambda: self._logged_call("后处理水阀切换", Valve_change_state, self.device_manager.current_water_valve)
        )
        #反应器添加溶液部分按钮连接
        self.main_window.btn_add_solution_a.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_add_solution_a,"blue")
        )
        self.main_window.btn_add_solution_a.clicked.connect(
            lambda: self._logged_call(
                "反应器加液：溶液A", Add_Solution_to_Reactor_Bond,
                self.device_manager, self.ui_feedback, 1, self.param_storage.set_dosage_a, self.param_storage.reactor.number
            )
        )
        self.main_window.btn_add_solution_b.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_add_solution_b, "blue")
        )
        self.main_window.btn_add_solution_b.clicked.connect(
            lambda: self._logged_call(
                "反应器加液：溶液B", Add_Solution_to_Reactor_Bond,
                self.device_manager, self.ui_feedback, 2, self.param_storage.set_dosage_b, self.param_storage.reactor.number
            )
        )
        self.main_window.btn_add_solution_c.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_add_solution_c, "blue")
        )
        self.main_window.btn_add_solution_c.clicked.connect(
            lambda: self._logged_call(
                "反应器加液：溶液C", Add_Solution_to_Reactor_Bond,
                self.device_manager, self.ui_feedback, 3, self.param_storage.set_dosage_c, self.param_storage.reactor.number
            )
        )
        self.main_window.btn_add_solution_d.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_add_solution_d, "blue")
        )
        self.main_window.btn_add_solution_d.clicked.connect(
            lambda: self._logged_call(
                "反应器加液：溶液D", Add_Solution_to_Reactor_Bond,
                self.device_manager, self.ui_feedback, 4, self.param_storage.set_dosage_d, self.param_storage.reactor.number
            )
        )

        #后处理部分添加溶液按钮连接
        self.main_window.btn_inject_solution_a.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_inject_solution_a,"blue")
        )
        self.main_window.btn_inject_solution_a.clicked.connect(
            lambda: self._logged_call(
                "后处理注入：反应液", Add_reactsolution_Post,
                self.device_manager, self.ui_feedback, self.param_storage.set_dosage_inject_a, self.param_storage.set_post_inject_speed_a, self.param_storage.posttreatmentmodule.number
            )
        )
        self.main_window.btn_inject_solution_b.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_inject_solution_b, "blue")
        )
        self.main_window.btn_inject_solution_b.clicked.connect(
            lambda: self._logged_call(
                "后处理注入：良溶剂", Add_goodsolution_Post,
                self.device_manager, self.ui_feedback, self.param_storage.set_dosage_inject_b, self.param_storage.set_post_inject_speed_b, self.param_storage.posttreatmentmodule.number
            )
        )
        
        self.main_window.btn_inject_solution_c.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_inject_solution_c, "blue")
        )       
        self.main_window.btn_inject_solution_c.clicked.connect(
            lambda: self._logged_call(
                "后处理注入：不良溶剂", Add_badsolution_Post,
                self.device_manager, self.ui_feedback, self.param_storage.set_dosage_inject_c, self.param_storage.set_post_inject_speed_c, self.param_storage.posttreatmentmodule.number
            )
        )
        self.main_window.btn_clean_step_a.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_clean_step_a, "blue")
        )
        self.main_window.btn_clean_step_a.clicked.connect(
            lambda: self._logged_call(
                "后处理清洁步骤A", Clean_Step_A_Post,
                self.device_manager, self.ui_feedback, self.param_storage.set_dosage_clean_a, self.param_storage.set_post_inject_speed_clean_a, self.param_storage.posttreatmentmodule.number
            )
        )
        self.main_window.btn_clean_step_b.clicked.connect(
            lambda: self.set_button_color(self.main_window.btn_clean_step_b, "blue")
        )
        self.main_window.btn_clean_step_b.clicked.connect(
            lambda: self._logged_call(
                "后处理清洁步骤B", Clean_Step_B_Post,
                self.device_manager, self.ui_feedback, self.param_storage.set_dosage_clean_b, self.param_storage.set_post_inject_speed_clean_b, self.param_storage.posttreatmentmodule.number
            )
        )
        #自动流程按钮绑定
        self.main_window.btn_settle_module1.clicked.connect(
            lambda: self._logged_call("自动化：模块1沉降程序", Auto_SettleProgram_Bond, self.device_manager, self.ui_feedback, 0)
        )
        self.main_window.btn_clean_module1.clicked.connect(
            lambda: self._logged_call("自动化：模块1清洁程序", Auto_CleanProgram_Bond, self.device_manager, self.ui_feedback, 0)
        )
        self.main_window.btn_settle_module2.clicked.connect(
            lambda: self._logged_call("自动化：模块2沉降程序", Auto_SettleProgram_Bond, self.device_manager, self.ui_feedback, 1)
        )
        self.main_window.btn_clean_module2.clicked.connect(
            lambda: self._logged_call("自动化：模块2清洁程序", Auto_CleanProgram_Bond, self.device_manager, self.ui_feedback, 1)
        )
        self.main_window.btn_settle_module3.clicked.connect(
            lambda: self._logged_call("自动化：模块3沉降程序", Auto_SettleProgram_Bond, self.device_manager, self.ui_feedback, 2)
        )
        self.main_window.btn_clean_module3.clicked.connect(
            lambda: self._logged_call("自动化：模块3清洁程序", Auto_CleanProgram_Bond, self.device_manager, self.ui_feedback, 2)
        )
        self.main_window.btn_settle_module4.clicked.connect(
            lambda: self._logged_call("自动化：模块4沉降程序", Auto_SettleProgram_Bond, self.device_manager, self.ui_feedback, 3)
        )
        self.main_window.btn_clean_module4.clicked.connect(
            lambda: self._logged_call("自动化：模块4清洁程序", Auto_CleanProgram_Bond, self.device_manager, self.ui_feedback, 3)
        )

        self.process_execution_thread = None
        
        #工艺流程导入按钮绑定
        self.main_window.btn_import_process.clicked.connect(
            lambda: self._logged_call("工艺流程：从文件导入", Import_Process_Bond, self.main_window.table_process)
        )
        
        #工艺流程执行按钮绑定 - 使用异步执行
        self.main_window.btn_execute_process.clicked.connect(self.execute_process_async)

        #测试按钮绑定
        # 抓取加液头按钮绑定
        self.main_window.btn_grab_a.clicked.connect(
            lambda: self._logged_call("三轴：移动至加液头A", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Adder_1)
        )
        self.main_window.btn_grab_b.clicked.connect(
            lambda: self._logged_call("三轴：移动至加液头B", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Adder_2)
        )
        self.main_window.btn_grab_c.clicked.connect(
            lambda: self._logged_call("三轴：移动至加液头C", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Adder_3)
        )
        self.main_window.btn_grab_d.clicked.connect(
            lambda: self._logged_call("三轴：移动至加液头D", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Adder_4)
        )
        self.main_window.btn_grab_e.clicked.connect(
            lambda: self._logged_call("三轴：移动至加液头E", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Adder_5)
        )
        
        # 反应器点位按钮绑定
        self.main_window.btn_reactor_1.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器1", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_1)
        )
        self.main_window.btn_reactor_2.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器2", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_2)
        )
        self.main_window.btn_reactor_3.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器3", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_3)
        )
        self.main_window.btn_reactor_4.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器4", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_4)
        )
        self.main_window.btn_reactor_5.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器5", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_5)
        )
        self.main_window.btn_reactor_6.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器6", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_6)
        )
        self.main_window.btn_reactor_7.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器7", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_7)
        )
        self.main_window.btn_reactor_8.clicked.connect(
            lambda: self._logged_call("三轴：移动至反应器8", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.Reactor_8)
        )
        # 待机位置点位按钮绑定
        self.main_window.btn_return_standby.clicked.connect(
            lambda: self._logged_call("三轴：返回待机位", Axis_Move_In_Thread, self.device_manager, self.ui_feedback, AxisPosition.HOME)
        )
        # 夹爪控制按钮绑定
        self.main_window.btn_init_claw.clicked.connect(
            lambda: self._logged_call("夹爪：初始化", Gripper_init_In_Thread, self.device_manager, self.ui_feedback)
        )
        self.main_window.btn_grip_claw.clicked.connect(
            lambda: self._logged_call("夹爪：夹紧", Gripper_on_In_Thread, self.device_manager, self.ui_feedback)
        )
        self.main_window.btn_release_claw.clicked.connect(
            lambda: self._logged_call("夹爪：松开", Gripper_off_In_Thread, self.device_manager, self.ui_feedback)
        )
        
        # 轴控制按钮绑定
        self.main_window.btn_axis_power_on.clicked.connect(
            lambda: self._logged_call("三轴：上电", Axis_Power_on, self.device_manager)
        )
        self.main_window.btn_axis_home.clicked.connect(
            lambda: self._logged_call("三轴：回原点", Axis_Origin_In_Thread, self.device_manager, self.ui_feedback)
        )
        self.main_window.btn_axis_reset.clicked.connect(
            lambda: self._logged_call("三轴：复位", Axis_Reset, self.device_manager)
        )
        # 测试用泵按钮绑定
        self.main_window.btn_add_liquid.clicked.connect(
            lambda: self._logged_call(
                "测试：定量泵加液", FixPump_Inject_In_Thread,
                self.device_manager, self.ui_feedback, self.param_storage.select_test_head, self.param_storage.set_test_dosage
            )
        )
        self.main_window.btn_reset_pump.clicked.connect(
            lambda: self._logged_call("测试：定量泵复位", FixPump_reset, self.device_manager, self.param_storage.select_test_head)
        )
        # 测试界面 多步动作按钮绑定
        self.main_window.btn_test_multi_step.clicked.connect(
            lambda: self._logged_call("测试：多步动作", Test_MultiStepAction_Bond, self.device_manager, self.ui_feedback)
        )
        
        # 仿真模式按钮绑定
        self.main_window.btn_simulation_mode.clicked.connect(
            lambda: self._logged_run("切换仿真模式", self.toggle_simulation_mode)
        )
        
        # 反应器气阀控制按钮绑定
        self.main_window.btn_valve_open_1.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块1开启", Reactor_N2_on, self.device_manager, 1)
        )
        self.main_window.btn_valve_open_2.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块2开启", Reactor_N2_on, self.device_manager, 2)
        )
        self.main_window.btn_valve_open_3.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块3开启", Reactor_N2_on, self.device_manager, 3)
        )
        self.main_window.btn_valve_open_4.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块4开启", Reactor_N2_on, self.device_manager, 4)
        )
        self.main_window.btn_valve_open_5.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块5开启", Reactor_N2_on, self.device_manager, 5)
        )
        self.main_window.btn_valve_open_6.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块6开启", Reactor_N2_on, self.device_manager, 6)
        )
        self.main_window.btn_valve_open_7.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块7开启", Reactor_N2_on, self.device_manager, 7)
        )
        self.main_window.btn_valve_open_8.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块8开启", Reactor_N2_on, self.device_manager, 8)
        )
        
        self.main_window.btn_valve_close_1.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块1关闭", Reactor_N2_off, self.device_manager, 1)
        )
        self.main_window.btn_valve_close_2.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块2关闭", Reactor_N2_off, self.device_manager, 2)
        )
        self.main_window.btn_valve_close_3.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块3关闭", Reactor_N2_off, self.device_manager, 3)
        )
        self.main_window.btn_valve_close_4.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块4关闭", Reactor_N2_off, self.device_manager, 4)
        )
        self.main_window.btn_valve_close_5.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块5关闭", Reactor_N2_off, self.device_manager, 5)
        )
        self.main_window.btn_valve_close_6.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块6关闭", Reactor_N2_off, self.device_manager, 6)
        )
        self.main_window.btn_valve_close_7.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块7关闭", Reactor_N2_off, self.device_manager, 7)
        )
        self.main_window.btn_valve_close_8.clicked.connect(
            lambda: self._logged_call("反应器N2通：模块8关闭", Reactor_N2_off, self.device_manager, 8)
        )
        # 为测试界面所有按钮（除了加液和复位）添加点击变蓝色的绑定
        test_buttons = [
            # 抓取加液头按钮
            self.main_window.btn_grab_a, self.main_window.btn_grab_b, 
            self.main_window.btn_grab_c, self.main_window.btn_grab_d, 
            self.main_window.btn_grab_e,
            # 反应器点位按钮
            self.main_window.btn_reactor_1, self.main_window.btn_reactor_2, 
            self.main_window.btn_reactor_3, self.main_window.btn_reactor_4,
            self.main_window.btn_reactor_5, self.main_window.btn_reactor_6,
            self.main_window.btn_reactor_7, self.main_window.btn_reactor_8,
            # 夹爪控制按钮
            self.main_window.btn_init_claw, self.main_window.btn_grip_claw, 
            self.main_window.btn_release_claw,
            # 轴控制按钮
            self.main_window.btn_axis_power_on, self.main_window.btn_axis_home, 
            self.main_window.btn_axis_reset
        ]
        
        for button in test_buttons:
            button.clicked.connect(lambda checked, btn=button: self.set_button_color(btn,"blue"))


    def refresh_serial_ports(self, combo_box:QComboBox):
        """
        扫描当前可用串口，并将其添加到传入的QComboBox控件中
        :param combo_box: QComboBox控件
        """
        combo_box.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            combo_box.addItem(port.device)
    
    def set_button_color(self, button: QPushButton,color:str):
        """
        设置按钮颜色，根据阀门状态或指定为蓝色
        
        Args:
            button (QPushButton): 需要设置颜色的按钮
            is_open (bool, optional): 阀门状态，True表示开启（绿色），False表示关闭（红色）
            is_blue (bool): 是否强制设置为蓝色状态
        """
        if color=="blue":
            # 蓝色状态
            button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: 1px solid #1976D2;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """)
        elif color=="green":
            # 开启状态：绿色
            button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 1px solid #45a049;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
        elif color=="red":
            # 关闭状态：红色
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: 1px solid #da190b;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:pressed {
                    background-color: #ba160c;
                }
            """)

    def execute_process_async(self):
        """异步执行工艺流程"""
        # 如果已有线程在运行，先停止
        if self.process_execution_thread is not None and self.process_execution_thread.isRunning():
            self.process_execution_thread.stop()
            self.process_execution_thread.wait()
        
        # 设置系统状态为忙
        self.param_storage.is_system_busy = True
        self.param_storage.process_execution_running = True
        self.param_storage.process_execution_filename = ""
        self.param_storage.process_execution_current_step = 0
        self.param_storage.process_execution_total_steps = 0
        
        self.main_window.label_progress.setText("执行进度: 0/0")
        self.main_window.progress_bar.setRange(0, 1)
        self.main_window.progress_bar.setValue(0)
        
        # 创建新的执行线程
        self.process_execution_thread = ProcessExecutionThread(self.device_manager)
        
        # 连接信号槽
        self.process_execution_thread.status.connect(self._on_execution_status)
        self.process_execution_thread.progress.connect(self._on_process_progress)
        self.process_execution_thread.finished.connect(self._on_execution_finished)
        self.process_execution_thread.error.connect(self._on_execution_error)
        self.process_execution_thread.interrupted.connect(self._on_process_interrupted)
        self.process_execution_thread.process_started.connect(self._on_process_started)
        
        get_action_logger().record("开始异步执行工艺流程（UI）")
        # 启动线程
        self.process_execution_thread.start()
    
    def _on_execution_status(self, message):
        """处理执行状态更新"""
        print(f"📋 {message}")
        # 可以在这里添加UI更新逻辑，如在状态栏显示消息
    
    def _on_process_progress(self, current: int, total: int):
        """更新工艺流程标签页：第几步 / 总计几步"""
        if total <= 0:
            self.main_window.label_progress.setText("执行进度: 0/0")
            self.main_window.progress_bar.setRange(0, 1)
            self.main_window.progress_bar.setValue(0)
            self.param_storage.process_execution_current_step = 0
            self.param_storage.process_execution_total_steps = 0
            return
        self.param_storage.process_execution_current_step = current
        self.param_storage.process_execution_total_steps = total
        self.main_window.label_progress.setText(f"执行进度: {current}/{total}")
        self.main_window.progress_bar.setRange(0, total)
        self.main_window.progress_bar.setValue(min(max(current, 0), total))
    
    def _on_process_started(self, filename: str, total: int):
        self.param_storage.process_execution_filename = filename or ""
        self.param_storage.process_execution_total_steps = total
        self.param_storage.process_execution_current_step = 0
    
    def _on_execution_finished(self, message):
        """处理执行完成"""
        print(f"✅ {message}")
        total = self.main_window.progress_bar.maximum()
        if total > 0:
            self.main_window.label_progress.setText(f"执行进度: {total}/{total}")
            self.main_window.progress_bar.setValue(total)
        #self.ui_feedback.show_message("执行完成", message)
        self.param_storage.is_system_busy = False
        self._clear_process_execution_state()
    
    def _on_execution_error(self, message):
        """处理执行错误"""
        print(f"❌ {message}")
        self.main_window.label_progress.setText("执行进度: 0/0")
        self.main_window.progress_bar.setRange(0, 1)
        self.main_window.progress_bar.setValue(0)
        self.ui_feedback.show_error("执行错误", message)
        self.param_storage.is_system_busy = False
        self._clear_process_execution_state()
    
    def _on_process_interrupted(self):
        """工艺线程被 stop() 中止时释放忙状态并复位进度显示"""
        self.main_window.label_progress.setText("执行进度: 0/0")
        self.main_window.progress_bar.setRange(0, 1)
        self.main_window.progress_bar.setValue(0)
        self.param_storage.is_system_busy = False
        self._clear_process_execution_state()
    
    def _clear_process_execution_state(self):
        self.param_storage.process_execution_running = False
        self.param_storage.process_execution_filename = ""
        self.param_storage.process_execution_current_step = 0
        self.param_storage.process_execution_total_steps = 0
    
    def toggle_control_mode(self):
        """
        切换控制模式：本地控制模式 <-> 远程控制模式
        """
        # 切换控制模式标志
        self.param_storage.is_local_control = not self.param_storage.is_local_control
        
        # 更新按钮文本和样式
        if self.param_storage.is_local_control:
            self.main_window.btn_mode_switch.setText('本地控制模式')
            self.main_window.btn_mode_switch.setStyleSheet("""
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
        else:
            self.main_window.btn_mode_switch.setText('远程控制模式')
            self.main_window.btn_mode_switch.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 20px;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
        
        # 更新所有控件的启用状态
        self.update_all_controls_status()
    
    def update_all_controls_status(self):
        """
        根据当前控制模式更新所有控件的启用状态
        本地控制模式：所有控件可用
        远程控制模式：所有可动按钮和输入文本框不可用，仅保留显示功能
        """
        # 获取当前控制模式
        is_local = self.param_storage.is_local_control
        
        # 所有标签页的可动控件列表
        # 第一标签页：指定模块设置
        tab1_controls = [
            self.main_window.btn_connect, self.main_window.btn_disconnect,
            self.main_window.combo_port, self.main_window.btn_refresh_port,
            self.main_window.combo_reactor, self.main_window.btn_start_motor,
            self.main_window.btn_stop_motor, self.main_window.line_motor_speed,
            self.main_window.btn_temp_set, self.main_window.line_temp,
            self.main_window.btn_vacuum, self.main_window.btn_add_solution_a,
            self.main_window.btn_add_solution_b, self.main_window.btn_add_solution_c,
            self.main_window.btn_add_solution_d, self.main_window.line_dosage_a,
            self.main_window.line_dosage_b, self.main_window.line_dosage_c,
            self.main_window.line_dosage_d
        ]
        
        # 第二标签页：后处理模块设置
        tab2_controls = [
            self.main_window.btn_connect_post, self.main_window.btn_disconnect_post,
            self.main_window.btn_emergency_stop, self.main_window.combo_port_post,
            self.main_window.btn_refresh_port_post, self.main_window.combo_post_module,
            self.main_window.combo_valve_output,
            self.main_window.btn_inject_solution_a, self.main_window.btn_inject_solution_b,
            self.main_window.btn_inject_solution_c, self.main_window.btn_clean_step_a,
            self.main_window.btn_clean_step_b, self.main_window.line_dosage_inject_a,
            self.main_window.line_dosage_inject_b, self.main_window.line_dosage_inject_c,
            self.main_window.line_dosage_clean_a, self.main_window.line_dosage_clean_b,
            self.main_window.btn_start_motor_post, self.main_window.btn_stop_motor_post
        ]
        
        # 第三标签页：三轴位置标定
        tab3_controls = [
            # 这里需要根据实际的三轴位置标定标签页控件添加
        ]
        
        # 第四标签页：自动化程序
        tab4_controls = [
            self.main_window.btn_settle_module1, self.main_window.btn_clean_module1,
            self.main_window.btn_settle_module2, self.main_window.btn_clean_module2,
            self.main_window.btn_settle_module3, self.main_window.btn_clean_module3,
            self.main_window.btn_settle_module4, self.main_window.btn_clean_module4
        ]
        
        # 第五标签页：工艺流程导入
        tab5_controls = [
            self.main_window.btn_import_process, self.main_window.btn_execute_process
        ]
        
        # 第六标签页：测试界面
        tab6_controls = [
            # 抓取加液头按钮
            self.main_window.btn_grab_a, self.main_window.btn_grab_b, 
            self.main_window.btn_grab_c, self.main_window.btn_grab_d, 
            self.main_window.btn_grab_e,
            # 反应器点位按钮
            self.main_window.btn_reactor_1, self.main_window.btn_reactor_2, 
            self.main_window.btn_reactor_3, self.main_window.btn_reactor_4,
            self.main_window.btn_reactor_5, self.main_window.btn_reactor_6,
            self.main_window.btn_reactor_7, self.main_window.btn_reactor_8,
            # 待机位置按钮
            self.main_window.btn_return_standby,
            # 夹爪控制按钮
            self.main_window.btn_init_claw, self.main_window.btn_grip_claw, 
            self.main_window.btn_release_claw,
            # 轴控制按钮
            self.main_window.btn_axis_power_on, self.main_window.btn_axis_home, 
            self.main_window.btn_axis_reset,
            # 测试用泵按钮
            self.main_window.btn_add_liquid, self.main_window.btn_reset_pump,
            self.main_window.line_dosage, self.main_window.combo_select_head,
            # 多步动作按钮
            self.main_window.btn_test_multi_step
        ]
        
        # 合并所有控件列表
        all_controls = tab1_controls + tab2_controls + tab3_controls + tab4_controls + tab5_controls + tab6_controls
        
        # 更新所有控件的启用状态
        for control in all_controls:
            control.setEnabled(is_local)
    
    def set_button_color_by_status(self, button, status):
        """
        根据逻辑值设置按钮颜色

        Args:
            button (QPushButton): 要设置颜色的按钮
            status (bool): 逻辑状态值，True为绿色，False为红色
        """
        if status:
            # 逻辑值为真时，设置按钮为绿色
            button.setStyleSheet("""
                QPushButton {
                    background-color: green;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #2e7d32;
                    border-radius: 5px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #2e7d32;
                }
                QPushButton:pressed {
                    background-color: #1b5e20;
                }
            """)
        else:
            # 逻辑值为假时，设置按钮为红色
            button.setStyleSheet("""
                QPushButton {
                    background-color: red;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #d32f2f;
                    border-radius: 5px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:pressed {
                    background-color: #b71c1c;
                }
            """)
    
    def toggle_simulation_mode(self):
        """
        切换仿真模式状态
        """
        # 调用设备管理器的切换仿真模式方法
        current_mode = self.device_manager.toggle_simulation_mode()
        
        # 更新按钮文本和样式
        if current_mode:
            self.main_window.btn_simulation_mode.setText('仿真模式: 开启')
            self.main_window.btn_simulation_mode.setStyleSheet("""
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
        else:
            self.main_window.btn_simulation_mode.setText('仿真模式: 关闭')
            self.main_window.btn_simulation_mode.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    font-size: 20px;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
                QPushButton:pressed {
                    background-color: #ef6c00;
                }
            """)