from BusinessActions import DeviceManager
from Drivers.EthernetDevices.inovance_three_axis.inovance_three_axis import Inovance_Three_Axis
from enum import IntEnum
from BusinessActions.UIFeedback import UIFeedbackHandler
import threading


class AxisPosition(IntEnum):
    """
    三轴目标位置枚举
    """
    HOME = 0
    Reactor_1 = 1
    Reactor_2 = 2
    Reactor_3 = 3
    Reactor_4 = 4
    Adder_1 = 5
    Adder_2 = 6
    Adder_3 = 7
    Adder_4 = 8
    Adder_5 = 9
    Reactor_5 = 10
    Reactor_6 = 11
    Reactor_7 = 12
    Reactor_8 = 13


def Axis_Power_on(deviceManager:DeviceManager):
    """
    三轴上电动作
    :param DeviceManager: 设备管理器实例
    """
    three_axis = deviceManager.three_axis
    if isinstance(three_axis,Inovance_Three_Axis):
        three_axis.axis_x_power_on()
        three_axis.axis_y_power_on()
        three_axis.axis_z_power_on()

def Axis_Origin(deviceManager:DeviceManager):
    """
    三轴原点动作
    :param DeviceManager: 设备管理器实例
    """
    three_axis = deviceManager.three_axis
    if isinstance(three_axis,Inovance_Three_Axis):
        three_axis.axis_z_origin()
        three_axis.axis_x_origin()
        three_axis.axis_y_origin()
        
def Axis_Origin_With_UISignal(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    带UI信号的三轴原点动作
    在执行前后发送UI信号，控制测试界面的按钮和进度条状态
    
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例
    """
    try:
        # 发送测试开始信号，禁用测试界面按钮并设置进度条为不定形式
        ui_feedback.test_start_signal.emit()
        print("发送测试开始信号，禁用测试界面按钮")
        
        # 执行三轴原点动作
        Axis_Origin(deviceManager)
        print("执行三轴原点动作")
        
        # 发送测试结束信号，激活测试界面按钮并重置进度条
        ui_feedback.test_stop_signal.emit()
        print("发送测试结束信号，激活测试界面按钮")
    except Exception as e:
        print(f"执行带UI信号的三轴原点动作时发生错误: {e}")
        # 即使发生错误，也要发送测试结束信号，确保界面状态正确
        ui_feedback.test_stop_signal.emit()


def Axis_Origin_In_Thread(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    在子线程中执行带UI信号的三轴原点动作
    
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例
    """
    # 使用threading.Thread创建并启动线程
    thread = threading.Thread(target=Axis_Origin_With_UISignal, args=(deviceManager, ui_feedback))
    thread.start()
    print("启动三轴原点动作子线程")


def Axis_Reset(deviceManager:DeviceManager):
    """
    三轴复位动作
    :param DeviceManager: 设备管理器实例
    """
    three_axis = deviceManager.three_axis
    if isinstance(three_axis,Inovance_Three_Axis):
        three_axis.axis_x_reset()
        three_axis.axis_y_reset()
        three_axis.axis_z_reset()

def Axis_Move(deviceManager:DeviceManager,position:AxisPosition):
    """
    三轴移动动作
    :param DeviceManager: 设备管理器实例
    :param position: 目标位置，单位毫米
    """
    three_axis = deviceManager.three_axis
    if isinstance(three_axis,Inovance_Three_Axis):
        if position == AxisPosition.HOME:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_home_pos()
            three_axis.axis_y_home_pos()
        elif position == AxisPosition.Reactor_1:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_2()
            three_axis.axis_y_pos_2()
            three_axis.axis_z_pos_2()
        elif position == AxisPosition.Reactor_2:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_3()
            three_axis.axis_y_pos_3()
            three_axis.axis_z_pos_3()
        elif position == AxisPosition.Reactor_3:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_4()
            three_axis.axis_y_pos_4()
            three_axis.axis_z_pos_4()
        elif position == AxisPosition.Reactor_4:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_5()
            three_axis.axis_y_pos_5()
            three_axis.axis_z_pos_5()
        elif position == AxisPosition.Adder_1:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_6()
            three_axis.axis_y_pos_6()
            three_axis.axis_z_pos_6()
        elif position == AxisPosition.Adder_2:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_7()
            three_axis.axis_y_pos_7()
            three_axis.axis_z_pos_7()
        elif position == AxisPosition.Adder_3:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_8()
            three_axis.axis_y_pos_8()
            three_axis.axis_z_pos_8()
        elif position == AxisPosition.Adder_4:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_9()
            three_axis.axis_y_pos_9()
            three_axis.axis_z_pos_9()
        elif position == AxisPosition.Adder_5:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_10()
            three_axis.axis_y_pos_10()
            three_axis.axis_z_pos_10()
        elif position == AxisPosition.Reactor_5:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_11()
            three_axis.axis_y_pos_11()
            three_axis.axis_z_pos_11()
        elif position == AxisPosition.Reactor_6:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_12()
            three_axis.axis_y_pos_12()
            three_axis.axis_z_pos_12()
        elif position == AxisPosition.Reactor_7:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_13()
            three_axis.axis_y_pos_13()
            three_axis.axis_z_pos_13()
        elif position == AxisPosition.Reactor_8:
            three_axis.axis_z_home_pos()
            three_axis.axis_x_pos_14()
            three_axis.axis_y_pos_14()
            three_axis.axis_z_pos_14()
        else:
            print("位置参数错误")


def Axis_Move_With_UISignal(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler, position:AxisPosition):
    """
    带UI信号的三轴移动动作
    在执行前后发送UI信号，控制测试界面的按钮和进度条状态
    
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例
    :param position: 目标位置
    """
    try:
        # 发送测试开始信号，禁用测试界面按钮并设置进度条为不定形式
        ui_feedback.test_start_signal.emit()
        print("发送测试开始信号，禁用测试界面按钮")
        
        # 执行三轴移动动作
        Axis_Move(deviceManager, position)
        print(f"执行三轴移动到位置: {position.name}")
        
        # 发送测试结束信号，激活测试界面按钮并重置进度条
        ui_feedback.test_stop_signal.emit()
        print("发送测试结束信号，激活测试界面按钮")
    except Exception as e:
        print(f"执行带UI信号的三轴移动时发生错误: {e}")
        # 即使发生错误，也要发送测试结束信号，确保界面状态正确
        ui_feedback.test_stop_signal.emit()


def Axis_Move_In_Thread(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler, position:AxisPosition):
    """
    在子线程中执行带UI信号的三轴移动动作（精简版）
    
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例
    :param position: 目标位置
    """
    # 使用QRunnable和QThreadPool实现一句话创建并启动线程
    thread=threading.Thread(target=Axis_Move_With_UISignal, args=(deviceManager, ui_feedback, position))
    thread.start()
    print("启动三轴移动子线程")

def Gripper_init(deviceManager:DeviceManager):
    """
     gripper 初始化动作
    :param DeviceManager: 设备管理器实例
    """
    gripper = deviceManager.three_axis
    if isinstance(gripper,Inovance_Three_Axis):
        gripper.gripper_init()

def Gripper_init_With_UISignal(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    带UI反馈的gripper初始化动作，执行前后发送UI信号
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    try:
        # 发送UI更新信号，控制测试界面状态
        ui_feedback.test_start_signal.emit()
        
        # 执行夹爪初始化动作
        Gripper_init(deviceManager)
        
        # 发送UI更新信号，恢复测试界面状态
        ui_feedback.test_stop_signal.emit()
    except Exception as e:
        print(f"执行夹爪初始化动作时发生错误: {e}")
        # 即使发生错误，也要恢复UI状态
        ui_feedback.test_stop_signal.emit()

def Gripper_init_In_Thread(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    在子线程中执行带UI信号的夹爪初始化动作
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    # 使用threading.Thread创建并启动线程
    thread=threading.Thread(target=Gripper_init_With_UISignal, args=(deviceManager, ui_feedback))
    thread.start()
    print("启动夹爪初始化子线程")

def Gripper_on(deviceManager:DeviceManager):
    """
     gripper 夹取动作
    :param DeviceManager: 设备管理器实例
    """
    gripper = deviceManager.three_axis
    if isinstance(gripper,Inovance_Three_Axis):
        gripper.gripper_on()

def Gripper_on_With_UISignal(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    带UI反馈的gripper夹取动作，执行前后发送UI信号
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    try:
        # 发送UI更新信号，控制测试界面状态
        ui_feedback.test_start_signal.emit()
        
        # 执行夹爪夹取动作
        Gripper_on(deviceManager)
        
        # 发送UI更新信号，恢复测试界面状态
        ui_feedback.test_stop_signal.emit()
    except Exception as e:
        print(f"执行夹爪夹取动作时发生错误: {e}")
        # 即使发生错误，也要恢复UI状态
        ui_feedback.test_stop_signal.emit()

def Gripper_on_In_Thread(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    在子线程中执行带UI信号的夹爪夹取动作
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    # 使用threading.Thread创建并启动线程
    thread=threading.Thread(target=Gripper_on_With_UISignal, args=(deviceManager, ui_feedback))
    thread.start()
    print("启动夹爪夹取子线程")

def Gripper_off(deviceManager:DeviceManager):
    """
     gripper 松开动作
    :param DeviceManager: 设备管理器实例
    """
    gripper = deviceManager.three_axis
    if isinstance(gripper,Inovance_Three_Axis):
        gripper.gripper_off()

def Gripper_off_With_UISignal(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    带UI反馈的gripper松开动作，执行前后发送UI信号
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    try:
        # 发送UI更新信号，控制测试界面状态
        ui_feedback.test_start_signal.emit()
        
        # 执行夹爪松开动作
        Gripper_off(deviceManager)
        
        # 发送UI更新信号，恢复测试界面状态
        ui_feedback.test_stop_signal.emit()
    except Exception as e:
        print(f"执行夹爪松开动作时发生错误: {e}")
        # 即使发生错误，也要恢复UI状态
        ui_feedback.test_stop_signal.emit()

def Gripper_off_In_Thread(deviceManager:DeviceManager, ui_feedback:UIFeedbackHandler):
    """
    在子线程中执行带UI信号的夹爪松开动作
    :param deviceManager: 设备管理器实例
    :param ui_feedback: UI反馈处理器实例，用于发送UI更新信号
    """
    # 使用threading.Thread创建并启动线程
    thread=threading.Thread(target=Gripper_off_With_UISignal, args=(deviceManager, ui_feedback))
    thread.start()
    print("启动夹爪松开子线程")

