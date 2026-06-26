from Drivers.SerialDevices.Common_Serial import Common_Serial
import time

class Pump:
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

    def move_absolute(self, position_ml: float):
        position_ul = int(position_ml * 1000)  # 转换为微升
        # 位置值转为4字节16进制
        pos_bytes = position_ul.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x14]) + pos_bytes
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )
        # 若recv为空，再次发送同样的指令
        max_retries = 3  # 最大重试次数
        retry_count = 0
        while not recv and retry_count < max_retries:
            print(f"未收到响应，第 {retry_count + 1} 次重试...")
            recv = self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x06), retries=1, retry_delay_s=0.1
            )
            retry_count += 1
        if not recv:
            print("多次重试后仍未收到响应")
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收数据:', recv.hex(' ').upper())
        # 实时读取位置直到到达目标
        time.sleep(7)
        while True:
            time.sleep(1)
            pos = self.get_current_volume()
            print(f'当前位置: {pos}, 目标位置: {position_ul}')
            if pos == position_ul:
                return True

    def force_reset(self):
        data = bytes([self.address, 0x06, 0x00, 0x14, 0xFF, 0xFF])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收数据:', recv.hex(' ').upper())
        
        # 复位后等待位置为0
        time.sleep(5)
        while True:
            time.sleep(1)
            pos = self.get_current_volume()
            print(f'当前位置: {pos}, 目标位置: 0')
            if pos == 0:
                return True

    def set_speed(self, speed_ml_s: float):
        speed_ul_s = int(speed_ml_s * 1000)  # 转换为微升每秒
        speed_bytes = speed_ul_s.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x0C]) + speed_bytes
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收数据:', recv.hex(' ').upper())

    def get_current_volume(self):
        data = bytes([self.address, 0x03, 0x00, 0x14, 0x00, 0x01])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x03), retries=2, retry_delay_s=0.1
        )
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收数据:', recv.hex(' ').upper())
        max_retries = 3  # 最大重试次数
        retry_count = 0
        while len(recv) != 8 and retry_count < max_retries:
            print(f"返回结果不是8位，第 {retry_count + 1} 次重试...")
            time.sleep(1)
            recv = self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x03), retries=1, retry_delay_s=0.1
            )
            retry_count += 1
        if len(recv) != 8:
            print("多次重试后返回结果仍不是8位")
            
        if len(recv) == 8:
            # 返回数据格式: 地址 03 00 14 XX XX CRC16
            value = int.from_bytes(recv[4:6], byteorder='big', signed=False)
            return value
        return None

    def query_speed(self):
        data = bytes([self.address, 0x03, 0x00, 0x0C, 0x00, 0x01])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x03), retries=2, retry_delay_s=0.1
        )
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收数据:', recv.hex(' ').upper())
        if len(recv) == 8:
            # 返回数据格式: 地址 03 00 0C XX XX CRC16
            value = int.from_bytes(recv[4:6], byteorder='big', signed=False)
            return value
        return None

class FixPump:
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

    def set_speed_rpm(self, speed_rpm: int):
        speed_value = int(speed_rpm)  # 转换为微升每秒
        speed_bytes = speed_value.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x0C]) + speed_bytes
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )

    def set_speed(self, speed_ml_s: float):
        """用户按ml/s设置速度，需要换算成rpm"""
        # 这里假设需要将ml/s转换为rpm，具体转换公式需根据实际硬件参数调整
        # 示例转换公式：speed_rpm = speed_ml_s * conversion_factor
        # 1转等于0.1ml
        conversion_factor = 1
        speed_rpm = speed_ml_s * conversion_factor
        speed_value = int(speed_rpm)  # 转换为微升每秒

        speed_bytes = speed_value.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x0C]) + speed_bytes
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )

    def set_injection_volume(self, volume_ml: float,conversion_factor:float):
        """用户按ml设置注射量，需要换算为转动次数n"""
        # 这里假设需要将ml转换为转动次数，具体转换公式需根据实际硬件参数调整
        # 示例转换公式：rotations  = volume_ml * conversion_factor
        # 1转动 = 0.1ml
        rotations = round(volume_ml / conversion_factor)

        volume_value = int(rotations)  # 转换为微升

        volume_bytes = volume_value.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x14]) + volume_bytes
        max_cmd_retries = 3
        cmd_ok = False
        for attempt in range(1, max_cmd_retries + 1):
            recv = self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
            )
            # 功能码06正常应答会回显请求前6字节（地址/功能码/寄存器/数据）
            if len(recv) == 8 and recv[:6] == data:
                cmd_ok = True
                break

            recv_hex = recv.hex(" ").upper() if recv else "EMPTY"
            expect_hex = data.hex(" ").upper()
            print(
                f"加液命令应答校验失败（第{attempt}次）：收到[{recv_hex}]，期望前6字节[{expect_hex}]"
            )
            print("执行定量泵复位，等待3秒后重发加液命令...")
            self.reset()
            time.sleep(3)

        if not cmd_ok:
            raise RuntimeError("定量泵加液命令多次重发后应答仍不一致")
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送设置注射量数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收设置注射量响应:', recv.hex(' ').upper())
        time.sleep(5)
        pos=0
        while pos!=volume_value and pos!=volume_value-1:
            time.sleep(1)
            pos = self.query_position()
            print(f'当前位置: {pos}, 目标位置: {volume_value}')

    def set_injection_turns(self, rotations: int):
        """直接设定转动圈数n"""

        volume_bytes = rotations.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06, 0x00, 0x14]) + volume_bytes
        max_cmd_retries = 3
        cmd_ok = False
        for attempt in range(1, max_cmd_retries + 1):
            recv = self.serial_port.sendcmd(
                data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
            )
            # 功能码06正常应答会回显请求前6字节（地址/功能码/寄存器/数据）
            if len(recv) == 8 and recv[:6] == data:
                cmd_ok = True
                break

            recv_hex = recv.hex(" ").upper() if recv else "EMPTY"
            expect_hex = data.hex(" ").upper()
            print(
                f"设定圈数命令应答校验失败（第{attempt}次）：收到[{recv_hex}]，期望前6字节[{expect_hex}]"
            )
            print("执行定量泵复位，等待3秒后重发设定圈数命令...")
            self.reset()
            time.sleep(3)

        if not cmd_ok:
            raise RuntimeError("定量泵设定圈数命令多次重发后应答仍不一致")
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送设置注射量数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(8)
        # print('接收设置注射量响应:', recv.hex(' ').upper())
        time.sleep(5)
        pos=0
        while pos!=rotations and pos!=rotations-1:
            time.sleep(1)
            pos = self.query_position()
            print(f'当前位置: {pos}圈, 目标位置: {rotations}圈')

    def stop(self):
        """停止动作"""
        data = bytes([self.address, 0x05, 0x01, 0x00, 0x00, 0x00])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
        )

    def resume(self):
        """继续运动"""
        data = bytes([self.address, 0x05, 0x01, 0xFF, 0x00, 0x00])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x05), retries=2, retry_delay_s=0.1
        )

    def reset(self):
        """复位动作"""
        data = bytes([self.address, 0x06, 0x00, 0x14, 0x00, 0x00])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x06), retries=2, retry_delay_s=0.1
        )

    def query_position(self):
        """查询当前位置，返回毫升(ml)单位，遵循协议格式：地址+03 00 14 +xx xx +crc16

        Args:
            conversion_factor: 转换因子，默认1转=0.1ml
        Returns:
            float: 当前位置(ml)，失败时返回None
        """
        # 协议格式解析：
        # 地址：设备地址
        # 03：功能码（读取保持寄存器）
        # 00 14：寄存器起始地址（十进制20）
        # 00 01：读取寄存器数量（十进制1，转换为两位十六进制00 01）
        data = bytes([self.address, 0x03, 0x00, 0x14, 0x00, 0x00])
        recv = self.serial_port.sendcmd(
            data, 8, validator=self._modbus_validator(0x03), retries=2, retry_delay_s=0.1
        )

        # 验证响应有效性
        if len(recv) != 8 or recv[0] != self.address or recv[1] != 0x03:
            print("查询位置响应无效")
            return None

        # 解析位置数据(从第3字节开始，共2字节)
        position_bytes = recv[4:6]
        position_value = int.from_bytes(position_bytes, byteorder='big', signed=False)

        # 转换为毫升单位
        return position_value
