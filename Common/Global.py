from enum import IntEnum

# SolidDoser 使用 AM600-CPU1608TN，通讯参数见 Common/PlcConfig.py
from Common.PlcConfig import PLC_ADDRESS, PLC_PORT_STR as PLC_PORT

ZMOTION_ADDRESS = "192.168.1.11"  # 遗留配置，SolidDoser 主程序未使用
SRND_IO_ADDRESS = "192.168.1.8:23"
SRND_IO_ADDRESS_2 = "192.168.1.9:25"
SRND_IO_SLAVE_ID = 1

class Bottle(IntEnum):
    Reaction = 3
    GoodSolution = 2
    BadSolution = 1
    TheBigBottle = 4
    Air = 5
    

# 温度传感器地址列表 (索引0-24对应模块1-25)
'''温度传感器地址列表用于存储每个模块的温度传感器地址，'''
TEMP_SENSE_ADDRESSES = [
    13,  # 模块1温度传感器地址
    14,  # 模块2温度传感器地址
    15,  # 模块3温度传感器地址
    16,  # 模块4温度传感器地址
    17,  # 模块5温度传感器地址
    18,  # 模块6温度传感器地址
    19,  # 模块7温度传感器地址
    20,  # 模块8温度传感器地址
    "",  # 模块9温度传感器地址
    "",  # 模块10温度传感器地址
    "",  # 模块11温度传感器地址
    "",  # 模块12温度传感器地址
    "",  # 模块13温度传感器地址
    "",  # 模块14温度传感器地址
    "",  # 模块15温度传感器地址
    "",  # 模块16温度传感器地址
    "",  # 模块17温度传感器地址
    "",  # 模块18温度传感器地址
    "",  # 模块19温度传感器地址
    "",  # 模块20温度传感器地址
    "",  # 模块21温度传感器地址
    "",  # 模块22温度传感器地址
    "",  # 模块23温度传感器地址
    "",  # 模块24温度传感器地址
    "",  # 模块25温度传感器地址
]

# 正运动轴电机轴地址列表 (索引0-24对应模块1-25)
MOTOR_AXIS_ADDRESSES = [
    0,  # 模块1电机轴地址
    1,  # 模块2电机轴地址
    2,  # 模块3电机轴地址
    3,  # 模块4电机轴地址
    4,  # 模块5电机轴地址
    5,  # 模块6电机轴地址
    6,  # 模块7电机轴地址
    7,  # 模块8电机轴地址
    8,  # 模块9电机轴地址
    9,  # 模块10电机轴地址
    10,  # 模块11电机轴地址
    11,  # 模块12电机轴地址
    12,  # 模块13电机轴地址
    13,  # 模块14电机轴地址
    14,  # 模块15电机轴地址
    15,  # 模块16电机轴地址
    16,  # 模块17电机轴地址
    17,  # 模块18电机轴地址
    18,  # 模块19电机轴地址
    19,  # 模块20电机轴地址
    20,  # 模块21电机轴地址
    21,  # 模块22电机轴地址
    22,  # 模块23电机轴地址
    23,  # 模块24电机轴地址
    24,  # 模块25电机轴地址
]

# 泵地址列表 (索引0-11对应模块1-12)
PUMP_ADDRESS = [
    0x1F,  # 模块1泵地址
    0x1D,  # 模块2泵地址
    0x25,  # 模块3泵地址
    0x03,  # 模块4泵地址
    "",  # 模块5泵地址
    "",  # 模块6泵地址
    "",  # 模块7泵地址
    "",  # 模块8泵地址
    "",  # 模块9泵地址
    "",  # 模块10泵地址
    "",  # 模块11泵地址
    "",  # 模块12泵地址
]

FIX_PUMP_ADDRESS = [
    0x5B,  # 模块1定量泵地址
    0x5C,  # 模块2定量泵地址
    0x5D,  # 模块3定量泵地址
    0x5E,  # 模块4定量泵地址
    0x5F,  # 模块5定量泵地址
    "",  # 模块6定量泵地址
    "",  # 模块7定量泵地址
    "",  # 模块8定量泵地址
    "",  # 模块9定量泵地址
    "",  # 模块10定量泵地址
    "",  # 模块11定量泵地址
    "",  # 模块12定量泵地址
]

# 阀门地址列表 (索引0-11对应模块1-12)
SWITCH_VALVE_ADDRESS = [
    0x21,  # 模块1阀门地址
    0x24,  # 模块2阀门地址
    0X27,  # 模块3阀门地址
    0x29,  # 模块4阀门地址
    "",  # 模块5阀门地址
    "",  # 模块6阀门地址
    "",  # 模块7阀门地址
    "",  # 模块8阀门地址
    "",  # 模块9阀门地址
    "",  # 模块10阀门地址
    "",  # 模块11阀门地址
    "",  # 模块12阀门地址
]

# 485电机地址列表 (索引0-11对应模块1-12)
MOTOR485_ADDRESS = [
    0x04,  # 模块1 485电机地址
    0x06,  # 模块2 485电机地址
    0X08,  # 模块3 485电机地址
    0x02,  # 模块4 485电机地址
    "",  # 模块5 485电机地址
    "",  # 模块6 485电机地址
    "",  # 模块7 485电机地址
    "",  # 模块8 485电机地址
    "",  # 模块9 485电机地址
    "",  # 模块10 485电机地址
    "",  # 模块11 485电机地址
    "",  # 模块12 485电机地址
]
MOTOR485_BOTTOM_ADDRESS = [
    0x01,  # 模块1  底部485电机地址
    0x42,  # 模块2 底部485电机地址
    0x41,  # 模块3 底部485电机地址
    0x40,  # 模块4 底部485电机地址
    "",  # 模块5 底部485电机地址
    "",  # 模块6 底部485电机地址
    "",  # 模块7 底部485电机地址
    "",  # 模块8 底部485电机地址
    "",  # 模块9 底部485电机地址
    "",  # 模块10 底部485电机地址
    "",  # 模块11 底部485电机地址
    "",  # 模块12 底部485电机地址
]

#IO口点位配置
class IO_POINT(IntEnum):
    Gas_Valve_1 = 0     # 气阀1
    Water_Valve_1 = 1  # 水阀1
    Discharge_Valve_1 = 2  # 排液阀
    Liquid_Return_Valve_1 = 3  # 液体回收阀
    
    
    Gas_Valve_2 = 4  # 气阀1
    Water_Valve_2 = 5  # 水阀1
    Discharge_Valve_2 = 6  # 排液阀
    Liquid_Return_Valve_2= 7  # 液体回收阀
    
    
    Gas_Valve_3 = 8  # 气阀1
    Water_Valve_3 = 9  # 水阀1
    Discharge_Valve_3 = 10  # 排液阀
    Liquid_Return_Valve_3 = 11  # 液体回收阀
    
    
    Gas_Valve_4 = 12  # 气阀1
    Water_Valve_4 = 13  # 水阀1
    Discharge_Valve_4 = 14  # 排液阀
    Liquid_Return_Valve_4 = 15  # 液体回收阀
    
    
    Gas_Valve_5 = 16  # 气阀1
    Water_Valve_5 = 17  # 水阀1
    Discharge_Valve_5 = 18  # 排液阀
    Liquid_Return_Valve_5 = 19  # 液体回收阀
    
    
    Gas_Valve_6 = 20  # 气阀1
    Water_Valve_6 = 21  # 水阀1
    Discharge_Valve_6 = 22  # 排液阀
    Liquid_Return_Valve_6 = 23  # 液体回收阀
    
    
    Gas_Valve_7 = 0  # 气阀1
    Water_Valve_7 = 1  # 水阀1
    Discharge_Valve_7 = 2  # 排液阀
    Liquid_Return_Valve_7 = 3  # 液体回收阀
    
    
    Gas_Valve_8 = 4  # 气阀1
    Water_Valve_8 = 5  # 水阀1
    Discharge_Valve_8 = 6  # 排液阀
    Liquid_Return_Valve_8 = 7  # 液体回收阀
    
    
    Gas_Valve_9 = 8  # 气阀1
    Water_Valve_9 = 9  # 水阀1
    Discharge_Valve_9 = 10  # 排液阀
    Liquid_Return_Valve_9 = 11  # 液体回收阀
    
    
    Gas_Valve_10 = 12  # 气阀1
    Water_Valve_10 = 13  # 水阀1
    Discharge_Valve_10 = 14  # 排液阀
    Liquid_Return_Valve_10 = 15  # 液体回收阀
    
    
    Gas_Valve_11 = 16  # 气阀1
    Water_Valve_11 = 17  # 水阀1
    Discharge_Valve_11 = 18  # 排液阀
    Liquid_Return_Valve_11 = 19  # 液体回收阀
    
    
    Gas_Valve_12 = 20  # 气阀1
    Water_Valve_12 = 21  # 水阀1
    Discharge_Valve_12 = 22  # 排液阀
    Liquid_Return_Valve_12 = 23  # 液体回收阀
    

    General_gas_valve = 24  # 总气阀
    #定量泵的控制阀门用不同板卡
    FixPump_Input_Valve_1 = 8  # 加液模块通氮气阀门
    FixPump_Gas_Valve_1 = 9  # 加液模块进液阀门
    FixPump_Input_Valve_2 = 10  # 加液模块通氮气阀门
    FixPump_Gas_Valve_2 = 11  # 加液模块进液阀门
    FixPump_Input_Valve_3 = 12  # 加液模块通氮气阀门
    FixPump_Gas_Valve_3 = 13  # 加液模块进液阀门
    FixPump_Input_Valve_4 = 14  # 加液模块通氮气阀门
    FixPump_Gas_Valve_4 = 15  # 加液模块进液阀门
    FixPump_Input_Valve_5 = 16  # 加液模块通氮气阀门
    FixPump_Gas_Valve_5 = 17  # 加液模块进液阀门
    FixPump_Input_Valve_6 = 18  # 加液模块通氮气阀门
    FixPump_Gas_Valve_6 = 19  # 加液模块进液阀门
    FixPump_Input_Valve_7 = 20  # 加液模块通氮气阀门
    FixPump_Gas_Valve_7 = 21  # 加液模块进液阀门
    FixPump_Input_Valve_8 = 22  # 加液模块通氮气阀门
    FixPump_Gas_Valve_8 = 23  # 加液模块进液阀门

    Reactor_N2_Valve_1 = 0  # 加液模块通氮气阀门
    Reactor_N2_Valve_2 = 1  # 加液模块通氮气阀门
    Reactor_N2_Valve_3 = 2  # 加液模块通氮气阀门
    Reactor_N2_Valve_4 = 3  # 加液模块通氮气阀门
    Reactor_N2_Valve_5 = 4  # 加液模块通氮气阀门
    Reactor_N2_Valve_6 = 5  # 加液模块通氮气阀门
    Reactor_N2_Valve_7 = 6  # 加液模块通氮气阀门
    Reactor_N2_Valve_8 = 7  # 加液模块通氮气阀门

    Reactor_AIR_Valve_1=18  # 加液模块通空气阀门
    Reactor_AIR_Valve_2=19  # 加液模块通空气阀门
    Reactor_AIR_Valve_3=20  # 加液模块通空气阀门
    Reactor_AIR_Valve_4=21  # 加液模块通空气阀门
    Reactor_AIR_Valve_5=22  # 加液模块通空气阀门
    Reactor_AIR_Valve_6=23  # 加液模块通空气阀门
    Reactor_AIR_Valve_7=24  # 加液模块通空气阀门
    Reactor_AIR_Valve_8=25  # 加液模块通空气阀门
    


# 气阀点位列表
GAS_VALVES=[
    IO_POINT.Gas_Valve_1,  # 模块1 气阀点位
    IO_POINT.Gas_Valve_2,  # 模块2 气阀点位
    IO_POINT.Gas_Valve_3,  # 模块3 气阀点位
    IO_POINT.Gas_Valve_4,  # 模块4 气阀点位
    IO_POINT.Gas_Valve_5,  # 模块5 气阀点位
    IO_POINT.Gas_Valve_6,  # 模块6 气阀点位
    IO_POINT.Gas_Valve_7,  # 模块7 气阀点位
    IO_POINT.Gas_Valve_8,  # 模块8 气阀点位
    IO_POINT.Gas_Valve_9,  # 模块9 气阀点位
    IO_POINT.Gas_Valve_10,  # 模块10 气阀点位
    IO_POINT.Gas_Valve_11,  # 模块11 气阀点位
    IO_POINT.Gas_Valve_12,  # 模块12 气阀点位
]
#排液阀点位列表
DISCHARGE_VALVES=[
    IO_POINT.Discharge_Valve_1,  # 模块1 排液阀点位
    IO_POINT.Discharge_Valve_2,  # 模块2 排液阀点位
    IO_POINT.Discharge_Valve_3,  # 模块3 排液阀点位
    IO_POINT.Discharge_Valve_4,  # 模块4 排液阀点位
    IO_POINT.Discharge_Valve_5,  # 模块5 排液阀点位
    IO_POINT.Discharge_Valve_6,  # 模块6 排液阀点位
    IO_POINT.Discharge_Valve_7,  # 模块7 排液阀点位
    IO_POINT.Discharge_Valve_8,  # 模块8 排液阀点位
    IO_POINT.Discharge_Valve_9,  # 模块9 排液阀点位
    IO_POINT.Discharge_Valve_10,  # 模块10 排液阀点位
    IO_POINT.Discharge_Valve_11,  # 模块11 排液阀点位
    IO_POINT.Discharge_Valve_12,  # 模块12 排液阀点位
]
#回液阀点位列表
LIQUID_RETURN_VALVES=[
    IO_POINT.Liquid_Return_Valve_1,  # 模块1 回液阀点位
    IO_POINT.Liquid_Return_Valve_2,  # 模块2 回液阀点位
    IO_POINT.Liquid_Return_Valve_3,  # 模块3 回液阀点位
    IO_POINT.Liquid_Return_Valve_4,  # 模块4 回液阀点位
    IO_POINT.Liquid_Return_Valve_5,  # 模块5 回液阀点位
    IO_POINT.Liquid_Return_Valve_6,  # 模块6 回液阀点位
    IO_POINT.Liquid_Return_Valve_7,  # 模块7 回液阀点位
    IO_POINT.Liquid_Return_Valve_8,  # 模块8 回液阀点位
    IO_POINT.Liquid_Return_Valve_9,  # 模块9 回液阀点位
    IO_POINT.Liquid_Return_Valve_10,  # 模块10 回液阀点位
    IO_POINT.Liquid_Return_Valve_11,  # 模块11 回液阀点位
    IO_POINT.Liquid_Return_Valve_12,  # 模块12 回液阀点位
]

WATER_VALVES=[
    IO_POINT.Water_Valve_1,  # 模块1 水阀点位
    IO_POINT.Water_Valve_2,  # 模块2 水阀点位
    IO_POINT.Water_Valve_3,  # 模块3 水阀点位
    IO_POINT.Water_Valve_4,  # 模块4 水阀点位
    IO_POINT.Water_Valve_5,  # 模块5 水阀点位
    IO_POINT.Water_Valve_6,  # 模块6 水阀点位
    IO_POINT.Water_Valve_7,  # 模块7 水阀点位
    IO_POINT.Water_Valve_8,  # 模块8 水阀点位
    IO_POINT.Water_Valve_9,  # 模块9 水阀点位
    IO_POINT.Water_Valve_10,  # 模块10 水阀点位
    IO_POINT.Water_Valve_11,  # 模块11 水阀点位
    IO_POINT.Water_Valve_12,  # 模块12 水阀点位

]
# 定量泵气体阀门地址列表 (索引0-11对应模块1-12)
FIX_PUMP_GAS_VALVES = [
    IO_POINT.FixPump_Gas_Valve_1,  # 模块1定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_2,  # 模块2定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_3,  # 模块3定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_4,  # 模块4定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_5,  # 模块5定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_6,  # 模块6定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_7,  # 模块7定量泵气体阀门地址
    IO_POINT.FixPump_Gas_Valve_8,  # 模块8定量泵气体阀门地址
]

FIX_PUMP_INPUT_VALVES = [
    IO_POINT.FixPump_Input_Valve_1,  # 模块1定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_2,  # 模块2定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_3,  # 模块3定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_4,  # 模块4定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_5,  # 模块5定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_6,  # 模块6定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_7,  # 模块7定量泵输入阀门地址
    IO_POINT.FixPump_Input_Valve_8,  # 模块8定量泵输入阀门地址
]

REACTOR_N2_VALVES = [
    IO_POINT.Reactor_N2_Valve_1,  # 模块1N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_2,  # 模块2N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_3,  # 模块3N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_4,  # 模块4N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_5,  # 模块5N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_6,  # 模块6N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_7,  # 模块7N2通液阀门地址
    IO_POINT.Reactor_N2_Valve_8,  # 模块8N2通液阀门地址
]

REACTOR_AIR_VALVES = [
    IO_POINT.Reactor_AIR_Valve_1,  # 模块1N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_2,  # 模块2N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_3,  # 模块3N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_4,  # 模块4N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_5,  # 模块5N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_6,  # 模块6N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_7,  # 模块7N2通液阀门地址
    IO_POINT.Reactor_AIR_Valve_8,  # 模块8N2通液阀门地址
]