import time
from Drivers.SerialDevices.Common_Serial import Common_Serial

class Motor:
    def __init__(self, serial_port: Common_Serial, address: int):
        self.serial_port = serial_port
        self.address = address
        self.set_speed_mode()
        self.set_direction()

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

    def set_speed_mode(self):
        # 配置电机为速度模式
        data = bytes([self.address, 0x06, 0x62, 0x00, 0x00, 0x02])
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

    def set_direction(self):
        # 配置电机方向
        data = bytes([self.address, 0x06, 0x00, 0x07, 0x00, 0x01])
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

    def set_speed(self,speed_rpm: int):
        #设置运行速度
        speed_bytes = speed_rpm.to_bytes(2, byteorder='big', signed=False)
        data = bytes([self.address, 0x06,0x62,0x03]) + speed_bytes
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

    def Run(self):
        # 启动电机
        data = bytes([self.address, 0x06, 0x60, 0x02, 0x00, 0x10])
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

    def stop(self):
        # 停止电机
        data = bytes([self.address, 0x06, 0x60, 0x02, 0x00, 0x40])
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
        # return recv == packet

    def get_state(self):
        data = bytes([self.address, 0x03, 0x10, 0x03, 0x00, 0x01])
        recv = self.serial_port.sendcmd(
            data, 7, validator=self._modbus_validator(0x03), retries=2, retry_delay_s=0.1
        )
        # packet = self.serial_port.crc16(data)
        # self.serial_port.ser.reset_input_buffer()
        # self.serial_port.ser.reset_output_buffer()
        # print('发送数据:', packet.hex(' ').upper())
        # self.serial_port.ser.write(packet)
        # recv = self.serial_port.ser.read(7)  # 修改为读取7字节
        # print('接收数据:', recv.hex(' ').upper())

        # 判断字节长度是否为7
        if len(recv) != 7:
            print(f"错误：接收数据长度不正确，期望7字节，实际接收{len(recv)}字节")
            return None

        # 截取第4、第5个字节（索引3和4）
        status_bytes = recv[3:5]

        # 将截取的字节转换为十六进制字符串，再转换为二进制字符串
        hex_str = status_bytes.hex().upper()
        # 导入hex_to_bin_padded函数来进行转换
        from tools.hex_utils import hex_to_bin_padded
        binary_str = hex_to_bin_padded(hex_str, 16)  # 2字节=16位

        print(f"状态字节: {hex_str}, 二进制: {binary_str}")

        # 判断第三位（bit2，从右往左数第3位，索引为2）是否为1
        # 注意：二进制字符串是从左到右的，所以需要从右边开始数
        bit2 = binary_str[-3]  # 从右边数第3位

        if bit2 == '0':
            return False
        elif bit2 == '1':
            return True
        else:
            print(f"错误：无法解析bit2值: {bit2}")
            return None

    def get_speed(self):
        data = bytes([self.address, 0x03, 0x62, 0x03, 0x00, 0x01])
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
            # 返回数据格式: 地址 03 02 XX XX CRC16
            value = int.from_bytes(recv[4:6], byteorder='big', signed=False)
            return value

    def timed_stir(self, speed_rpm: int, duration_seconds: int):
        """
        定时搅拌方法
        
        Args:
            speed_rpm: 搅拌转速（转/分钟）
            duration_seconds: 搅拌持续时间（秒）
        
        Returns:
            bool: 操作是否成功完成
        """
        import time
        try:
            # 设置电机速度
            speed_result = self.set_speed(speed_rpm)
            if not speed_result:
                print(f"设置速度失败: {speed_rpm} RPM")
                return False
            time.sleep(0.5)
            # 启动电机
            run_result = self.Run()
            
            print(f"电机已启动，以{speed_rpm} RPM速度搅拌{duration_seconds}秒")
            
            # 计时等待
            time.sleep(duration_seconds)
            
            # 停止电机
            stop_result = self.stop()
            if not stop_result:
                print("停止电机失败")
                return False
            
            print(f"定时搅拌完成，已停止电机")
            return True
        except Exception as e:
            print(f"定时搅拌过程中发生错误: {e}")
            # 尝试停止电机
            try:
                self.stop()
            except:
                pass
            return False
        return None
