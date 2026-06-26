# coding=utf-8
# !/usr/bin/env python
"""
mod:"constants" -- Global constants file for easy maintenance
======================================
module:: constants
platform: Windows
synopsis: Global constants file for easy maintenance.
This file contains all constants used in the Chemplier Porject.
such as dictionary keys, device type,and forth. Keeping them
all in one file makes futue maintenance a lot easier and avoids duplicates.
"""
ADDRESS = "IP_address"
ASSOCIATED_FLASK = "associtaed_flask"
CAMERA_REAL_SENSE = 'intel_realsense_d435i'
CHILLER = "chiller"
CLASS = "class"
COLLECTION_FLASK = "chemputer_collection_flask"
COLUMN = "chemputer_column"
CURRENT_VOLUME = "current_volume"
CONNECTED_NO = "not connected"
CONNECTED_YES = "connected"
CONNECTED_INIT = "initialization"
DEST = "dest_position"
DISPLACEMENT_PUMP = "displacement_pump"
DISPLACEMENT_PUMP_HENGCHUANG = "displacement_pump_hengchuang"
DISPLACEMENT_VALVE = "displacement_valve"
DISPLACEMENT_VALVE_HENGCHUANG = "displacement_valve_hengchuang"
DISPLACEMENT_VALVE_KEYTO = "displacement_valve_keyto"
DISPLACEMENT_VALVE_RUNZE = "displacement_valve_runze"
DISPLACEMENT_FLASK = "displacement_flask"
DUCO_ROBOT = "DUCO_Robot"
FIXED_PUMP = "fixed_pump"
FIXED_PUMP_HECHUANG = "fixed_pump_hengchuang"
FIXED_VALVE = "fixed_valve"
FIXED_VALVE_HENGCHUANG = "fixed_valve_hengchuang"
FIXED_VALVE_KEYTO = "fixed_valve_keyto"
FIXED_VALVE_RUNZE = "fixed_valve_runze"
FIXED_FLASK = "fixed_flask"
FILTER = "chemputer_filter"
IKA_CHILLER = "IKA_Chiller"
IKA_OVERHEAD_STIRRER = "IKA_Overhead_Stirrer"
IKA_RV = "IKA_RV"
IKA_RET_STIRRER = "IKA_RET_Stirrer"
IKA_VACUUM = "IKA_Vacuum"
IKKEM_SOLID_DISPENSE = "IKKEM_SolidDispenseModule_1"
INPUT = "input"
IO_DEVICE = "io_device"
MAX_VOLUME = "max_volume"
MODEL = "model"
MODBUS_DEVICE = "modbus_device"
NAME = "name"
NEXT = "next"
OBJECT = "obj"
OUTPUT = "output"
PARENT_FLASK = "parent_flask"
PERISTALTIC_PUMP = "peristaltic_pump"
PERISTALTIC_PUMP_RUNZE_LM60B = "peristaltic_pump_runze_lm60b"
PERISTALTIC_PUMP_RUNZE_BJ30 = "peristaltic_pump_runze_bj30"
PERISTALTIC_VALVE = "peristaltic_valve"
PERISTALTIC_VALVE_HENGCHUANG = "peristaltic_valve_hengchuang"
PERISTALTIC_VALVE_KEYTO = "peristaltic_valve_keyto"
PERISTALTIC_VALVE_RUNZE = "peristaltic_valve_runze"
PERISTALTIC_FLASK = "peristaltic_flask"
PUMP_AND_VALVES = "pump_and_valves"
PORT = "port"
ROTAVAP = "chemputer_rotavap"
SEPARATOR = "chemputer_separator"
SERIAL_DEVICE = "serial_device"
SOCKET_DEVICE = "socket_device"
SOILD_DISPENSE_MODULE = "soild_dispense_module"
SOURCE = "source_position"
STIRRER = "stirrer"
SNRD_IO = "SNRD_IO"
VACUUM = "vacuum_pump"
VOLUME = "volume"
WASTE = "chemputer_waste"

# numerical constants (in alphabetical order)
COOLING_THRESHOLD = 0.5  # degrees
DEFAULT_FIXED_PUMP_SPEED = 300  # rpm
DEFAULT_PUMP_SPEED = 1  # mL/s
DEFAULT_PERISTALTIC_PUMP_SPEED = 300  # rpm
EMPTY = 0
EQUILIBRATION_TIME = 1  # S
FIXED_PUMP_ML_PER_TIME = 0.049  # ml
OP_POS = 1

# io constants
CHILLER_CIRCULATION_SOLENOID_VALVE = "Circulation_Solenoid_Valve"
REACTOR_VAC_SOLENOID_VALVE = "Vac_Solenoid_Valve"
REACTOR_GAS_SOLENOID_VALVE = "Gas_Solenoid_Valve"
REACTOR_CHILLER_SOLENOID_VALVE = "Chiller_Solenoid_Valve"
REACTOR_SEAL_SOLENOID_VALVE = "Seal_Solenoid_Valve"
REACTOR_BOTTOM_SOLENOID_VALVE = "Bottom_Solenoid_Valve"
REACTOR_BRANCH_SOLENOID_VALVE = "Branch_Solenoid_Valve"
REACTOR_WASTE_SOLENOID_VALVE = "Waste_Solenoid_Valve"
REACTOR_PRODUCT_SOLENOID_VALVE = "Product_Solenoid_Valve"

# devices (for setup)
CHILLERS = [
    IKA_CHILLER
]

OVERHEAD_STIRRERS = [
    IKA_OVERHEAD_STIRRER
]

DISPLACEMENT_PUMPS = [
    DISPLACEMENT_PUMP_HENGCHUANG
]

FIXED_PUMPS = [
    FIXED_PUMP_HECHUANG
]

PERISTALTIC_PUMPS = [
    PERISTALTIC_PUMP_RUNZE_LM60B,
    PERISTALTIC_PUMP_RUNZE_BJ30
]

ROTAVAPS = [
   IKA_RV
]

ROBOTS = [
    "Three_Axies",
    DUCO_ROBOT
]

RET_STIRRERS = [
    IKA_RET_STIRRER
]

SOILD_DISPENSE_MODULES = [
    IKKEM_SOLID_DISPENSE
]

VACUUM_PUMPS = [
    IKA_VACUUM
]

DISPLACEMENT_VALVES = [
    DISPLACEMENT_VALVE_HENGCHUANG,
    DISPLACEMENT_VALVE_KEYTO,
    DISPLACEMENT_VALVE_RUNZE
]

FIXED_VALVES = [
    FIXED_VALVE_HENGCHUANG,
    FIXED_VALVE_KEYTO,
    FIXED_VALVE_RUNZE
]

PERISTALTIC_VALVES = [
    PERISTALTIC_VALVE_HENGCHUANG,
    PERISTALTIC_VALVE_KEYTO,
    PERISTALTIC_VALVE_RUNZE
]

IO_DEVICES = [
    SNRD_IO
]

SPECIAL_DEVICES = [
    "chemputer_filter",
    "chemputer_separator",
    "chemputer_ratavap",
    "chemputer_column"
]

HENGCHUANG_VALVES = [
    DISPLACEMENT_VALVE_HENGCHUANG,
    FIXED_VALVE_HENGCHUANG,
    PERISTALTIC_VALVE_HENGCHUANG
]

RUNZE_VALVES = [
    DISPLACEMENT_VALVE_RUNZE,
    FIXED_VALVE_RUNZE,
    PERISTALTIC_VALVE_RUNZE
]

KEYTO_VALVES = [
    DISPLACEMENT_VALVE_KEYTO,
    FIXED_VALVE_KEYTO,
    PERISTALTIC_VALVE_KEYTO
]

# ChASM commands
CHILLER_CMDS = [
    "START_CHILLER",
    "STOP_CHILLER",
    "SET_CHILLER",
    "CHILLER_WAIT_FOR_TEMP",
    "SWITCH_CHILLER_INNER_CIRCULATION",
    "SWITCH_CHILLER_OUTER_CIRCULATION"
]

OVERHEAD_STIR_CMDS = [
    "START_OVERHEAD_STIR",
    "STOP_OVERHEAD_STIR",
    "SET_OVERHEAD_STIR_RPM"
]

DISPLACEMENT_PUMP_CMDS = [
    "DISPLACEMENT_PUMP_MOVE",
    "DISPLACEMENT_PUMP_HOME",
    "DISPLACEMENT_PUMP_PRIME"
]

FIXED_PUMP_CMDS = [
    "FIXED_PUMP_PUMP",
    "FIXED_PUMP_AIR_BLOW"
]

PERISTALTIC_PUMP_CMDS = [
    "PERISTALTIC_PUMP_PUMP",
    "PERISTALTIC_PUMP_AIR_BLOW"
]

ROTAVAP_CMDS = [
    "START_HEATER_BATH",
    "STOP_HEATER_BATH",
    "START_ROTATION",
    "STOP_ROTATION",
    "LIFT_ARM_UP",
    "LIFT_ARM_DOWN",
    "RESET_ROTAVAP",
    "SET_BATH_TEMP",
    "SET_ROTATION",
    "RV_WAIT_FOR_TEMP",
    "SET_INTERVAL"
]

ROBOTS_CMDS = [
    "ROBOT_HOME",
    "ROBOT_LOAD_ARM_END",
    "ROBOT_UNLOAD_ARM_END",
    "ROBOT_ARM_END_ACTION",
    "ROBOT_MOVE",
]

RET_STIR_CMDS = [
    "START_RET_STIR",
    "START_RET_HEAT",
    "STOP_RET_HEAT",
    "STOP_RET_STIR",
    "SET_RET_TEMP",
    "SET_RET_STIR_RPM",
    "RET_STIRRER_WAIT_FOR_TEMP"
]

REACTOR_CMDS = [
    "SWITCH_REACTOR_CHILLER_ON",
    "SWITCH_REACTOR_CHILLER_OFF",
    "SWITCH_REACTOR_GAS_ON",
    "SWITCH_REACTOR_GAS_OFF",
    "SWITCH_REACTOR_VAC_ON",
    "SWITCH_REACTOR_VAC_OFF",
    "SWITCH_REACTOR_SEAL_ON",
    "SWITCH_REACTOR_SEAL_OFF",
    "SWITCH_REACTOR_DISCHARGE_WASTE_ON",
    "SWITCH_REACTOR_DISCHARGE_WASTE_OFF",
    "SWITCH_REACTOR_COLLECT_PRODUCT_ON",
    "SWITCH_REACTOR_COLLECT_PRODUCT_OFF"
]

SOLID_DISPENSE_MODULE_CMDS = [
    "MATCH_DOSING_HEAD",
    "OPEN_DOSING",
    "DOSING",
    "CLOSE_DOSING",
    "DOSING_WITHOUT_FEEDBACK"
]

VACUUM_CMDS = [
    "SET_VAC_SP",
    "RESET_VAC",
    "START_VAC",
    "STOP_VAC"
]

WAIT = [
    "WAIT"
]

BREAKPOINT_CMDS = "BREAKPOINT"

# Device Flags
CHILLER_FLAG = "CHILLER"
DISPLACEMENT_PUMP_FLAG = "DISPLACEMENT_PUMPS"
DISPLACEMENT_VALVE_FLAG = "DISPLACEMENT_VALVES"
FIXED_PUMP_FLAG = "FIXED_PUMPS"
FIXED_VALVE_FLAG = "FIXED_VALVES"
OVERHEAD_STIR_FLAG = "OVERHEAD_STIRRER"
PERISTALTIC_PUMP_FLAG = "PERISTALTIC_PUMPS"
PERISTALTIC_VALVE_FLAG = "PERISTALTIC_VALVES"
ROTAVAP_FLAG = "ROTAVAP"
RET_STIR_FLAG = "RET_STIRRER"
SOLID_DISPENSE_MODULE_FLAG = "SOLID_DISPENSE_MODULE"
IO_DEVICE_FLAG = "ID_DEVICE"
VAC_FLAG = "VACUUM"

# Misc
PARALLEL = "P"
SEQUENTIAL = "S"


def displacement_pump_items():
    return None