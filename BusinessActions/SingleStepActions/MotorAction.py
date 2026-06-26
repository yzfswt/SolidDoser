from BusinessActions.DeviceManager import DeviceManager
from Drivers.EthernetDevices.MotorZmc import MotorZmc
from Drivers.SerialDevices.Motor485_iDM42 import Motor
from Drivers.SerialDevices.Motor485_ZhangDaTou import Motor_Bottom
import time

def Motor_zmc_start_stirrer(motor:MotorZmc,speed:float):
    if motor is None:
        print("搅拌电机未连接")
        return
    motor.StartStirrer(speed)

def Motor_zmc_stop_stirrer(motor:MotorZmc):
    if motor is None:
        print("搅拌电机未连接")
        return
    motor.StopStirrer()

def Motor_zmc_get_state(motor:MotorZmc):
    return motor.get_state()

def Motor_zmc_get_speed(motor:MotorZmc):
    return motor.get_speed()

def Motor_485_idm42_start_stirrer(motor:Motor,speed:int):
    motor.set_speed(speed)
    time.sleep(0.5)
    motor.Run()

def Motor_485_idm42_stop_stirrer(motor:Motor):
    motor.stop()

def Motor_485_idm42_time_stir(motor:Motor,speed:int,time_sec:int):
    motor.timed_stir(speed,time_sec)

def Motor_485_idm42_get_state(motor:Motor):
    return motor.get_state()

def Motor_485_idm42_get_speed(motor:Motor):
    return motor.get_speed()

def Motor_Bottom_start_stirrer(motor:Motor_Bottom):
    motor.Run()
    
def Motor_Bottom_stop_stirrer(motor:Motor_Bottom):
    motor.stop()

def Start_Reactor_Stirrer(device_manager:DeviceManager,reactor_id:int,speed:float):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器搅拌器启动 - 反应器: {reactor_id}, 速度: {speed} RPM")
        return
    if device_manager.motorzmcs:
        motor = device_manager.motorzmcs[reactor_id-1]# 索引从0开始，reactor_id从1开始
        Motor_zmc_start_stirrer(motor,speed)

def Stop_Reactor_Stirrer(device_manager:DeviceManager,reactor_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器搅拌器停止 - 反应器: {reactor_id}")
        return
    if device_manager.motorzmcs:
        motor = device_manager.motorzmcs[reactor_id-1]# 索引从0开始，reactor_id从1开始
        Motor_zmc_stop_stirrer(motor)

def Wait(time_sec:int):
    for elapsed_time in range(1, time_sec + 1):
        time.sleep(1)
        print(f"当前步骤需等待反应处理，已等待 {elapsed_time} /{time_sec}秒")