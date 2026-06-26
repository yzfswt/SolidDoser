import json
from platform import node
import re
#from pymodbus.client import ModbusTcpClient
from Drivers.EthernetDevices.inovance_three_axis.tools.modbus import WorderOrder, Coil, DiscreteInputs, HoldRegister, InputRegister, DataType
import time
import threading
import csv
import os
from datetime import datetime
from typing import Callable
from Drivers.EthernetDevices.inovance_three_axis.tools.client import TCPClient, ModbusNode, PLCWorkflow, ModbusWorkflow, WorkflowAction, BaseClient
from Drivers.EthernetDevices.inovance_three_axis.tools.modbus import DeviceType, Base as ModbusNodeBase, DataType, WorderOrder
CLAMPING = 'clamping'
OPEN = 'open'
LIQUID_SAMPLING = 'liquid sampling'
VACAUM_SEALING = 'vacuum_sealing'

# 创建点位字典
devices_pos = {
    # dosing_head设备
    'dosing_head_a': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_5_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_5_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_5_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_5_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_5_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_5_STATUS'
    },
    'dosing_head_b': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_6_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_6_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_6_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_6_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_6_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_6_STATUS'
    },
    'dosing_head_c': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_7_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_7_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_7_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_7_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_7_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_7_STATUS'
    },

    # reactor设备
    'reactor_a': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_1_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_1_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_1_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_1_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_1_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_1_STATUS'
    },
    'reactor_b': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_2_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_2_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_2_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_2_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_2_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_2_STATUS'
    },
    'reactor_c': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_3_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_3_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_3_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_3_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_3_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_3_STATUS'
    },
    'reactor_d': {
        'pos_x_cmd': 'COIL_AXIS_X_POS_4_CMD',
        'pos_y_cmd': 'COIL_AXIS_Y_POS_4_CMD',
        'pos_z_cmd': 'COIL_AXIS_Z_POS_4_CMD',
        'pos_x_status': 'COIL_AXIS_X_POS_4_STATUS',
        'pos_y_status': 'COIL_AXIS_Y_POS_4_STATUS',
        'pos_z_status': 'COIL_AXIS_Z_POS_4_STATUS'
    }

}
gripper_cmd = {
    CLAMPING: {
        'cmd': 'COIL_GRIPPER_CLAMPING_CMD',
        'status': 'COIL_GRIPPER_CLAMPING_STATUS'
    },
    OPEN: {
        'cmd': 'COIL_GRIPPER_OPEN_CMD',
        'status': 'COIL_GRIPPER_OPEN_STATUS'
    },
}

class Inovance_Three_Axis:
    """
    This provides a python class for the Inovance Three Axis. It provides functions to read and write to the system.
    """
    def __init__(self, address='192.168.1.20', port=502):
        """
        Initializer of the Inovance Three Axis class.
        This function sets up the modbus tcp connection to the Inovance Three Axis
        """
        modbus_client = TCPClient(addr=address, port=port)#实例化TCP通讯连接
        modbus_client.client.connect()#指定TCP实例进行连接
        count = 100
        while count >0:
            count -=1
            if modbus_client.client.is_socket_open():
                break
            time.sleep(2)
        if not modbus_client.client.is_socket_open():
            raise ValueError('modbus tcp connection failed')
        self.nodes = BaseClient.load_csv('.\\inovance_three_axis.csv')
        self.client  = modbus_client.register_node_list(self.nodes)
        self.success = False
        self.csv_export_thread = None
        self.csv_export_running = False
        self.csv_expoart_file = None

    # ====================== 命令类指令（COIL_x_） ======================
    def axis_x_power_on_cmd(self, cmd):
        """x轴上电命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POWER_ON_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_POWER_ON_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_origin_cmd(self, cmd):
        """x轴回原点命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_ORIGIN_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_ORIGIN_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_stop_cmd(self, cmd):
        """x轴停止命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_STOP_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_STOP_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_reset_cmd(self, cmd):
        """x轴复位命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_RESET_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_RESET_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_home_pos_cmd(self, cmd):
        """x轴回待机位置命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_HOME_POS_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_HOME_POS_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_pos_2_cmd(self, cmd):
        """x轴回位置2命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_2_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err =  self.client.use_node('COIL_AXIS_X_POS_2_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_pos_3_cmd(self, cmd):
        """设备回位置3命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_3_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_3_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_4_cmd(self, cmd):
        """x轴回位置4命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_4_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_4_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_5_cmd(self,cmd):
        """x轴回位置5命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_5_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_5_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_6_cmd(self,cmd):
        """x轴回位置6命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_6_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_6_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_7_cmd(self,cmd):
        """x轴回位置7命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_7_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_7_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_pos_8_cmd(self,cmd):
        """x轴回位置8命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_8_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_8_CMD').read(1)
            return cmd_feedback[0]

    def axis_x_pos_9_cmd(self,cmd):
        """x轴回位置9命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_9_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_9_CMD').read(1)
            return cmd_feedback[0]
    
    def axis_x_pos_10_cmd(self,cmd):
        """x轴回位置10命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_10_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_10_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_11_cmd(self,cmd):
        """x轴回位置11命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_11_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_11_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_12_cmd(self,cmd):
        """x轴回位置12命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_12_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_12_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_13_cmd(self,cmd):
        """x轴回位置13命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_13_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_13_CMD').read(1)
            return cmd_feedback[0]
    def axis_x_pos_14_cmd(self,cmd):
        """x轴回位置14命令（可读写）"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_AXIS_X_POS_14_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_X_POS_14_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_power_on_cmd(self, cmd):
        """y轴上电命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POWER_ON_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POWER_ON_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_origin_cmd(self, cmd):
        """y轴回原点命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_ORIGIN_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_ORIGIN_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_stop_cmd(self, cmd):
        """y轴停止命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_STOP_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_STOP_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_reset_cmd(self, cmd):
        """y轴复位命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_RESET_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_RESET_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_home_pos_cmd(self, cmd):
        """y轴回待机位置命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_HOME_POS_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_HOME_POS_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_pos_2_cmd(self, cmd):
        """y轴回位置2命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_2_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_2_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_pos_3_cmd(self, cmd):
        """y轴回位置3命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_3_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_3_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_4_cmd(self, cmd):
        """y轴回位置4命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_4_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_4_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_5_cmd(self, cmd):
        """y轴回位置5命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_5_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_5_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_6_cmd(self, cmd):
        """y轴回位置6命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_6_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_6_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_7_cmd(self, cmd):
        """y轴回位置7命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Y_POS_7_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_7_CMD').read(1)
            return cmd_feedback[0]

    def axis_y_pos_8_cmd(self,cmd):
        """y轴回位置8命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_8_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_8_CMD').read(1)
            return cmd_feedback[0]
    
    def axis_y_pos_9_cmd(self,cmd):
        """y轴回位置9命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_9_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_9_CMD').read(1)
            return cmd_feedback[0]
    
    def axis_y_pos_10_cmd(self,cmd):
        """y轴回位置10命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_10_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_10_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_11_cmd(self,cmd):
        """y轴回位置11命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_11_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_11_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_12_cmd(self,cmd):
        """y轴回位置12命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_12_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_12_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_13_cmd(self,cmd):
        """y轴回位置13命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_13_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_13_CMD').read(1)
            return cmd_feedback[0]
    def axis_y_pos_14_cmd(self,cmd):
        """y轴回位置14命令（可读写）"""
        if cmd is not None:
            self.success = False
            node= self.client.use_node('COIL_AXIS_Y_POS_14_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Y_POS_14_CMD').read(1)
            return cmd_feedback[0]
    
    def axis_z_power_on_cmd(self, cmd):
        """z轴上电命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POWER_ON_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POWER_ON_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_origin_cmd(self, cmd):
        """z轴回原点命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_ORIGIN_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_ORIGIN_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_stop_cmd(self, cmd):
        """z轴停止命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_STOP_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_STOP_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_reset_cmd(self, cmd):
        """z轴复位命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_RESET_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_RESET_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_home_pos_cmd(self, cmd):
        """z轴回待机位置命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_HOME_POS_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_HOME_POS_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_pos_2_cmd(self, cmd):
        """z轴回位置2命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_2_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_2_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_pos_3_cmd(self, cmd):
        """z轴回位置3命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_3_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_3_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_4_cmd(self, cmd):
        """z轴回位置4命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_4_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_4_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_5_cmd(self, cmd):
        """z轴回位置5命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_5_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_5_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_6_cmd(self, cmd):
        """z轴回位置6命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_6_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_6_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_7_cmd(self, cmd):
        """z轴回位置7命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_7_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_7_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_8_cmd(self, cmd):
        """z轴回位置8命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_8_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_8_CMD').read(1)
            return cmd_feedback[0]

    def axis_z_pos_9_cmd(self, cmd):
        """z轴回位置9命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_9_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_9_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_10_cmd(self, cmd):
        """z轴回位置10命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_10_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_10_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_11_cmd(self, cmd):
        """z轴回位置11命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_11_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_11_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_12_cmd(self, cmd):
        """z轴回位置12命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_12_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_12_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_13_cmd(self, cmd):
        """z轴回位置13命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_13_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_13_CMD').read(1)
            return cmd_feedback[0]
    def axis_z_pos_14_cmd(self, cmd):
        """z轴回位置14命令 (可读写)"""
        if cmd is not None:  # 写入模式
            self.success = False
            node = self.client.use_node('COIL_AXIS_Z_POS_14_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:  # 读取模式
            cmd_feedback, read_err = self.client.use_node('COIL_AXIS_Z_POS_14_CMD').read(1)
            return cmd_feedback[0]

    def gripper_init_cmd(self, cmd):
        """夹爪初始化命令 (可读写)"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_GRIPPER_INIT_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_INIT_CMD').read(1)
            return cmd_feedback[0]

    def gripper_on_cmd(self, cmd):
        """夹爪打开命令 (可读写)"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_GRIPPER_CLAMPING_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_CLAMPING_CMD').read(1)
            return cmd_feedback[0]

    def gripper_off_cmd(self, cmd):
        """夹爪关闭命令 (可读写)"""
        if cmd is not None:
            self.success = False
            node = self.client.use_node('COIL_GRIPPER_OPEN_CMD')
            ret = node.write(cmd)
            self.success = ret
            return self.success
        else:
            cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_OPEN_CMD').read(1)
            return cmd_feedback[0]

    #def func_pack_device_start(self):
    #    """打包指令：设备启动"""
    #    self.success = False
    #    with open('action_device_start.json', 'r', encoding='utf-8') as f:
    #        action_json = json.load(f)
    #    self.client.execute_procedure_from_json(action_json)
    #    self.success = True
    #    return self.success
    #
    # def func_pack_device_start(self):
    #     #切换手动模式
    #     self.sys_hand_cmd(True)
    #     while (self.sys_hand_status) == False:
    #         print("waiting for hand_cmd")
    #         time.sleep(1)
    #     #设备初始化
    #     self.sys_init_cmd(True)
    #     #sys_init_status为bool值，不加括号
    #     while (self.sys_init_status)== False:
    #         print("waiting for init_cmd")
    #         time.sleep(1)
    #     #手动按钮置回False
    #     self.sys_hand_cmd(False)
    #     while (self.sys_hand_cmd()) == True:
    #         print("waiting for hand_cmd to False")
    #         time.sleep(1)
    #     #初始化命令置回False
    #     self.sys_init_cmd(False)
    #     while (self.sys_init_cmd()) == True:
    #         print("waiting for init_cmd to False")
    #         time.sleep(1)

    # def func_pack_device_auto(self):
    #     #切换自动
    #     self.sys_auto_cmd(True)
    #     while (self.sys_auto_status) == False:
    #         print("waiting for auto_status")
    #         time.sleep(1)
    #     #自动按钮置False
    #     self.sys_auto_cmd(False)
    #     while (self.sys_auto_cmd()) == True:
    #         print("waiting for auto_cmd")
    #         time.sleep(1)
    #
    #
    #--------------早期测试函数-----------------
    def func_pack_z_home(self):
        """打包指令：设备停止"""
        self.success = False
        with open('action_axis_z_home.json', 'r', encoding='utf-8') as f:
            action_json = json.load(f)
        self.client.execute_procedure_from_json(action_json)
        self.success = True
        return self.success

    def func_pack_three_axis_move_target(self,target_pos=None):
        """打包指令：三轴移动到目标位置"""
        if target_pos is not None:
            self.success = False
            params = {
                'pos_x_cmd': target_pos['pos_x_cmd'],
                'pos_y_cmd': target_pos['pos_y_cmd'],
                'pos_z_cmd': target_pos['pos_z_cmd'],
                'pos_x_status': target_pos['pos_x_status'],
                'pos_y_status': target_pos['pos_y_status'],
                'pos_z_status': target_pos['pos_z_status']
            }
            with open('action_three_axis_move_target_pos.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **params)
            self.success = True
            return self.success
        else:
            return False

    def func_pack_test(self):
        params_a = {
            'robot_end': 'dosing_head_a',
            'reactor': 'dosing_head_b',
            'type': LIQUID_SAMPLING
        }
        params_b = {
            'robot_end': 'dosing_head_a',
            'reactor': 'dosing_head_b',
            'type': VACAUM_SEALING
        }
        self.func_pack_standard_robot_move_cycle(params_a)
    def func_pack_test_2(self):
        params = {
            'robot_end': 'dosing_head_c',
            'reactor': 'dosing_head_b',
            'type': LIQUID_SAMPLING
        }
        self.func_pack_standard_robot_move_cycle(params)
    # 标准工作流
    def func_pack_standard_robot_move_cycle(self, params=None):
        """打包指令：液体加样"""
        if params is not None:
            self.success = False
            robot_end = params['robot_end']
            reactor = params['reactor']
            type = params['type']

            '''STEP1:三轴移动到机械臂末端的位置'''
            # X轴、Y轴、Z轴移动到机械臂末端位置
            with open('action_three_axis_move_target_pos.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **devices_pos.get(robot_end))

            '''STEP2：夹爪加持加样头'''
            with open('action_gripper.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **gripper_cmd.get(CLAMPING))

            '''STEP3:三轴移动到反应釜的位置'''
            # Z轴移动到待机位置
            with open('action_axis_z_home.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json)
            # X轴、Y轴、Z轴移动到反应釜位置
            with open('action_three_axis_move_target_pos.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **devices_pos.get(reactor))


            '''STEP4:末端动作'''
            if type == LIQUID_SAMPLING:
                '''液体加样动作'''
                time.sleep(10)
                # 阀泵开
                # 等待加样结束
                # 阀泵关
                # 吹气开
                # 吹气关

            elif type == VACAUM_SEALING:
                '''抽真空动作'''
                pass

            '''STEP5:三轴移动到机械臂末端的位置'''
            # Z轴移动到待机位置
            with open('action_axis_z_home.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json)
            # X轴、Y轴、Z轴移动到机械臂末端位置
            with open('action_three_axis_move_target_pos.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **devices_pos.get(robot_end))

            '''STEP6：夹爪松开加样头'''
            with open('action_gripper.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json, **gripper_cmd.get(OPEN))

            '''STEP7:三轴回原点'''
            # Z轴移动到待机位置
            with open('action_axis_z_home.json', 'r', encoding='utf-8') as f:
                action_json = json.load(f)
            self.client.execute_procedure_from_json(action_json)
            # # Y轴移动到待机位置
            # with open('action_axis_y_home.json', 'r', encoding='utf-8') as f:
            #     action_json = json.load(f)
            # self.client.execute_procedure_from_json(action_json)
            # # X轴移动到待机位置
            # with open('action_axis_x_home.json', 'r', encoding='utf-8') as f:
            #     action_json = json.load(f)
            # self.client.execute_procedure_from_json(action_json)

            self.success = True
            return self.success
        else:
            return False
    #def func_pack_device_write_per_elec_param(self, params=None):
    #    """打包指令：设备单瓶电解液参数下发"""
    #    if params is not None:
    #        self.success = False
    #        params = json.load(params)
    #        with open('action_device_write_per_elec_param.json', 'r', encoding='utf-8') as f:
    #            action_json = json.load(f)
    #        self.client.execute_procedure_from_json(action_json, **params)
    #        self.success = True
    #        return self.success
    #    else:
    #        return False



    #def func_pack_device_write_per_elec_param(self, params=None):
    #    """打包指令：设备单瓶电解液参数下发"""
    #    if params is not None:
    #        self.success = False
    #        print(params)
    #        # 1. 处理 params 参数
    #        if isinstance(params, str):
    #            # 如果是 JSON 字符串则解析
    #            try:
    #                params_dict = json.loads(params)
    #            except json.JSONDecodeError:
    #                return False
    #        elif isinstance(params, dict):
    #            # 如果是字典直接使用
    #            params_dict = params
    #        else:
    #            return False
    #        # 2. 读取并处理 JSON 模板
    #        try:
    #            with open('action_device_write_per_elec_param.json', 'r', encoding='utf-8') as f:
    #                action_json = json.load(f)
    #        except FileNotFoundError:
    #            return False
    #        # 3. 替换模板变量
    #        def replace_template_vars(data, context):
    #            """递归替换模板变量"""
    #            if isinstance(data, dict):
    #                return {k: replace_template_vars(v, context) for k, v in data.items()}
    #            elif isinstance(data, list):
    #                return [replace_template_vars(item, context) for item in data]
    #            elif isinstance(data, str) and data.startswith("{{") and data.endswith("}}"):
    #                # 提取变量名：{{elec_use_num}} -> elec_use_num
    #                var_name = data[2:-2].strip()
    #                return context.get(var_name, data)
    #            return data
    #        processed_json = replace_template_vars(action_json, params_dict)
    #        print("The json is", processed_json)
    #        # 4. 执行处理后的 JSON
    #        self.client.execute_procedure_from_json(processed_json)
    #        self.success = True
    #        return self.success
    #    else:
    #        print("No params")
    #        return False



    #def func_pack_device_write_batch_elec_param(self, params=None):
    #    """打包指令：设备批量电解液参数下发"""
    #    if params is not None:
    #        self.success = False
    #        params = json.load(params)
    #        with open('action_device_write_batch_elec_param.json', 'r', encoding='utf-8') as f:
    #            action_json = json.load(f)
    #        self.client.execute_procedure_from_json(action_json, **params)
    #        self.success = True
    #        return self.success
    #    else:
    #        return False


  #
  # # ====================== 命令类指令（REG_x_） ======================
  #   def unilab_send_msg_electrolyte_num(self, num=None):
  #       """UNILAB写电解液使用瓶数(可读写)"""
  #       if num is not None:
  #           self.success = False
  #           ret = self.client.use_node('REG_MSG_ELECTROLYTE_NUM').write(num)
  #           print(ret)
  #           self.success = True
  #           return self.success
  #       else:
  #           cmd_feedback, read_err = self.client.use_node('REG_MSG_ELECTROLYTE_NUM').read(1)
  #           return cmd_feedback[0]
  #
  #
    # ==================== 状态类属性（COIL_x_STATUS） ====================
    @property
    def axis_x_power_on_status(self) -> bool:
        """x轴上电状态( BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POWER_ON_STATUS').read(1)
        return status[0]

    @property
    def axis_x_origin_status(self) -> bool:
        """X轴回原点反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_ORIGIN_STATUS').read(1)
        return status[0]

    @property
    def axis_x_stop_status(self) -> bool:
        """X轴停止反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_STOP_STATUS').read(1)
        return status[0]

    @property
    def axis_x_reset_status(self) -> bool:
        """X轴故障复位反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_RESET_STATUS').read(1)
        return status[0]

    @property
    def axis_x_home_pos_status(self) -> bool:
        """X轴待机位置反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_HOME_POS_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_2_status(self) -> bool:
        """X轴位置2反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_2_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_3_status(self) -> bool:
        """X轴位置3反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_3_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_4_status(self) -> bool:
        """X轴位置4反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_4_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_5_status(self) -> bool:
        """X轴位置5反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_5_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_6_status(self) -> bool:
        """X轴位置6反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_6_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_7_status(self) -> bool:
        """X轴位置7反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_7_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_8_status(self) -> bool:
        """X轴位置8反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_8_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_9_status(self) -> bool:
        """X轴位置9反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_9_STATUS').read(1)
        return status[0]
    @property
    def axis_x_pos_10_status(self) -> bool:
        """X轴位置10反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_10_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_11_status(self) -> bool:
        """X轴位置11反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_11_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_12_status(self) -> bool:
        """X轴位置12反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_12_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_13_status(self) -> bool:
        """X轴位置13反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_13_STATUS').read(1)
        return status[0]

    @property
    def axis_x_pos_14_status(self) -> bool:
        """X轴位置14反馈 (BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_X_POS_14_STATUS').read(1)
        return status[0]

    @property
    def axis_y_power_on_status(self) -> bool:
        """y轴上电状态(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POWER_ON_STATUS').read(1)
        return status[0]

    @property
    def axis_y_origin_status(self) -> bool:
        """y轴回原点反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_ORIGIN_STATUS').read(1)
        return status[0]

    @property
    def axis_y_stop_status(self) -> bool:
        """y轴停止反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_STOP_STATUS').read(1)
        return status[0]

    @property
    def axis_y_reset_status(self) -> bool:
        """y轴故障复位反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_RESET_STATUS').read(1)
        return status[0]

    @property
    def axis_y_home_pos_status(self) -> bool:
        """y轴待机位置反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_HOME_POS_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_2_status(self) -> bool:
        """y轴位置2反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_2_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_3_status(self) -> bool:
        """y轴位置3反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_3_STATUS').read(1)
        return status[0]
    
    @property
    def axis_y_pos_4_status(self) -> bool:
        """y轴位置4反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_4_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_5_status(self) -> bool:
        """y轴位置5反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_5_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_6_status(self) -> bool:
        """y轴位置6反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_6_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_7_status(self) -> bool:
        """y轴位置7反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_7_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_8_status(self) -> bool:
        """y轴位置8反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_8_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_9_status(self) -> bool:
        """y轴位置9反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_9_STATUS').read(1)
        return status[0]
    @property
    def axis_y_pos_10_status(self) -> bool:
        """y轴位置10反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_10_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_11_status(self) -> bool:
        """y轴位置11反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_11_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_12_status(self) -> bool:
        """y轴位置12反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_12_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_13_status(self) -> bool:
        """y轴位置13反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_13_STATUS').read(1)
        return status[0]

    @property
    def axis_y_pos_14_status(self) -> bool:
        """y轴位置14反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Y_POS_14_STATUS').read(1)
        return status[0]

    @property
    def axis_z_power_on_status(self) -> bool:
        """z轴上电状态( BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POWER_ON_STATUS').read(1)
        return status[0]

    @property
    def axis_z_origin_status(self) -> bool:
        """z轴回原点反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_ORIGIN_STATUS').read(1)
        return status[0]

    @property
    def axis_z_stop_status(self) -> bool:
        """z轴停止反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_STOP_STATUS').read(1)
        return status[0]

    @property
    def axis_z_reset_status(self) -> bool:
        """z轴故障复位反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_RESET_STATUS').read(1)
        return status[0]

    @property
    def axis_z_home_pos_status(self) -> bool:
        """z轴待机位置反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_HOME_POS_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_2_status(self) -> bool:
        """y轴位置2反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_2_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_3_status(self) -> bool:
        """y轴位置3反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_3_STATUS').read(1)
        return status[0]
    
    @property
    def axis_z_pos_4_status(self) -> bool:
        """z轴位置4反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_4_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_5_status(self) -> bool:
        """z轴位置5反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_5_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_6_status(self) -> bool:
        """z轴位置6反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_6_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_7_status(self) -> bool:
        """z轴位置7反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_7_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_8_status(self) -> bool:
        """z轴位置8反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_8_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_9_status(self) -> bool:
        """z轴位置9反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_9_STATUS').read(1)
        return status[0]
    @property
    def axis_z_pos_10_status(self) -> bool:
        """z轴位置10反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_10_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_11_status(self) -> bool:
        """z轴位置11反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_11_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_12_status(self) -> bool:
        """z轴位置12反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_12_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_13_status(self) -> bool:
        """z轴位置13反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_13_STATUS').read(1)
        return status[0]

    @property
    def axis_z_pos_14_status(self) -> bool:
        """z轴位置14反馈(BOOL)"""
        status, read_err = self.client.use_node('COIL_AXIS_Z_POS_14_STATUS').read(1)
        return status[0]

    @property
    def gripper_init_status(self):
        """夹爪初始化状态 (只读)"""
        cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_INIT_STATUS').read(1)
        return cmd_feedback[0]

    @property
    def gripper_on_status(self):
        """夹爪打开状态 (只读)"""
        cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_ON_STATUS').read(1)
        return cmd_feedback[0]

    @property
    def gripper_off_status(self):
        """夹爪关闭状态 (只读)"""
        cmd_feedback, read_err = self.client.use_node('COIL_GRIPPER_OFF_STATUS').read(1)
        return cmd_feedback[0]

    # -----------------打包执行的最终动作函数-----------------
    def axis_x_power_on(self):
        print('power on cmd:', self.axis_x_power_on_cmd(True))
        while not self.axis_x_power_on_status:
            print('waiting for axis_x_power_on_status')
            time.sleep(1)
        print('axis_x_power_on_status:', self.axis_x_power_on_status)
        print('power on cmd:', self.axis_x_power_on_cmd(False))

    def axis_y_power_on(self):
        print('power on cmd:', self.axis_y_power_on_cmd(True))
        while not self.axis_y_power_on_status:
            print('waiting for axis_y_power_on_status')
            time.sleep(1)
        print('axis_y_power_on_status:', self.axis_y_power_on_status)
        print('power on cmd:', self.axis_y_power_on_cmd(False))
    
    def axis_z_power_on(self):
        print('power on cmd:', self.axis_z_power_on_cmd(True))
        while not self.axis_z_power_on_status:
            print('waiting for axis_z_power_on_status')
            time.sleep(1)
        print('axis_z_power_on_status:', self.axis_z_power_on_status)
        print('power on cmd:', self.axis_z_power_on_cmd(False))

    def axis_x_origin(self):
        print('origin cmd:', self.axis_x_origin_cmd(True))
        while not self.axis_x_origin_status:
            print('waiting for axis_x_origin_status')
            time.sleep(1)
        print('axis_x_origin_status:', self.axis_x_origin_status)
        print('origin cmd:', self.axis_x_origin_cmd(False))

    def axis_y_origin(self):
        print('origin cmd:', self.axis_y_origin_cmd(True))
        while not self.axis_y_origin_status:
            print('waiting for axis_y_origin_status')
            time.sleep(1)
        print('axis_y_origin_status:', self.axis_y_origin_status)
        print('origin cmd:', self.axis_y_origin_cmd(False))

    def axis_z_origin(self):
        print('origin cmd:', self.axis_z_origin_cmd(True))
        while not self.axis_z_origin_status:
            print('waiting for axis_z_origin_status')
            time.sleep(1)
        print('axis_z_origin_status:', self.axis_z_origin_status)
        print('origin cmd:', self.axis_z_origin_cmd(False))

    def axis_x_stop(self):
        print('stop cmd:', self.axis_x_stop_cmd(True))
        while self.axis_x_stop_status:
            print('waiting for axis_x_stop_status')
            time.sleep(1)
        print('axis_x_stop_status:', self.axis_x_stop_status)
        print('stop cmd:', self.axis_x_stop_cmd(False))
    
    def axis_y_stop(self):
        print('stop cmd:', self.axis_y_stop_cmd(True))
        while self.axis_y_stop_status:
            print('waiting for axis_y_stop_status')
            time.sleep(1)
        print('axis_y_stop_status:', self.axis_y_stop_status)
        print('stop cmd:', self.axis_y_stop_cmd(False))
    
    def axis_z_stop(self):
        print('stop cmd:', self.axis_z_stop_cmd(True))
        while self.axis_z_stop_status:
            print('waiting for axis_z_stop_status')
            time.sleep(1)
        print('axis_z_stop_status:', self.axis_z_stop_status)
        print('stop cmd:', self.axis_z_stop_cmd(False))

    def axis_x_reset(self):
        print('reset cmd:', self.axis_x_reset_cmd(True))
        while not self.axis_x_reset_status:
            print('waiting for axis_x_reset_status')
            time.sleep(1)
        print('axis_x_reset_status:', self.axis_x_reset_status)
        print('reset cmd:', self.axis_x_reset_cmd(False))
    
    def axis_y_reset(self):
        print('reset cmd:', self.axis_y_reset_cmd(True))
        while not self.axis_y_reset_status:
            print('waiting for axis_y_reset_status')
            time.sleep(1)
        print('axis_y_reset_status:', self.axis_y_reset_status)
        print('reset cmd:', self.axis_y_reset_cmd(False))
    
    def axis_z_reset(self):
        print('reset cmd:', self.axis_z_reset_cmd(True))
        while not self.axis_z_reset_status:
            print('waiting for axis_z_reset_status')
            time.sleep(1)
        print('axis_z_reset_status:', self.axis_z_reset_status)
        print('reset cmd:', self.axis_z_reset_cmd(False))

    def axis_x_pos_2(self):
        print('pos 2 cmd:', self.axis_x_pos_2_cmd(True))
        while not self.axis_x_pos_2_status:
            print('waiting for axis_x_pos_2_status')
            time.sleep(1)
        print('axis_x_pos_2_status:', self.axis_x_pos_2_status)
        print('pos 2 cmd:', self.axis_x_pos_2_cmd(False))

    def axis_x_pos_3(self):
        print('pos 3 cmd:', self.axis_x_pos_3_cmd(True))
        while not self.axis_x_pos_3_status:
            print('waiting for axis_x_pos_3_status')
            time.sleep(1)
        print('axis_x_pos_3_status:', self.axis_x_pos_3_status)
        print('pos 3 cmd:', self.axis_x_pos_3_cmd(False))
    
    def axis_x_pos_4(self):
        print('pos 4 cmd:', self.axis_x_pos_4_cmd(True))
        while not self.axis_x_pos_4_status:
            print('waiting for axis_x_pos_4_status')
            time.sleep(1)
        print('axis_x_pos_4_status:', self.axis_x_pos_4_status)
        print('pos 4 cmd:', self.axis_x_pos_4_cmd(False))

    def axis_x_pos_5(self):
        print('pos 5 cmd:', self.axis_x_pos_5_cmd(True))
        while not self.axis_x_pos_5_status:
            print('waiting for axis_x_pos_5_status')
            time.sleep(1)
        print('axis_x_pos_5_status:', self.axis_x_pos_5_status)
        print('pos 5 cmd:', self.axis_x_pos_5_cmd(False))

    def axis_x_pos_6(self):
        print('pos 6 cmd:', self.axis_x_pos_6_cmd(True))
        while not self.axis_x_pos_6_status:
            print('waiting for axis_x_pos_6_status')
            time.sleep(1)
        print('axis_x_pos_6_status:', self.axis_x_pos_6_status)
        print('pos 6 cmd:', self.axis_x_pos_6_cmd(False))

    def axis_x_pos_7(self):
        print('pos 7 cmd:', self.axis_x_pos_7_cmd(True))
        while not self.axis_x_pos_7_status:
            print('waiting for axis_x_pos_7_status')
            time.sleep(1)
        print('axis_x_pos_7_status:', self.axis_x_pos_7_status)
        print('pos 7 cmd:', self.axis_x_pos_7_cmd(False))
    
    def axis_x_pos_8(self):
        print('pos 8 cmd:', self.axis_x_pos_8_cmd(True))
        while not self.axis_x_pos_8_status:
            print('waiting for axis_x_pos_8_status')
            time.sleep(1)
        print('axis_x_pos_8_status:', self.axis_x_pos_8_status)
        print('pos 8 cmd:', self.axis_x_pos_8_cmd(False))
    
    def axis_x_pos_9(self):
        print('pos 9 cmd:', self.axis_x_pos_9_cmd(True))
        while not self.axis_x_pos_9_status:
            print('waiting for axis_x_pos_9_status')
            time.sleep(1)
        print('axis_x_pos_9_status:', self.axis_x_pos_9_status)
        print('pos 9 cmd:', self.axis_x_pos_9_cmd(False))
    
    def axis_x_pos_10(self):
        print('pos 10 cmd:', self.axis_x_pos_10_cmd(True))
        while not self.axis_x_pos_10_status:
            print('waiting for axis_x_pos_10_status')
            time.sleep(1)
        print('axis_x_pos_10_status:', self.axis_x_pos_10_status)
        print('pos 10 cmd:', self.axis_x_pos_10_cmd(False))
    
    def axis_x_pos_11(self):
        print('pos 11 cmd:', self.axis_x_pos_11_cmd(True))
        while not self.axis_x_pos_11_status:
            print('waiting for axis_x_pos_11_status')
            time.sleep(1)
        print('axis_x_pos_11_status:', self.axis_x_pos_11_status)
        print('pos 11 cmd:', self.axis_x_pos_11_cmd(False))
        
    def axis_x_pos_12(self):
        print('pos 12 cmd:', self.axis_x_pos_12_cmd(True))
        while not self.axis_x_pos_12_status:
            print('waiting for axis_x_pos_12_status')
            time.sleep(1)
        print('axis_x_pos_12_status:', self.axis_x_pos_12_status)
        print('pos 12 cmd:', self.axis_x_pos_12_cmd(False))
        
    def axis_x_pos_13(self):
        print('pos 13 cmd:', self.axis_x_pos_13_cmd(True))
        while not self.axis_x_pos_13_status:
            print('waiting for axis_x_pos_13_status')
            time.sleep(1)
        print('axis_x_pos_13_status:', self.axis_x_pos_13_status)
        print('pos 13 cmd:', self.axis_x_pos_13_cmd(False))
        
    def axis_x_pos_14(self):
        print('pos 14 cmd:', self.axis_x_pos_14_cmd(True))
        while not self.axis_x_pos_14_status:
            print('waiting for axis_x_pos_14_status')
            time.sleep(1)
        print('axis_x_pos_14_status:', self.axis_x_pos_14_status)
        print('pos 14 cmd:', self.axis_x_pos_14_cmd(False))

    def axis_y_pos_2(self):
        print('pos 2 cmd:', self.axis_y_pos_2_cmd(True))
        while not self.axis_y_pos_2_status:
            print('waiting for axis_y_pos_2_status')
            time.sleep(1)
        print('axis_y_pos_2_status:', self.axis_y_pos_2_status)
        print('pos 2 cmd:', self.axis_y_pos_2_cmd(False))

    def axis_y_pos_3(self):
        print('pos 3 cmd:', self.axis_y_pos_3_cmd(True))
        while not self.axis_y_pos_3_status:
            print('waiting for axis_y_pos_3_status')
            time.sleep(1)
        print('axis_y_pos_3_status:', self.axis_y_pos_3_status)
        print('pos 3 cmd:', self.axis_y_pos_3_cmd(False))
    def axis_y_pos_4(self):
        print('pos 4 cmd:', self.axis_y_pos_4_cmd(True))
        while not self.axis_y_pos_4_status:
            print('waiting for axis_y_pos_4_status')
            time.sleep(1)
        print('axis_y_pos_4_status:', self.axis_y_pos_4_status)
        print('pos 4 cmd:', self.axis_y_pos_4_cmd(False))

    def axis_y_pos_5(self):
        print('pos 5 cmd:', self.axis_y_pos_5_cmd(True))
        while not self.axis_y_pos_5_status:
            print('waiting for axis_y_pos_5_status')
            time.sleep(1)
        print('axis_y_pos_5_status:', self.axis_y_pos_5_status)
        print('pos 5 cmd:', self.axis_y_pos_5_cmd(False))

    def axis_y_pos_6(self):
        print('pos 6 cmd:', self.axis_y_pos_6_cmd(True))
        while not self.axis_y_pos_6_status:
            print('waiting for axis_y_pos_6_status')
            time.sleep(1)
        print('axis_y_pos_6_status:', self.axis_y_pos_6_status)
        print('pos 6 cmd:', self.axis_y_pos_6_cmd(False))

    def axis_y_pos_7(self):
        print('pos 7 cmd:', self.axis_y_pos_7_cmd(True))
        while not self.axis_y_pos_7_status:
            print('waiting for axis_y_pos_7_status')
            time.sleep(1)
        print('axis_y_pos_7_status:', self.axis_y_pos_7_status)
        print('pos 7 cmd:', self.axis_y_pos_7_cmd(False))
    
    def axis_y_pos_8(self):
        print('pos 8 cmd:', self.axis_y_pos_8_cmd(True))
        while not self.axis_y_pos_8_status:
            print('waiting for axis_y_pos_8_status')
            time.sleep(1)
        print('axis_y_pos_8_status:', self.axis_y_pos_8_status)
        print('pos 8 cmd:', self.axis_y_pos_8_cmd(False))
    
    def axis_y_pos_9(self):
        print('pos 9 cmd:', self.axis_y_pos_9_cmd(True))
        while not self.axis_y_pos_9_status:
            print('waiting for axis_y_pos_9_status')
            time.sleep(1)
        print('axis_y_pos_9_status:', self.axis_y_pos_9_status)
        print('pos 9 cmd:', self.axis_y_pos_9_cmd(False))
        
    def axis_y_pos_10(self):
        print('pos 10 cmd:', self.axis_y_pos_10_cmd(True))
        while not self.axis_y_pos_10_status:
            print('waiting for axis_y_pos_10_status')
            time.sleep(1)
        print('axis_y_pos_10_status:', self.axis_y_pos_10_status)
        print('pos 10 cmd:', self.axis_y_pos_10_cmd(False))
    def axis_y_pos_11(self):
        print('pos 11 cmd:', self.axis_y_pos_11_cmd(True))
        while not self.axis_y_pos_11_status:
            print('waiting for axis_y_pos_11_status')
            time.sleep(1)
        print('axis_y_pos_11_status:', self.axis_y_pos_11_status)
        print('pos 11 cmd:', self.axis_y_pos_11_cmd(False))
    def axis_y_pos_12(self):
        print('pos 12 cmd:', self.axis_y_pos_12_cmd(True))
        while not self.axis_y_pos_12_status:
            print('waiting for axis_y_pos_12_status')
            time.sleep(1)
        print('axis_y_pos_12_status:', self.axis_y_pos_12_status)
        print('pos 12 cmd:', self.axis_y_pos_12_cmd(False))
    def axis_y_pos_13(self):
        print('pos 13 cmd:', self.axis_y_pos_13_cmd(True))
        while not self.axis_y_pos_13_status:
            print('waiting for axis_y_pos_13_status')
            time.sleep(1)
        print('axis_y_pos_13_status:', self.axis_y_pos_13_status)
        print('pos 13 cmd:', self.axis_y_pos_13_cmd(False))
    def axis_y_pos_14(self):
        print('pos 14 cmd:', self.axis_y_pos_14_cmd(True))
        while not self.axis_y_pos_14_status:
            print('waiting for axis_y_pos_14_status')
            time.sleep(1)
        print('axis_y_pos_14_status:', self.axis_y_pos_14_status)
        print('pos 14 cmd:', self.axis_y_pos_14_cmd(False))

    def axis_z_pos_2(self):
        print('pos 2 cmd:', self.axis_z_pos_2_cmd(True))
        while not self.axis_z_pos_2_status:
            print('waiting for axis_z_pos_2_status')
            time.sleep(1)
        print('axis_z_pos_2_status:', self.axis_z_pos_2_status)
        print('pos 2 cmd:', self.axis_z_pos_2_cmd(False))
        
    def axis_z_pos_3(self):
        print('pos 3 cmd:', self.axis_z_pos_3_cmd(True))
        while not self.axis_z_pos_3_status:
            print('waiting for axis_z_pos_3_status')
            time.sleep(1)
        print('axis_z_pos_3_status:', self.axis_z_pos_3_status)
        print('pos 3 cmd:', self.axis_z_pos_3_cmd(False))
    def axis_z_pos_4(self):
        print('pos 4 cmd:', self.axis_z_pos_4_cmd(True))
        while not self.axis_z_pos_4_status:
            print('waiting for axis_z_pos_4_status')
            time.sleep(1)
        print('axis_z_pos_4_status:', self.axis_z_pos_4_status)
        print('pos 4 cmd:', self.axis_z_pos_4_cmd(False))

    def axis_z_pos_5(self):
        print('pos 5 cmd:', self.axis_z_pos_5_cmd(True))
        while not self.axis_z_pos_5_status:
            print('waiting for axis_z_pos_5_status')
            time.sleep(1)
        print('axis_z_pos_5_status:', self.axis_z_pos_5_status)
        print('pos 5 cmd:', self.axis_z_pos_5_cmd(False))

    def axis_z_pos_6(self):
        print('pos 6 cmd:', self.axis_z_pos_6_cmd(True))
        while not self.axis_z_pos_6_status:
            print('waiting for axis_z_pos_6_status')
            time.sleep(1)
        print('axis_z_pos_6_status:', self.axis_z_pos_6_status)
        print('pos 6 cmd:', self.axis_z_pos_6_cmd(False))

    def axis_z_pos_7(self):
        print('pos 7 cmd:', self.axis_z_pos_7_cmd(True))
        while not self.axis_z_pos_7_status:
            print('waiting for axis_z_pos_7_status')
            time.sleep(1)
        print('axis_z_pos_7_status:', self.axis_z_pos_7_status)
        print('pos 7 cmd:', self.axis_z_pos_7_cmd(False))
    
    def axis_z_pos_8(self):
        print('pos 8 cmd:', self.axis_z_pos_8_cmd(True))
        while not self.axis_z_pos_8_status:
            print('waiting for axis_z_pos_8_status')
            time.sleep(1)
        print('axis_z_pos_8_status:', self.axis_z_pos_8_status)
        print('pos 8 cmd:', self.axis_z_pos_8_cmd(False))
    
    def axis_z_pos_9(self):
        print('pos 9 cmd:', self.axis_z_pos_9_cmd(True))
        while not self.axis_z_pos_9_status:
            print('waiting for axis_z_pos_9_status')
            time.sleep(1)
        print('axis_z_pos_9_status:', self.axis_z_pos_9_status)
        print('pos 9 cmd:', self.axis_z_pos_9_cmd(False))
    
    def axis_z_pos_10(self):
        print('pos 10 cmd:', self.axis_z_pos_10_cmd(True))
        while not self.axis_z_pos_10_status:
            print('waiting for axis_z_pos_10_status')
            time.sleep(1)
        print('axis_z_pos_10_status:', self.axis_z_pos_10_status)
        print('pos 10 cmd:', self.axis_z_pos_10_cmd(False))

    def axis_z_pos_11(self):
        print('pos 11 cmd:', self.axis_z_pos_11_cmd(True))
        while not self.axis_z_pos_11_status:
            print('waiting for axis_z_pos_11_status')
            time.sleep(1)
        print('axis_z_pos_11_status:', self.axis_z_pos_11_status)
        print('pos 11 cmd:', self.axis_z_pos_11_cmd(False))
    
    def axis_z_pos_12(self):
        print('pos 12 cmd:', self.axis_z_pos_12_cmd(True))
        while not self.axis_z_pos_12_status:
            print('waiting for axis_z_pos_12_status')
            time.sleep(1)
        print('axis_z_pos_12_status:', self.axis_z_pos_12_status)
        print('pos 12 cmd:', self.axis_z_pos_12_cmd(False))
        
    def axis_z_pos_13(self):
        print('pos 13 cmd:', self.axis_z_pos_13_cmd(True))
        while not self.axis_z_pos_13_status:
            print('waiting for axis_z_pos_13_status')
            time.sleep(1)
        print('axis_z_pos_13_status:', self.axis_z_pos_13_status)
        print('pos 13 cmd:', self.axis_z_pos_13_cmd(False))
    
    def axis_z_pos_14(self):
        print('pos 14 cmd:', self.axis_z_pos_14_cmd(True))
        while not self.axis_z_pos_14_status:
            print('waiting for axis_z_pos_14_status')
            time.sleep(1)
        print('axis_z_pos_14_status:', self.axis_z_pos_14_status)
        print('pos 14 cmd:', self.axis_z_pos_14_cmd(False))
    
    def axis_x_home_pos(self):
        print('home pos cmd:', self.axis_x_home_pos_cmd(True))
        while not self.axis_x_home_pos_status:
            print('waiting for axis_x_home_pos_status')
            time.sleep(1)
        print('axis_x_home_pos_status:', self.axis_x_home_pos_status)
        print('home pos cmd:', self.axis_x_home_pos_cmd(False))
    def axis_y_home_pos(self):
        print('home pos cmd:', self.axis_y_home_pos_cmd(True))
        while not self.axis_y_home_pos_status:
            print('waiting for axis_y_home_pos_status')
            time.sleep(1)
        print('axis_y_home_pos_status:', self.axis_y_home_pos_status)
        print('home pos cmd:', self.axis_y_home_pos_cmd(False))
    def axis_z_home_pos(self):
        print('home pos cmd:', self.axis_z_home_pos_cmd(True))
        while not self.axis_z_home_pos_status:
            print('waiting for axis_z_home_pos_status')
            time.sleep(1)
        print('axis_z_home_pos_status:', self.axis_z_home_pos_status)
        print('home pos cmd:', self.axis_z_home_pos_cmd(False))
    def gripper_init(self):
        print('gripper init cmd:', self.gripper_init_cmd(True))
        while not self.gripper_init_status:
            print('waiting for gripper_init_status')
            time.sleep(1)
        print('gripper_init_status:', self.gripper_init_status)
        print('gripper init cmd:', self.gripper_init_cmd(False))
    def gripper_on(self):
        print('gripper on cmd:', self.gripper_on_cmd(True))
        while not self.gripper_on_status:
            print('waiting for gripper_on_status')
            time.sleep(1)
        print('gripper_on_status:', self.gripper_on_status)
        print('gripper on cmd:', self.gripper_on_cmd(False))
    def gripper_off(self):
        print('gripper off cmd:', self.gripper_off_cmd(True))
        while not self.gripper_off_status:
            print('waiting for gripper_off_status')
            time.sleep(1)
        print('gripper_off_status:', self.gripper_off_status)
        print('gripper off cmd:', self.gripper_off_cmd(False))

    def Take_Adder_1(self):
        self.axis_z_home_pos()
        self.axis_x_pos_6()
        self.axis_y_pos_6()
        self.axis_z_pos_6()
        self.gripper_on()
        self.axis_z_home_pos()

    def Take_Adder_2(self):
        self.axis_z_home_pos()
        self.axis_x_pos_7()
        self.axis_y_pos_7()
        self.axis_z_pos_7()
        self.gripper_on()
        self.axis_z_home_pos()

    def Go_to_bottle_1(self):
        self.axis_z_home_pos()
        self.axis_x_pos_2()
        self.axis_y_pos_2()
        self.axis_z_pos_2()

    def Go_to_bottle_2(self):
        self.axis_z_home_pos()
        self.axis_x_pos_3()
        self.axis_y_pos_3()
        self.axis_z_pos_3()

    def Go_to_bottle_3(self):
        self.axis_z_home_pos()
        self.axis_x_pos_4()
        self.axis_y_pos_4()
        self.axis_z_pos_4()

    def Go_to_bottle_4(self):
        self.axis_z_home_pos()
        self.axis_x_pos_5()
        self.axis_y_pos_5()
        self.axis_z_pos_5()

    def Realse_Adder_1(self):
        self.axis_z_home_pos()
        self.axis_x_pos_6()
        self.axis_y_pos_6()
        self.axis_z_pos_6()
        self.gripper_off()
        self.axis_z_home_pos()

    def Realse_Adder_2(self):
        self.axis_z_home_pos()
        self.axis_x_pos_7()
        self.axis_y_pos_7()
        self.axis_z_pos_7()
        self.gripper_off()
        self.axis_z_home_pos()

    def Go_to_home(self):
        self.axis_z_home_pos()
        self.axis_x_home_pos()
        self.axis_y_home_pos()


if __name__ == '__main__':
    three_axis = Inovance_Three_Axis(address="192.168.1.20", port="502")
    three_axis.Take_Adder_2()
    three_axis.Go_to_bottle_3()
    three_axis.Realse_Adder_2()
    # # # 测试三轴上电
    # three_axis.test_axis_x_power_on()
    # three_axis.test_axis_y_power_on()
    # three_axis.test_axis_z_power_on()
    # # # 测试三轴回零
    # three_axis.test_axis_z_origin()
    # three_axis.test_axis_x_origin()
    # three_axis.test_axis_y_origin()
    #
    #保证Z轴在待机位置
    # three_axis.test_axis_z_home_pos()
    # # 测试三轴点位
    

    # # 测试夹爪
    # three_axis.test_gripper_init()
    # three_axis.test_gripper_on()
    # three_axis.test_gripper_off()


    #three_axis.func_pack_test()
    #time.sleep(1)
    #three_axis.func_pack_test_2()
    #调用Z轴测试函数
    #test_axis_z_sequence(three_axis)

    '''
    print('start:', coin_cell_assmbly.func_pack_device_start())
    time.sleep(1)

    print('stop:', coin_cell_assmbly.func_pack_device_stop())
    time.sleep(1)

    while True:
        # cmd coil
        print('start cmd:', coin_cell_assmbly.sys_start_cmd(True))
        time.sleep(1)


        # cmd reg
        print('elec use num msg:', coin_cell_assmbly.unilab_send_msg_electrolyte_use_num(8))
        time.sleep(1)


        # status coil
        print('start status:',coin_cell_assmbly.sys_start_status)
        time.sleep(1)

        # status reg
        print('assembly coin cell num:', coin_cell_assmbly.data_assembly_coin_cell_num)
        time.sleep(1)


'''


