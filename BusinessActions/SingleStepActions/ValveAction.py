from BusinessActions.DeviceManager import DeviceManager
from Drivers.EthernetDevices.Valve import Valve

def Valve_open(valve:Valve):
    valve.open()

def Valve_close(valve:Valve):
    valve.close()

def Valve_change_state(valve:Valve):
    valve.change_state()

def Valve_read_state(valve:Valve):
    return valve.get_state()

def Post_Process_Discharge_On(device_manager:DeviceManager,post_process_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行后处理模块排料开启 - 模块: {post_process_id}")
        return
    if device_manager.gas_valves and device_manager.discharge_valves:
        device_manager.gas_valves[post_process_id-1].open()
        device_manager.discharge_valves[post_process_id-1].open()

def Post_Process_Discharge_Off(device_manager:DeviceManager,post_process_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行后处理模块排料关闭 - 模块: {post_process_id}")
        return
    if device_manager.gas_valves and device_manager.discharge_valves:
        device_manager.gas_valves[post_process_id-1].close()
        device_manager.discharge_valves[post_process_id-1].close()

def Reactor_N2_on(device_manager:DeviceManager,reactor_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器氮气开启 - 反应器: {reactor_id}")
        return
    if device_manager.reactor_N2_valves:
        device_manager.reactor_N2_valves[reactor_id-1].open()
def Reactor_N2_off(device_manager:DeviceManager,reactor_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器氮气关闭 - 反应器: {reactor_id}")
        return
    if device_manager.reactor_N2_valves:
        device_manager.reactor_N2_valves[reactor_id-1].close()
def Reactor_Air_on(device_manager:DeviceManager,reactor_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器空气开启 - 反应器: {reactor_id}")
        return
    if device_manager.reactor_Air_valves:
        device_manager.reactor_N2_valves[reactor_id - 1].open()
        device_manager.reactor_Air_valves[reactor_id-1].open()
def Reactor_Air_off(device_manager:DeviceManager,reactor_id:int):
    # 检查是否在仿真模式下
    if device_manager.simulation_mode:
        print(f"仿真模式：执行反应器空气关闭 - 反应器: {reactor_id}")
        return
    if device_manager.reactor_Air_valves:
        device_manager.reactor_N2_valves[reactor_id - 1].close()
        device_manager.reactor_Air_valves[reactor_id-1].close()
