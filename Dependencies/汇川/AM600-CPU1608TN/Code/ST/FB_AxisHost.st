(* ==============================================
   FB_AxisHost  — 单轴：上位机 M/D 握手 → MC_* 运动

   ★ InoProShop 粘贴注意（这条最容易导致连锁错误）★
   1. 新建 FB，名称 FB_AxisHost，语言 ST
   2. 切到「声明」页，只粘贴 【声明开始】到 【声明结束】之间
      —— 不要粘 FUNCTION_BLOCK / END_FUNCTION_BLOCK
   3. 切到「实现」页，只粘贴 【实现开始】到 【实现结束】之间
   4. 双击 Application 下「库管理器」→ 添加库 → SM3_Basic
      （树里点一下没用，必须双击打开，再点添加库）
   5. SoftMotion3 轴类型必须用 AXIS_REF_SM3（不是 AXIS_REF）
      DS402 真实轴 AXIS_REF_ETC_DS402_CS 可传入该 IN_OUT
   6. SM3 的 MC_Home 仅有 Axis/Execute/Position；回零模式与速度
      在驱动器/轴参数里配置，不要在 FB 里传 HomingMode/Velocity
   ============================================== *)

(* ========== 【声明开始】粘贴下面到实现页上面的声明区 ========== *)
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
    fbHome          : MC_Home;
    fbMove          : MC_MoveAbsolute;
    fbStop          : MC_Stop;
    fbReadPos       : MC_ReadActualPosition;
    fbReset         : MC_Reset;
    rTrigPower      : R_TRIG;
    rTrigHome       : R_TRIG;
    rTrigMove       : R_TRIG;
    rTrigStop       : R_TRIG;
    bEnable         : BOOL;
    bHomedLatch     : BOOL;
    rVelUse         : REAL;
END_VAR
(* ========== 【声明结束】 ========== *)

(* ========== 【实现开始】粘贴到实现页 ========== *)
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
    fbHome.Execute := FALSE;
    fbMove.Execute := FALSE;
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

rTrigHome(CLK := CmdHome);
IF rTrigHome.Q THEN
    StatusHomeDone := FALSE;
    fbMove.Execute := FALSE;
    fbHome.Execute := TRUE;
END_IF;

(* SM3 MC_Home：回零由驱动器执行，此处只给完成时的绝对位置 *)
fbHome(
    Axis := Axis,
    Execute := fbHome.Execute,
    Position := 0.0
);

IF CmdHome THEN
    IF fbHome.Done THEN
        StatusHomeDone := TRUE;
        bHomedLatch := TRUE;
        fbHome.Execute := FALSE;
    END_IF;
    IF fbHome.Error THEN
        StatusHomeDone := FALSE;
        fbHome.Execute := FALSE;
    END_IF;
ELSE
    StatusHomeDone := FALSE;
    IF NOT fbHome.Busy THEN
        fbHome.Execute := FALSE;
    END_IF;
END_IF;

StatusHomed := bHomedLatch;

rTrigMove(CLK := CmdMove);
rVelUse := SEL(Velocity > 0.0, Velocity, 10.0);
IF rTrigMove.Q THEN
    StatusMoveDone := FALSE;
    fbHome.Execute := FALSE;
    fbMove.Execute := TRUE;
END_IF;

fbMove(
    Axis := Axis,
    Execute := fbMove.Execute,
    Position := PosTarget,
    Velocity := rVelUse,
    Acceleration := Accel,
    Deceleration := Decel,
    Jerk := Jerk,
    Direction := 0
);

IF CmdMove THEN
    IF fbMove.Done THEN
        StatusMoveDone := TRUE;
        fbMove.Execute := FALSE;
    END_IF;
    IF fbMove.Error THEN
        StatusMoveDone := FALSE;
        fbMove.Execute := FALSE;
    END_IF;
ELSE
    StatusMoveDone := FALSE;
    IF NOT fbMove.Busy THEN
        fbMove.Execute := FALSE;
    END_IF;
END_IF;

fbReadPos(Axis := Axis, Enable := TRUE);
IF fbReadPos.Valid THEN
    PosActual := fbReadPos.Position;
END_IF;

StatusMoving := fbHome.Busy OR fbMove.Busy OR fbStop.Busy;
StatusAlarm := fbPower.Error OR fbHome.Error OR fbMove.Error OR fbStop.Error;

IF StatusAlarm AND CmdStop THEN
    fbReset(Axis := Axis, Execute := TRUE);
ELSE
    fbReset(Axis := Axis, Execute := FALSE);
END_IF;
(* ========== 【实现结束】不要粘 END_FUNCTION_BLOCK ========== *)
