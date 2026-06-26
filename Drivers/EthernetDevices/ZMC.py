import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from zmcdll.zauxdllPython import ZAUXDLL


class ZMC:
    def __init__(self,ip:str):
        self.ip=ip
        self.Zmc = ZAUXDLL()
        self.Connect(ip)

    def Connect(self, strtemp):
        print("当前正运动板卡的连接ip是 ：", strtemp)
        try:
            if self.Zmc.handle.value is not None:
                self.Zmc.ZAux_Close()
            iresult = self.Zmc.ZAux_OpenEth(strtemp)
            if 0 != iresult:
                print("网络连接", f"连接失败，错误码：{iresult}")
            else:
                print("网络连接", "连接成功")
            mode = 1
            axis_units = 3200
            # 设置轴类型 - 为两个轴都设置
            self.Zmc.ZAux_Direct_SetAtype(0, mode)
            self.Zmc.ZAux_Direct_SetAtype(1, mode)
            self.Zmc.ZAux_Direct_SetAtype(2, mode)
            self.Zmc.ZAux_Direct_SetAtype(3, mode)
            self.Zmc.ZAux_Direct_SetAtype(4, mode)
            self.Zmc.ZAux_Direct_SetAtype(5, mode)
            self.Zmc.ZAux_Direct_SetAtype(6, mode)
            self.Zmc.ZAux_Direct_SetAtype(7, mode)
            # 设置轴脉冲当量 - 为两个轴都设置
            self.Zmc.ZAux_Direct_SetUnits(0, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(1, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(2, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(3, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(4, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(5, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(6, axis_units)
            self.Zmc.ZAux_Direct_SetUnits(7, axis_units)
        except Exception as e:
            print("网络连接", f"连接异常: {e}") 
    def Close(self):
        """关闭ZMC连接"""
        try:
            if self.Zmc.handle.value is not None:
                self.Zmc.ZAux_Close()
                print("ZMC连接已关闭")
            else:
                print("未检测到有效连接，无需关闭")
        except Exception as e:
            print("关闭连接时出现异常: ", e)
