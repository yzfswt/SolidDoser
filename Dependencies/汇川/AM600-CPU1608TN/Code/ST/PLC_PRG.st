(* ==============================================
   PLC_PRG — 对接 EtherCAT SoftMotion 真实轴名
     EtherCAT 接线顺序：分度 → 升降 → 搅拌 → 水平 → 承粉
     Axis=分度 Axis_1=升降 Axis_2=搅拌 Axis_3=水平 Axis_4=承粉

   ★ InoProShop 粘贴注意 ★
   打开已有 PLC_PRG，不要新建；不要粘 PROGRAM / END_PROGRAM
   1. 声明区：只粘 【声明开始】～【声明结束】
   2. 实现区：只粘 【实现开始】～【实现结束】
   3. 先确保工程树里已有 FB_AxisHost、FB_AxisVelocityHost 且能单独编译通过

   轴命令/状态走 D 区 WORD（AM600 线圈写不进 %MX）：
     Cmd_*: bit0=Power bit1=Home bit2=Move bit3=Stop
     Sts_*: bit0=PowerOk bit1=HomeDone bit2=MoveDone bit3=Homed bit4=Moving bit5=Alarm
   ★ PLC_PRG 必须加入 EtherCAT_Task（勿放 MainTask）
   ============================================== *)

(* ========== 【声明开始】 ========== *)
VAR
    fbHori : FB_AxisHost;
    fbLift : FB_AxisHost;
    fbStir : FB_AxisVelocityHost;
    fbIdx  : FB_AxisHost;
    fbPwd  : FB_AxisHost;
END_VAR
(* ========== 【声明结束】 ========== *)

(* ========== 【实现开始】 ========== *)
(* 上电/下载后首扫清轴命令字，避免 RETAIN 残留导致自使能 *)
IF NOT bAxisCmdCleared THEN
    Cmd_Hori_W := 0;
    Cmd_Lift_W := 0;
    Cmd_Stir_W := 0;
    Cmd_Idx_W := 0;
    Cmd_Pwd_W := 0;
    Cmd_VibrationW := 0;
    Cmd_IonFanW := 0;
    bAxisCmdCleared := TRUE;
END_IF;

(* DO：振动 Q0.7 / 离子风扇 Q0.6 *)
DO_Vibration := Cmd_VibrationW <> 0;
DO_IonFan    := Cmd_IonFanW <> 0;

fbHori(
    Axis := Axis_3,
    CmdPower := (Cmd_Hori_W AND 16#0001) <> 0,
    CmdHome := (Cmd_Hori_W AND 16#0002) <> 0,
    CmdMove := (Cmd_Hori_W AND 16#0004) <> 0,
    CmdStop := (Cmd_Hori_W AND 16#0008) <> 0,
    PosTarget := Pos_Hori_Target,
    Velocity := Vel_Hori,
    StatusPowerOk => Sts_Hori_PowerOk,
    StatusHomeDone => Sts_Hori_HomeDone,
    StatusMoveDone => Sts_Hori_MoveDone,
    StatusHomed => Sts_Hori_Homed,
    StatusMoving => Sts_Hori_Moving,
    StatusAlarm => Sts_Hori_Alarm,
    PosActual => Pos_Hori_Actual
);
Sts_Hori_W := 0;
IF Sts_Hori_PowerOk THEN Sts_Hori_W := Sts_Hori_W OR 16#0001; END_IF;
IF Sts_Hori_HomeDone THEN Sts_Hori_W := Sts_Hori_W OR 16#0002; END_IF;
IF Sts_Hori_MoveDone THEN Sts_Hori_W := Sts_Hori_W OR 16#0004; END_IF;
IF Sts_Hori_Homed THEN Sts_Hori_W := Sts_Hori_W OR 16#0008; END_IF;
IF Sts_Hori_Moving THEN Sts_Hori_W := Sts_Hori_W OR 16#0010; END_IF;
IF Sts_Hori_Alarm THEN Sts_Hori_W := Sts_Hori_W OR 16#0020; END_IF;

fbIdx(
    Axis := Axis,
    CmdPower := (Cmd_Idx_W AND 16#0001) <> 0,
    CmdHome := (Cmd_Idx_W AND 16#0002) <> 0,
    CmdMove := (Cmd_Idx_W AND 16#0004) <> 0,
    CmdStop := (Cmd_Idx_W AND 16#0008) <> 0,
    PosTarget := Pos_Idx_Target,
    Velocity := Vel_Idx,
    StatusPowerOk => Sts_Idx_PowerOk,
    StatusHomeDone => Sts_Idx_HomeDone,
    StatusMoveDone => Sts_Idx_MoveDone,
    StatusHomed => Sts_Idx_Homed,
    StatusMoving => Sts_Idx_Moving,
    StatusAlarm => Sts_Idx_Alarm,
    PosActual => Pos_Idx_Actual
);
Sts_Idx_W := 0;
IF Sts_Idx_PowerOk THEN Sts_Idx_W := Sts_Idx_W OR 16#0001; END_IF;
IF Sts_Idx_HomeDone THEN Sts_Idx_W := Sts_Idx_W OR 16#0002; END_IF;
IF Sts_Idx_MoveDone THEN Sts_Idx_W := Sts_Idx_W OR 16#0004; END_IF;
IF Sts_Idx_Homed THEN Sts_Idx_W := Sts_Idx_W OR 16#0008; END_IF;
IF Sts_Idx_Moving THEN Sts_Idx_W := Sts_Idx_W OR 16#0010; END_IF;
IF Sts_Idx_Alarm THEN Sts_Idx_W := Sts_Idx_W OR 16#0020; END_IF;

fbLift(
    Axis := Axis_1,
    CmdPower := (Cmd_Lift_W AND 16#0001) <> 0,
    CmdHome := (Cmd_Lift_W AND 16#0002) <> 0,
    CmdMove := (Cmd_Lift_W AND 16#0004) <> 0,
    CmdStop := (Cmd_Lift_W AND 16#0008) <> 0,
    PosTarget := Pos_Lift_Target,
    Velocity := Vel_Lift,
    StatusPowerOk => Sts_Lift_PowerOk,
    StatusHomeDone => Sts_Lift_HomeDone,
    StatusMoveDone => Sts_Lift_MoveDone,
    StatusHomed => Sts_Lift_Homed,
    StatusMoving => Sts_Lift_Moving,
    StatusAlarm => Sts_Lift_Alarm,
    PosActual => Pos_Lift_Actual
);
Sts_Lift_W := 0;
IF Sts_Lift_PowerOk THEN Sts_Lift_W := Sts_Lift_W OR 16#0001; END_IF;
IF Sts_Lift_HomeDone THEN Sts_Lift_W := Sts_Lift_W OR 16#0002; END_IF;
IF Sts_Lift_MoveDone THEN Sts_Lift_W := Sts_Lift_W OR 16#0004; END_IF;
IF Sts_Lift_Homed THEN Sts_Lift_W := Sts_Lift_W OR 16#0008; END_IF;
IF Sts_Lift_Moving THEN Sts_Lift_W := Sts_Lift_W OR 16#0010; END_IF;
IF Sts_Lift_Alarm THEN Sts_Lift_W := Sts_Lift_W OR 16#0020; END_IF;

fbStir(
    Axis := Axis_2,
    CmdPower := (Cmd_Stir_W AND 16#0001) <> 0,
    CmdHome := (Cmd_Stir_W AND 16#0002) <> 0,
    CmdMove := (Cmd_Stir_W AND 16#0004) <> 0,
    CmdStop := (Cmd_Stir_W AND 16#0008) <> 0,
    PosTarget := Pos_Stir_Target,
    Velocity := Vel_Stir,
    StatusPowerOk => Sts_Stir_PowerOk,
    StatusHomeDone => Sts_Stir_HomeDone,
    StatusMoveDone => Sts_Stir_MoveDone,
    StatusHomed => Sts_Stir_Homed,
    StatusMoving => Sts_Stir_Moving,
    StatusAlarm => Sts_Stir_Alarm,
    PosActual => Pos_Stir_Actual
);
Sts_Stir_W := 0;
IF Sts_Stir_PowerOk THEN Sts_Stir_W := Sts_Stir_W OR 16#0001; END_IF;
IF Sts_Stir_HomeDone THEN Sts_Stir_W := Sts_Stir_W OR 16#0002; END_IF;
IF Sts_Stir_MoveDone THEN Sts_Stir_W := Sts_Stir_W OR 16#0004; END_IF;
IF Sts_Stir_Homed THEN Sts_Stir_W := Sts_Stir_W OR 16#0008; END_IF;
IF Sts_Stir_Moving THEN Sts_Stir_W := Sts_Stir_W OR 16#0010; END_IF;
IF Sts_Stir_Alarm THEN Sts_Stir_W := Sts_Stir_W OR 16#0020; END_IF;

fbPwd(
    Axis := Axis_4,
    CmdPower := (Cmd_Pwd_W AND 16#0001) <> 0,
    CmdHome := (Cmd_Pwd_W AND 16#0002) <> 0,
    CmdMove := (Cmd_Pwd_W AND 16#0004) <> 0,
    CmdStop := (Cmd_Pwd_W AND 16#0008) <> 0,
    PosTarget := Pos_Pwd_Target,
    Velocity := Vel_Pwd,
    bUseControllerHoming := TRUE,
    bHomeSwitch := DI_Pwd_Home,
    bHomeSwitchActiveHigh := TRUE,
    (* 机械负向找原点；FALSE=负向。碰到后 FAST_SLOW 会反向找下降沿 *)
    bHomeDirPositive := FALSE,
    fHomeVelFast := 10.0,
    fHomeVelSlow := 2.0,
    fHomeAcc := 100.0,
    fHomeDec := 100.0,
    StatusPowerOk => Sts_Pwd_PowerOk,
    StatusHomeDone => Sts_Pwd_HomeDone,
    StatusMoveDone => Sts_Pwd_MoveDone,
    StatusHomed => Sts_Pwd_Homed,
    StatusMoving => Sts_Pwd_Moving,
    StatusAlarm => Sts_Pwd_Alarm,
    PosActual => Pos_Pwd_Actual
);
Sts_Pwd_W := 0;
IF Sts_Pwd_PowerOk THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0001; END_IF;
IF Sts_Pwd_HomeDone THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0002; END_IF;
IF Sts_Pwd_MoveDone THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0004; END_IF;
IF Sts_Pwd_Homed THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0008; END_IF;
IF Sts_Pwd_Moving THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0010; END_IF;
IF Sts_Pwd_Alarm THEN Sts_Pwd_W := Sts_Pwd_W OR 16#0020; END_IF;
(* ========== 【实现结束】不要粘 END_PROGRAM ========== *)
