# coding=utf-8
# !/usr/bin/env python
"""
mod:"SRND_16_IO" -- Setup and initialisation HARDWARE for the srnd-16 board


This module provides the necessary functions to setup and initialise the hardware for the srnd-16 board.
============================
module:: srnd_16_io
platform:: Windows, Unix
synopsis:: Setup and initialisaztion routines for the srnd-16 board
Performs the initial setup of the srnd-16 board and provides functions to read and write to the board.
Reads and sanitises a graph from a GraphML file
This graph is populated with objects relates
"""
import re
import os
import inspect
import sys
import logging
import time

from Drivers.EthernetDevices.tools.modbus_rtu_over_tcp_labware import ModbusRtuOverTcpClientDevice

class SRND_16_IO(ModbusRtuOverTcpClientDevice):
    """
    This provides a python class for the SRND-16 board. It provides functions to read and write to the board.
    """
    def __init__(self, address=None, slave_id=None, device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False, **kwargs):
        """
        Initializer of the SRND_16_IO class.


        This function sets up the modbus tcp connection to the SRND-16 board.

        Args:
            address (str): The port name/number of the device
            slave_id (int): The slave id of the tcp device
            device_name (str): A descriptive name for the device, used mainly in debug prints.
            connect_on_instantiation (bool): (optional) determines if the connection is established on instantiation of
            the class. Default: Off
            soft_fail_for_testing (bool): (optional) switch for just logging an error rather than raising it. Default: False
        """
        super().__init__(address, device_name, soft_fail_for_testing)
        self.logger = logging.getLogger("main_logger.srnd_io_logger")
        # answer check?
        self.slave_id = int(slave_id)
        if connect_on_instantiation:
            self.connect()

    def read_io_coil(self, io_device_port):
        """
        Read the coil input of the SRND hardware
        MODBUS COIL ADDRESS: DI 10000-19999
        :param int io_device_port: coil address
        :return: call back to send_message with a request to return
        """
        address = int(io_device_port)
        #self.logger.info('read io coil {0}'.format(address))
        response = self.modbus_client.read_coils(address=address, count=1, slave=self.slave_id).bits
        return response[0]

    def write_io_coil(self, io_device_port, value):
        """
        Write the coil input of the SRND hardware
        MODBUS COIL ADDRESS: DO 00000-09999
        :param int io_device_port: call back to send_message with a request to return
        :param Bool value: coil value
        :return: call back to send_message with a request to return
        """
        address = int(io_device_port)
        #self.logger.info('read io coil {0}'.format(address))
        self.modbus_client.write_coils(address=address, values=[value], slave=self.slave_id)


if __name__ == '__main__':
    srnd = SRND_16_IO(address="192.168.1.9:25", slave_id=1, device_name="test")
    test_number= 8
    # srnd.write_io_coil(13, False)
    # print("False")
    # time.sleep(1)
    # srnd.write_io_coil(13, True)
    # time.sleep(1)
    # print("True")
    message=srnd.read_io_coil(test_number)
    # print(message)
    # time.sleep(1)
    # srnd.write_io_coil(test_number, False)
    # time.sleep(1)
    # message = srnd.read_io_coil(test_number)
    # print(message)
    # srnd.write_io_coil(test_number, True)
    srnd.write_io_coil(test_number, False)
    # time.sleep(1)
    # message = srnd.read_io_coil(test_number)
    # print(message)