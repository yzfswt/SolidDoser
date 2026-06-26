from Drivers.EthernetDevices.ZMC import ZMC

class MotorZmc:
    def __init__(self, zmc:ZMC, AxisNum: int):
        self.AxisNum = AxisNum
        self.Zmc = zmc.Zmc

    def StartStirrer(self, speed:float):
        if self.Zmc.handle.value is None:
            print("警告:未连接控制器")
            return
        # 转换为每秒转速
        float_tmp = float(speed)/60.0
        self.Zmc.ZAux_Direct_SetSpeed(self.AxisNum, float_tmp)
        self.Zmc.ZAux_Direct_Single_Vmove(self.AxisNum, 1)

    def StopStirrer(self):
        if self.Zmc.handle.value is None:
            print( "警告:未连接控制器")
            return
        isidle=self.Zmc.ZAux_Direct_GetIfIdle(self.AxisNum)[1].value
        if isidle:
            print("警告:已停止")
            return
        self.Zmc.ZAux_Direct_Single_Cancel(self.AxisNum, 2)

    def get_state(self):
        if self.Zmc.handle.value is None:
            print("警告:未连接控制器")
            return None
        return self.Zmc.ZAux_Direct_GetIfIdle(self.AxisNum)[1].value
    
    def get_speed(self):
        if self.Zmc.handle.value is None:
            print("警告:未连接控制器")
            return None
        speed_result=self.Zmc.ZAux_Direct_GetSpeed(self.AxisNum)[1].value
        fvspeed = float(round(speed_result, 3))
        fvspeed = fvspeed * 60.0  # 转换为每分钟转速
        return fvspeed