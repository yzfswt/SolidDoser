(* GVL_HostAxis — 上位机 Modbus 接口
   AM600：保持寄存器地址 = %MW 索引（1:1）；%MDn 占 MW(2n)/MW(2n+1)
   例：%MW230 → HR230；%MD250 → HR500/501
   线圈区对应 %QX，不能可靠写 %MX，故轴命令/状态走 WORD
   %MW230+ 在掉电保持区，须 RETAIN PERSISTENT；PLC_PRG 首扫清命令字
*)
VAR_GLOBAL RETAIN PERSISTENT
    (* 轴目标/速度/实际：%MD → 上位机 HR = 2×MD 索引 *)
    Pos_Hori_Target AT %MD250 : REAL;
    Vel_Hori AT %MD251 : REAL;
    Pos_Hori_Actual AT %MD252 : REAL;

    Pos_Idx_Target AT %MD265 : REAL;
    Vel_Idx AT %MD266 : REAL;
    Pos_Idx_Actual AT %MD267 : REAL;

    Pos_Lift_Target AT %MD255 : REAL;
    Vel_Lift AT %MD256 : REAL;
    Pos_Lift_Actual AT %MD257 : REAL;

    Pos_Stir_Target AT %MD260 : REAL;
    Vel_Stir AT %MD261 : REAL;
    Pos_Stir_Actual AT %MD262 : REAL;

    Pos_Pwd_Target AT %MD270 : REAL;
    Vel_Pwd AT %MD271 : REAL;
    Pos_Pwd_Actual AT %MD272 : REAL;

    (* Cmd bit：0=Power 1=Home 2=Move 3=Stop
       Sts bit：0=PowerOk 1=HomeDone 2=MoveDone 3=Homed 4=Moving 5=Alarm *)
    Cmd_Hori_W AT %MW230 : WORD := 0;
    Sts_Hori_W AT %MW231 : WORD := 0;
    Cmd_Lift_W AT %MW232 : WORD := 0;
    Sts_Lift_W AT %MW233 : WORD := 0;
    Cmd_Stir_W AT %MW234 : WORD := 0;
    Sts_Stir_W AT %MW235 : WORD := 0;
    Cmd_Idx_W AT %MW236 : WORD := 0;
    Sts_Idx_W AT %MW237 : WORD := 0;
    Cmd_Pwd_W AT %MW238 : WORD := 0;
    Sts_Pwd_W AT %MW239 : WORD := 0;

    Sts_Hori_PowerOk : BOOL;
    Sts_Hori_HomeDone : BOOL;
    Sts_Hori_MoveDone : BOOL;
    Sts_Hori_Homed : BOOL;
    Sts_Hori_Moving : BOOL;
    Sts_Hori_Alarm : BOOL;

    Sts_Idx_PowerOk : BOOL;
    Sts_Idx_HomeDone : BOOL;
    Sts_Idx_MoveDone : BOOL;
    Sts_Idx_Homed : BOOL;
    Sts_Idx_Moving : BOOL;
    Sts_Idx_Alarm : BOOL;

    Sts_Lift_PowerOk : BOOL;
    Sts_Lift_HomeDone : BOOL;
    Sts_Lift_MoveDone : BOOL;
    Sts_Lift_Homed : BOOL;
    Sts_Lift_Moving : BOOL;
    Sts_Lift_Alarm : BOOL;

    Sts_Stir_PowerOk : BOOL;
    Sts_Stir_HomeDone : BOOL;
    Sts_Stir_MoveDone : BOOL;
    Sts_Stir_Homed : BOOL;
    Sts_Stir_Moving : BOOL;
    Sts_Stir_Alarm : BOOL;

    Sts_Pwd_PowerOk : BOOL;
    Sts_Pwd_HomeDone : BOOL;
    Sts_Pwd_MoveDone : BOOL;
    Sts_Pwd_Homed : BOOL;
    Sts_Pwd_Moving : BOOL;
    Sts_Pwd_Alarm : BOOL;

    Cmd_VibrationW AT %MW245 : WORD := 0;
    Cmd_IonFanW AT %MW246 : WORD := 0;
END_VAR

VAR_GLOBAL
    DO_Vibration AT %QX0.7 : BOOL;
    DO_IonFan AT %QX0.6 : BOOL;
    bAxisCmdCleared : BOOL := FALSE;
    (* 承粉原点：传感器接 STF X7（探针1）。
       不要用 AT %I*（未配 VAR_CONFIG 会报 C0128）。
       InoProShop：承粉从站 → I/O 映射 → X7/探针1 的变量列选 GVL_HostAxis.DI_Pwd_Home *)
    DI_Pwd_Home : BOOL;
END_VAR
