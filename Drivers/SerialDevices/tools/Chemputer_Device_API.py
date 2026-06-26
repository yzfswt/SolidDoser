# coding=utf-8
# !/usr/bin/env python
"""
mod:"Chemputer_Device_API" -- API for Chemputer pumps and valves
=======================================
module: Chemputer_Device_API
platform: Unix, Windows
synopsis: Control Chemputer pumps and valves
This API is intended for controlling a set of Chemputer pump and valves over a local network
"""
import serial
import logging
import socket
import sys
import threading
import time
import re
from collections import OrderedDict

""" CONSTANTS """
BUFFER_SIZE = 8


class ChemputerDevice(object):
    """
    API for interfacing with the Chemputer pumps and valves.

    Args:
        address (str): Address of the device
        name (str): Optional name of the device
        serial_type (str): Serial type of the device
        serial_port (str): Serial port of the device
    """
    def __init__(self, address, name="", slave_id = 0x11, serial_type=None, serial_port=None):
        self.name = name
        self.address = str(address)
        self.serial_type = serial_type
        self.serial_port = serial_port
        self.slave_id = slave_id  # Default slave ID for Keyto devices is 0x11
        self.ser: serial.Serial = None
        self.tcp_client = None
        self.set_port = -1
        self.set_volume = -1
        self.logger = logging.getLogger("main_logger.pv_logger")

    def crc16(self, data):
        crc = 0xFFFF  # 初始值为0xFFFF
        for byte in data:
            crc ^= byte  # 异或运算
            for _ in range(8):  # 移位操作
                if crc & 0x0001:  # 检查最低位
                    crc >>= 1  # 右移一位
                    crc ^= 0xA001  # 异或多项式
                else:
                    crc >>= 1  # 右移一位
        return crc & 0xFFFF  # 返回校验码的低16位

    def packet_data(self, data):
        # 对数据进行CRC16校验，并将校验码低位和高位添加到数据末尾
        crc = self.crc16(data)
        data.append(crc & 0xFF)  # 添加CRC低8位
        data.append((crc >> 8) & 0xFF)  # 添加CRC高8位
        return data

    def packet_data_keyto(self, cmd, data=0):
        # 组装Keyto设备的数据包，包含命令和数据，并计算校验和
        senddata = [0] * 8
        senddata[0] = 0xAA  # 包头
        senddata[1] = self.slave_id  # 从机地址
        senddata[2] = cmd  # 命令字
        senddata[3] = (data >> 24) & 0xFF  # 数据高字节
        senddata[4] = (data >> 16) & 0xFF
        senddata[5] = (data >> 8) & 0xFF
        senddata[6] = data & 0xFF  # 数据低字节

        for i in range(7):
            senddata[7] += senddata[i]  # 计算校验和

        senddata[7] = senddata[7] & 0xFF  # 校验和取低8��
        return senddata

    def packet_data_runze(self, cmd, data=0):
        # 组装Runze设备的数据包，包含命令和数据，固定包格式
        senddata = [0] * 8
        senddata[0] = 0xCC  # 包头
        senddata[1] = self.slave_id  # 从机地址
        senddata[2] = cmd  # 命令字
        senddata[3] = data & 0xFF  # 数据低字节
        senddata[4] = (data >> 8) & 0xFF  # 数据高字节
        senddata[5] = 0xDD  # 包尾

        sum = 0
        for i in range(6):
            sum += senddata[i]  # 计算校验和

        senddata[6] = sum & 0xFF  # 校验和低8位
        senddata[7] = (sum >> 8) & 0xFF  # 校验和高8位
        return senddata

    def packet_data_runze_lm60b(self, cmd, data=0):
        # 组装Runze LM60B设备的数据包，包含命令和数据，固定包格式
        senddata = [0] * 10
        senddata[0] = 0xCC  # 包头
        senddata[1] = self.slave_id  # 从机地址
        senddata[2] = cmd  # 命令字
        senddata[3] = data & 0xFF  # 数据低字节
        senddata[4] = (data >> 8) & 0xFF  # 数据次低字节
        senddata[5] = (data >> 16) & 0xFF  # 数据次高字节
        senddata[6] = (data >> 24) & 0xFF  # 数据高字节
        senddata[7] = 0xDD  # 包尾

        sum = 0
        for i in range(8):
            sum += senddata[i]  # 计算校验和

        senddata[8] = sum & 0xFF  # 校验和低8位
        senddata[9] = (sum >> 8) & 0xFF  # 校验和高8位
        return senddata

    def send_data(self, bsend):
        if self.tcp_client is not None:
            self.tcp_client.send(bsend)
        else:
            self.ser.reset_input_buffer()
            self.ser.write(bsend)
            #self.ser.flush()

    def recv_data(self):
        if self.tcp_client is not None:
            return self.tcp_client.recv(BUFFER_SIZE)
        else:
            return self.ser.read(BUFFER_SIZE)

    def __del__(self):
        try:
            if self.ser is not None:
                self.ser.close()
            if self.tcp_client is not None:
                self.tcp_client.close()
        except AttributeError:
            pass
