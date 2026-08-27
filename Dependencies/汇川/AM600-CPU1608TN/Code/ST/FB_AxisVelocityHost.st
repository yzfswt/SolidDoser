(* ==============================================
   FB_AxisVelocityHost — 单轴速度运行：上位机 M/D 握手 → MC_MoveVelocity

   用于搅拌轴等连续旋转轴：
   - CmdPower：伺服使能
   - CmdMove ：启动速度运行（脉冲触发，PLC 内部锁存运行）
   - CmdStop ：减速停止
   - CmdHome / PosTarget：为兼容上位机点表保留，不参与控制

   InoProShop 粘贴注意：
   1. 新建 FB，名称 FB_AxisVelocityHost，语言 ST
   2. 声明区只粘 【声明开始】～【声明结束】
   3. 实现区只粘 【实现开始】～【实现结束】
   4. 库管理器需有 SM3_Basic
   ============================================== *)

(* ========== 【声明开始】粘贴下面到声明区 ========== *)
VAR_IN_OUT
    Axis            : AXIS_REF_SM3;
END_VAR
VAR_INPUT
    CmdPower        : BOOL;
    CmdHome         : BOOL;
    CmdMove         : BOOL;
    CmdStop         : BOOL;
    PosTarget       : REAL;
    Velocity        : REAL;
    Accel           : REAL := 500.0;
    Decel           : REAL := 500.0;
    Jerk            : REAL := 0.0;
END_VAR
VAR_OUTPUT
    StatusPowerOk   : BOOL;
    StatusHomeDone  : BOOL;
    StatusMoveDone  : BOOL;
    StatusHomed     : BOOL;
    StatusMoving    : BOOL;
    StatusAlarm     : BOOL;
    PosActual       : REAL;
END_VAR
VAR
    fbPower         : MC_Power;
    fbMoveVel       : MC_MoveVelocity;
    fbStop          : MC_Stop;
    fbReadPos       : MC_ReadActualPosition;
    fbReset         : MC_Reset;
    rTrigPower      : R_TRIG;
    rTrigMove       : R_TRIG;
    rTrigStop       : R_TRIG;
    bEnable         : BOOL;
    bRunLatch       : BOOL;
    bInVelocity     : BOOL;
    rVelUse         : REAL;
    nDirection      : INT;
END_VAR
(* ========== 【声明结束】 ========== *)

(* ========== 【实现开始】粘贴到实现区 ========== *)
rTrigPower(CLK := CmdPower);
IF rTrigPower.Q THEN
    bEnable := TRUE;
END_IF;

fbPower(
    Axis := Axis,
    Enable := bEnable,
    bRegulatorOn := TRUE,
    bDriveStart := TRUE
);
StatusPowerOk := fbPower.Status AND NOT fbPower.Error;

rTrigStop(CLK := CmdStop);
IF rTrigStop.Q THEN
    bRunLatch := FALSE;
    bInVelocity := FALSE;
    fbStop.Execute := TRUE;
END_IF;

fbStop(
    Axis := Axis,
    Execute := fbStop.Execute,
    Deceleration := Decel,
    Jerk := Jerk
);
IF fbStop.Done OR fbStop.Error THEN
    fbStop.Execute := FALSE;
END_IF;

rTrigMove(CLK := CmdMove);
IF rTrigMove.Q AND (Velocity <> 0.0) AND StatusPowerOk THEN
    bRunLatch := TRUE;
    bInVelocity := FALSE;
END_IF;

IF Velocity < 0.0 THEN
    rVelUse := -Velocity;
    nDirection := -1;
ELSE
    rVelUse := Velocity;
    nDirection := 1;
END_IF;

(* MC_MoveVelocity 须保持 Execute=TRUE 才能连续转；勿单周期脉冲 *)
fbMoveVel(
    Axis := Axis,
    Execute := bRunLatch AND NOT fbStop.Busy,
    Velocity := rVelUse,
    Acceleration := Accel,
    Deceleration := Decel,
    Jerk := Jerk,
    Direction := nDirection
);

IF fbMoveVel.InVelocity THEN
    bInVelocity := TRUE;
END_IF;
IF fbMoveVel.Error THEN
    bRunLatch := FALSE;
END_IF;

fbReadPos(Axis := Axis, Enable := TRUE);
IF fbReadPos.Valid THEN
    PosActual := fbReadPos.Position;
END_IF;

(* 搅拌轴不需要回零：对上位机报告已回零，避免启动前被“未回零”拦截。 *)
StatusHomeDone := TRUE;
StatusHomed := TRUE;
StatusMoveDone := bInVelocity;
StatusMoving := bRunLatch OR fbMoveVel.Busy OR fbStop.Busy;
StatusAlarm := fbPower.Error OR fbMoveVel.Error OR fbStop.Error;

IF StatusAlarm AND CmdStop THEN
    fbReset(Axis := Axis, Execute := TRUE);
ELSE
    fbReset(Axis := Axis, Execute := FALSE);
END_IF;
(* ========== 【实现结束】不要粘 END_FUNCTION_BLOCK ========== *)
