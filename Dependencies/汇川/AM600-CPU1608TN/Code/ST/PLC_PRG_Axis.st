(* ==============================================
   PLC_PRG — 对接 EtherCAT SoftMotion 真实轴名
     Axis=水平 Axis_1=分度 Axis_2=升降 Axis_3=搅拌 Axis_4=承粉

   ★ InoProShop 粘贴注意 ★
   打开已有 PLC_PRG，不要新建；不要粘 PROGRAM / END_PROGRAM
   1. 声明区：只粘 【声明开始】～【声明结束】
   2. 实现区：只粘 【实现开始】～【实现结束】
   3. 先确保工程树里已有 FB_AxisHost 且能单独编译通过
   ============================================== *)

(* ========== 【声明开始】 ========== *)
VAR
    fbHori : FB_AxisHost;
    fbLift : FB_AxisHost;
    fbStir : FB_AxisHost;
    fbIdx  : FB_AxisHost;
    fbPwd  : FB_AxisHost;
END_VAR
(* ========== 【声明结束】 ========== *)

(* ========== 【实现开始】 ========== *)
DO_Vibration := Cmd_Vibration;
DO_IonFan    := Cmd_IonFan;

fbHori(
    Axis := Axis,
    CmdPower := Cmd_Hori_Power,
    CmdHome := Cmd_Hori_Home,
    CmdMove := Cmd_Hori_Move,
    CmdStop := Cmd_Hori_Stop,
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

fbIdx(
    Axis := Axis_1,
    CmdPower := Cmd_Idx_Power,
    CmdHome := Cmd_Idx_Home,
    CmdMove := Cmd_Idx_Move,
    CmdStop := Cmd_Idx_Stop,
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

fbLift(
    Axis := Axis_2,
    CmdPower := Cmd_Lift_Power,
    CmdHome := Cmd_Lift_Home,
    CmdMove := Cmd_Lift_Move,
    CmdStop := Cmd_Lift_Stop,
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

fbStir(
    Axis := Axis_3,
    CmdPower := Cmd_Stir_Power,
    CmdHome := Cmd_Stir_Home,
    CmdMove := Cmd_Stir_Move,
    CmdStop := Cmd_Stir_Stop,
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

fbPwd(
    Axis := Axis_4,
    CmdPower := Cmd_Pwd_Power,
    CmdHome := Cmd_Pwd_Home,
    CmdMove := Cmd_Pwd_Move,
    CmdStop := Cmd_Pwd_Stop,
    PosTarget := Pos_Pwd_Target,
    Velocity := Vel_Pwd,
    StatusPowerOk => Sts_Pwd_PowerOk,
    StatusHomeDone => Sts_Pwd_HomeDone,
    StatusMoveDone => Sts_Pwd_MoveDone,
    StatusHomed => Sts_Pwd_Homed,
    StatusMoving => Sts_Pwd_Moving,
    StatusAlarm => Sts_Pwd_Alarm,
    PosActual => Pos_Pwd_Actual
);
(* ========== 【实现结束】不要粘 END_PROGRAM ========== *)
