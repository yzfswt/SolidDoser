(* GVL_HostAxis - Modbus host interface
   InoProShop style: Name AT %addr : TYPE;
   REAL -> %MDn where n = host MW/2 (D500 -> MD250)

   ★ AM600：%MX500+ / %MD250+ 落在掉电保持区，必须同时加 RETAIN PERSISTENT
   ★ 物理输出 %QXx.x 不要放 RETAIN 区，单独用普通 VAR_GLOBAL
*)
VAR_GLOBAL RETAIN PERSISTENT
    (* Axis0 Horizontal M500 / D500 *)
    Cmd_Hori_Power AT %MX500.0 : BOOL;
    Sts_Hori_PowerOk AT %MX502.0 : BOOL;
    Cmd_Hori_Home AT %MX510.0 : BOOL;
    Cmd_Hori_Move AT %MX512.0 : BOOL;
    Cmd_Hori_Stop AT %MX513.0 : BOOL;
    Sts_Hori_HomeDone AT %MX520.0 : BOOL;
    Sts_Hori_MoveDone AT %MX521.0 : BOOL;
    Sts_Hori_Homed AT %MX522.0 : BOOL;
    Sts_Hori_Moving AT %MX523.0 : BOOL;
    Sts_Hori_Alarm AT %MX524.0 : BOOL;
    Pos_Hori_Target AT %MD250 : REAL;
    Vel_Hori AT %MD251 : REAL;
    Pos_Hori_Actual AT %MD252 : REAL;

    (* Axis1 Index M590 / D530 *)
    Cmd_Idx_Power AT %MX590.0 : BOOL;
    Sts_Idx_PowerOk AT %MX592.0 : BOOL;
    Cmd_Idx_Home AT %MX600.0 : BOOL;
    Cmd_Idx_Move AT %MX602.0 : BOOL;
    Cmd_Idx_Stop AT %MX603.0 : BOOL;
    Sts_Idx_HomeDone AT %MX610.0 : BOOL;
    Sts_Idx_MoveDone AT %MX611.0 : BOOL;
    Sts_Idx_Homed AT %MX612.0 : BOOL;
    Sts_Idx_Moving AT %MX613.0 : BOOL;
    Sts_Idx_Alarm AT %MX614.0 : BOOL;
    Pos_Idx_Target AT %MD265 : REAL;
    Vel_Idx AT %MD266 : REAL;
    Pos_Idx_Actual AT %MD267 : REAL;

    (* Axis2 Lift M530 / D510 *)
    Cmd_Lift_Power AT %MX530.0 : BOOL;
    Sts_Lift_PowerOk AT %MX532.0 : BOOL;
    Cmd_Lift_Home AT %MX540.0 : BOOL;
    Cmd_Lift_Move AT %MX542.0 : BOOL;
    Cmd_Lift_Stop AT %MX543.0 : BOOL;
    Sts_Lift_HomeDone AT %MX550.0 : BOOL;
    Sts_Lift_MoveDone AT %MX551.0 : BOOL;
    Sts_Lift_Homed AT %MX552.0 : BOOL;
    Sts_Lift_Moving AT %MX553.0 : BOOL;
    Sts_Lift_Alarm AT %MX554.0 : BOOL;
    Pos_Lift_Target AT %MD255 : REAL;
    Vel_Lift AT %MD256 : REAL;
    Pos_Lift_Actual AT %MD257 : REAL;

    (* Axis3 Stir M560 / D520 *)
    Cmd_Stir_Power AT %MX560.0 : BOOL;
    Sts_Stir_PowerOk AT %MX562.0 : BOOL;
    Cmd_Stir_Home AT %MX570.0 : BOOL;
    Cmd_Stir_Move AT %MX572.0 : BOOL;
    Cmd_Stir_Stop AT %MX573.0 : BOOL;
    Sts_Stir_HomeDone AT %MX580.0 : BOOL;
    Sts_Stir_MoveDone AT %MX581.0 : BOOL;
    Sts_Stir_Homed AT %MX582.0 : BOOL;
    Sts_Stir_Moving AT %MX583.0 : BOOL;
    Sts_Stir_Alarm AT %MX584.0 : BOOL;
    Pos_Stir_Target AT %MD260 : REAL;
    Vel_Stir AT %MD261 : REAL;
    Pos_Stir_Actual AT %MD262 : REAL;

    (* Axis4 Powder M620 / D540 *)
    Cmd_Pwd_Power AT %MX620.0 : BOOL;
    Sts_Pwd_PowerOk AT %MX622.0 : BOOL;
    Cmd_Pwd_Home AT %MX630.0 : BOOL;
    Cmd_Pwd_Move AT %MX632.0 : BOOL;
    Cmd_Pwd_Stop AT %MX633.0 : BOOL;
    Sts_Pwd_HomeDone AT %MX640.0 : BOOL;
    Sts_Pwd_MoveDone AT %MX641.0 : BOOL;
    Sts_Pwd_Homed AT %MX642.0 : BOOL;
    Sts_Pwd_Moving AT %MX643.0 : BOOL;
    Sts_Pwd_Alarm AT %MX644.0 : BOOL;
    Pos_Pwd_Target AT %MD270 : REAL;
    Vel_Pwd AT %MD271 : REAL;
    Pos_Pwd_Actual AT %MD272 : REAL;

    (* 上位机 DO 命令位（仍在保持区地址上） *)
    Cmd_Vibration AT %MX650.0 : BOOL;
    Cmd_IonFan AT %MX651.0 : BOOL;
END_VAR

VAR_GLOBAL
    (* 物理 DO，非保持区 *)
    DO_Vibration AT %QX0.0 : BOOL;
    DO_IonFan AT %QX0.1 : BOOL;
END_VAR
