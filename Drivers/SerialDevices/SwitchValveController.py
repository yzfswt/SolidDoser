import time
from Drivers.SerialDevices.Common_Serial import Common_Serial

class SwitchValve:
    def __init__(self, serial_port: Common_Serial, address: int):
        self.serial_port = serial_port
        self.address = address

    def _modbus_validator(self, expected_func: int):
        def _validate(resp: bytes):
            if len(resp) < 2:
                return False, "header_too_short"
            if resp[0] != self.address:
                return False, f"address_mismatch(expected={self.address}, actual={resp[0]})"
            if resp[1] != expected_func:
                return False, f"function_mismatch(expected={expected_func}, actual={resp[1]})"
            return True, "ok"

        return _validate

    def move_to_position(self, position: int):
        time.sleep(1)
        data = bytes([self.address, 0x05, 0x00, position,0xFF,0x00])
        self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
        )
        time.sleep(2)
        # 读取一次位置；若读空则重发位置命令，若收到 11 03 EE 开头则先复位后再执行原位置命令
        query_data = bytes([self.address, 0x04, 0x00,0x00, 0x00,0x02])
        query_recv = self.serial_port.sendcmd(query_data, 9, retries=2, retry_delay_s=0.1)

        if not query_recv:
            self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
            )
            time.sleep(2)
        elif query_recv.startswith(bytes([0x11, 0x03, 0xEE])):
            self.reset()
            time.sleep(3)
            self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
            )
            time.sleep(2)

        pos = self.query_position()
        print(f'当前位置: {pos}, 目标位置: {position}')
        return pos == position

    def reset(self):
        data = bytes([self.address, 0x05, 0x00, 0x00, 0xFF, 0x00])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
        )
        return len(recv) == 8


    def query_position(self):
        data = bytes([self.address, 0x04, 0x00,0x00, 0x00,0x02])
        recv = self.serial_port.sendcmd(
            data, 9, validator=self._modbus_validator(0x04), retries=2, retry_delay_s=0.1
        )
        if len(recv) == 9:
            # 返回数据格式: 地址 04 04 4C 00 00 XX CRC16
            value = int.from_bytes(recv[6:7], byteorder='big', signed=False)
            return value
        return None
