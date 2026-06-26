from Drivers.SerialDevices.Common_Serial import Common_Serial
from Drivers.SerialDevices.tools.hex_utils import append_crc16, hex_to_dec
import time

class TemperatureController:
    def __init__(self, serial_port: Common_Serial, address: int):
        self.serial_port = serial_port
        self.address = address

    def set_temperature(self, set_temp: float):
        """
        设置温控器的温度值。
        set_temp: 要设置的温度值
        返回: 操作是否成功
        """
        try:
            temp_val = float(set_temp)
            temp_int = int(round(temp_val * 10))  # 放大10倍并取整
            hex_temp = f'{temp_int:04X}'  # 4位十六进制
            hex_high = hex_temp[:2]
            hex_low = hex_temp[2:]
            cmd = f'{self.address:02X}060000{hex_high}{hex_low}'
            cmd_crc = append_crc16(cmd)
            
            for attempt in range(3):
                # 使用serial_port发送命令
                self.serial_port.ser.reset_input_buffer()
                self.serial_port.ser.write(bytes.fromhex(cmd_crc))
                print(f"已发送{self.address}号温控器设定温度指令: {cmd_crc}")

                # 读取响应
                resp = self.serial_port.ser.read(8)  # 期望返回8字节
                if len(resp) == 8:
                    print(f"接收{self.address}号温控器设定温度响应: {resp.hex(' ').upper()}")
                    return True

                print(f"未收到{self.address}号温控器完整响应")
                if attempt == 0:
                    print(f"{self.address}号温控器将在1秒后重试设定温度")
                    time.sleep(1)

            return False
        except Exception as e:
            print(f"设定温度失败: {e}")
            return False

    def read_temperature(self):
        """
        读取温控器的当前温度值。
        返回: 温度值字符串（保留1位小数），读取失败返回None
        """
        # 指令内容，使用指定的设备地址
        cmd = f'{self.address:02X}03004A0001'
        cmd_crc = append_crc16(cmd)
        
        try:
            self.serial_port.ser.reset_input_buffer()
            self.serial_port.ser.write(bytes.fromhex(cmd_crc))
            #print(f"已发送{self.address}号温控器读取温度指令: {cmd_crc}")
            
            resp = self.serial_port.ser.read(7)  # 期望返回7字节
            if len(resp) == 7:
                #print(f"接收{self.address}号温控器读取温度响应: {resp.hex(' ').upper()}")
                # 第4、5字节为温度数据
                temp_hex = resp[3:5].hex().upper()
                temp = hex_to_dec(temp_hex)
                temp = temp / 10.0
                return f"{temp:.1f}"
            else:
                #print(f"未收到{self.address}号温控器完整响应")
                return None
        except Exception as e:
            print(f"读取温度失败: {e}")
            return None

    def query_status(self):
        """
        查询温控器的状态。
        返回: 状态数据字典，失败返回None
        """
        # 这里可以根据温控器的协议实现状态查询功能
        # 示例实现（具体协议可能需要调整）
        try:
            # 读取温度作为基本状态
            temperature = self.read_temperature()
            if temperature is not None:
                return {
                    'temperature': temperature,
                    'device_address': self.address,
                    'status': 'online'
                }
            else:
                return None
        except Exception as e:
            print(f"查询状态失败: {e}")
            return None