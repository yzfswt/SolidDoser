# coding=utf-8
# !/usr/bin/env python
"""
:mod:"modbus_tcp_labware" -- Generic base class for communicating with lab equipment via modbus rtu over tcp connection
===================================

.. module::   modbus_rtu_over_tcp_labware
   :platform: Windows
   :synopsis: Generic base class to control lab equipment via modbus.
.. moduleauthor:: IKKEM 2024

(c) 2024 The IKKEM

This provides a generic python class for safe socket communication
with various lab equipment use modbus rtu over TCP connection interfaces (TCP client).
This parent class handles establishing a connection as well as sending and receiving commands.

"""

# system imports
import platform
import threading

# additional module imports
import logging

from pymodbus import FramerType
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerRTU

class ModbusRtuOverTcpClientDevice:
    """
    This is a generic parent class handling modbus rtu over tcp communication with lab equipment. It provides
    methods for opening and closing connections as well as a keepalive. It works by spawning a
    daemon thread which periodically checks a queue for commands. If no commands are enqueued,
    a keepalive method is executed periodically. Replies are put in their own reply queue where
    they can be retrieved at any time.
    """
    def __init__(self, address=None, device_name=None, soft_fail_for_testing=False):
        """
        Initializer of the SerialDevice class
        :param str address: The address name/number of the tcp device
        :param str device_name: A descriptive name for the device, used mainly in debug prints.
        :param bool soft_fail_for_testing: (optional) determines if an invalid serial port raises an error or merely
            logs a message. Default: Off
        """
        # note down current thread number
        self.current_thread = threading.get_ident()
        # implement class logger
        self.logger = logging.getLogger("main_logger.modbus_tcp_device_logger")
        # DEBUG testing switch, to allow soft-fails instead of exceptions
        self.__soft_fail_for_testing = soft_fail_for_testing
        # check if the port passed is of the correct format
        if platform.system() == "Windows":
            try:
                if ":" in address:
                    self.server_ip = address.split(":")[0]
                    self.server_port = int(address.split(":")[1])
                else:
                    # allowing for soft fail in test modes, this will allow an outer script to continue, even if an
                    # invalid port was passed
                    if not self.__soft_fail_for_testing:
                        # in normal use raise an exception to make surrounding python scrips stop
                        raise (ValueError("The port number ({0}) is not a valid net port!".format(address)))
                    else:
                        # soft-fail error message
                        self.logger.debug("ERROR: The specified net port is not valid: {0}".format(address))
            except (AttributeError, ValueError) as e:
                # self.logger.debug a more descriptive error message before re-raising the exception
                self.logger.debug("ERROR: The specified net port is not valid: {0}".format(e))
                # raising the exception again so the surrounding script is aware that this failed
                raise  # raises the last exception again
        else:
            # TODO ADD address consistency checks for posix operating systems
            raise (OSError(
                "You are running a currently unsupported operating system: \"{0}\"".format(platform.system())
            ))

        self.device_name = device_name
        # 在 pymodbus 3.9.2+ 中，使用 FramerRTU 来指定 RTU framer
        self.modbus_client = ModbusTcpClient(
            host=self.server_ip,
            port=self.server_port,
            framer=FramerType.RTU
        )

    def connect(self):
        """
        Establishes a connection to the modbus tcp device.
        :return: True if connection was successful, False otherwise.
        """
        # create a modbus_client object
        if self.modbus_client.connect():
            print("Modbus Tcp Client Connected to {0} on port {1}".format(self.server_ip, self.server_port))
            self.logger.debug("Modbus Tcp Client Connected to {0} on port {1}".format(self.server_ip, self.server_port))
            return True
        else:
            self.logger.debug("ERROR: Failed to connect to Modbus Tcp Client {0} on port {1}".format(self.server_ip, self.server_port))
            return False

    def close(self):
        """
        Close a connection to the modbus tcp device.
        :return: True if connection was successful, False otherwise.
        """
        self.modbus_client.close()
