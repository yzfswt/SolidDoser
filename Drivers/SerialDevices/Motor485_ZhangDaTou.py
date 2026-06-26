from Drivers.SerialDevices.Common_Serial import Common_Serial

class Motor_Bottom:
    def __init__(self, serial_port: Common_Serial, address: int):
        self.serial_port = serial_port
        self.address = address

    def _raw_validator(self, resp: bytes):
        if len(resp) < 1:
            return False, "header_too_short"
        if resp[0] != self.address:
            return False, f"address_mismatch(expected={self.address}, actual={resp[0]})"
        return True, "ok"

    def Run(self):
        # 启动电机
        data = bytes([self.address, 0xF6, 0x01,0x01,0xF4,0x00,0x00,0x6B])
        self.serial_port.sendraw(data, 4, validator=self._raw_validator, retries=2, retry_delay_s=0.1)

    def stop(self):
        # 停止电机
        data = bytes([self.address, 0xFE,0x98,0x00,0x6B])
        self.serial_port.sendraw(data, 4, validator=self._raw_validator, retries=2, retry_delay_s=0.1)
