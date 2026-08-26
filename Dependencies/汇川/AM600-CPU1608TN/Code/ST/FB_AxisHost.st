(* ==============================================
   FB_AxisHost  — 单轴：上位机 WORD 握手 → MC_* 运动

   使能：CmdPower 上升沿锁存 bEnable，MC_Power.Enable 保持
   回零：
     bUseControllerHoming=FALSE → MC_Home（伺服回原）
     bUseControllerHoming=TRUE  → 自写搜原点（承粉，无限位）
       1) 搜索方向走到原点 ON
       2) 反向慢速，直到原点 OFF（下降沿）
       3) 停止并 MC_SetPosition(0)
       ★ 不用 SMC_Homing：FAST_SLOW 要限位(51)，FAST_BSLOW 不反向
   定位：CmdMove 上升沿 → MC_MoveAbsolute
   停止：CmdStop 上升沿 → MC_Stop + MC_Reset

   ★ InoProShop：声明区 / 实现区分开粘贴；勿粘 FUNCTION_BLOCK 外壳
   ============================================== *)

(* ========== 【声明开始】 ========== *)
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
    bUseControllerHoming : BOOL := FALSE;
    bHomeSwitch     : BOOL := FALSE;
    (* TRUE：挡片挡住时 DI=TRUE *)
    bHomeSwitchActiveHigh : BOOL := TRUE;
    fHomeVelFast    : LREAL := 10.0;
    fHomeVelSlow    : LREAL := 2.0;
    fHomeAcc        : LREAL := 100.0;
    fHomeDec        : LREAL := 100.0;
    (* FALSE=负向搜索（承粉已验证） *)
    bHomeDirPositive : BOOL := FALSE;
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
    fbHomeVel       : MC_MoveVelocity;
    fbSetPos        : MC_SetPosition;
    fbMove          : MC_MoveAbsolute;
    fbStop          : MC_Stop;
    fbReadPos       : MC_ReadActualPosition;
    fbReset         : MC_Reset;
    rTrigPower      : R_TRIG;
    rTrigHomeGate   : R_TRIG;
    rTrigMove       : R_TRIG;
    rTrigStop       : R_TRIG;
    bEnable         : BOOL;
    bHomedLatch     : BOOL;
    bHomeGate       : BOOL;
    bHomePending    : BOOL;
    bHomeReset      : BOOL;
    bAlarmLatch     : BOOL;
    bStopReset      : BOOL;
    bHomeExec       : BOOL;
    bHomeDone       : BOOL;
    bHomeBusy       : BOOL;
    bHomeErr        : BOOL;
    bHomeOn         : BOOL;
    bHomeVelExec    : BOOL;
    bSetPosExec     : BOOL;
    nHomeStep       : INT;
    nHomeWait       : INT;
    nStopResetWait  : INT;
    nHomeVelDir     : INT;
    nSearchDir      : INT;
    nLeaveDir       : INT;
    rHomeVel        : REAL;
    bReadPosEn      : BOOL;
    bDoReset        : BOOL;
    rVelUse         : REAL;
END_VAR
(* ========== 【声明结束】 ========== *)

(* ========== 【实现开始】 ========== *)
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

IF bHomeSwitchActiveHigh THEN
    bHomeOn := bHomeSwitch;
ELSE
    bHomeOn := NOT bHomeSwitch;
END_IF;
IF bHomeDirPositive THEN
    nSearchDir := 1;
    nLeaveDir := -1;
ELSE
    nSearchDir := -1;
    nLeaveDir := 1;
END_IF;

rTrigStop(CLK := CmdStop);
IF rTrigStop.Q THEN
    bHomePending := FALSE;
    bHomeReset := FALSE;
    nHomeStep := 0;
    nHomeWait := 0;
    bHomeExec := FALSE;
    bHomeVelExec := FALSE;
    bSetPosExec := FALSE;
    fbMove.Execute := FALSE;
    fbStop.Execute := TRUE;
    bStopReset := TRUE;
    nStopResetWait := 0;
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

IF bStopReset THEN
    nStopResetWait := nStopResetWait + 1;
    IF nStopResetWait >= 10 THEN
        bStopReset := FALSE;
        nStopResetWait := 0;
        bAlarmLatch := FALSE;
    END_IF;
END_IF;

bHomeGate := CmdHome AND StatusPowerOk AND NOT bAlarmLatch;
rTrigHomeGate(CLK := bHomeGate);
IF rTrigHomeGate.Q THEN
    StatusHomeDone := FALSE;
    bHomeDone := FALSE;
    bHomeErr := FALSE;
    fbMove.Execute := FALSE;
    bHomeExec := FALSE;
    bHomeVelExec := FALSE;
    bSetPosExec := FALSE;
    bHomePending := TRUE;
    bHomeReset := TRUE;
    nHomeStep := 1;
    nHomeWait := 0;
END_IF;

IF bUseControllerHoming THEN
    (* 承粉：速度搜原点。10=正向搜索 12=反向找下降沿 13=停 14=置零 *)
    IF bHomePending THEN
        IF NOT CmdHome OR NOT StatusPowerOk OR bAlarmLatch THEN
            bHomePending := FALSE;
            bHomeReset := FALSE;
            nHomeStep := 0;
            bHomeVelExec := FALSE;
            bSetPosExec := FALSE;
        ELSE
            CASE nHomeStep OF
                1:
                    nHomeWait := nHomeWait + 1;
                    IF nHomeWait >= 8 THEN
                        bHomeReset := FALSE;
                        nHomeWait := 0;
                        IF fbMove.Busy OR fbHomeVel.Busy OR fbStop.Busy THEN
                            fbStop.Execute := TRUE;
                            nHomeStep := 2;
                        ELSE
                            nHomeStep := 10;
                        END_IF;
                    END_IF;
                2:
                    IF NOT fbStop.Execute AND NOT fbStop.Busy THEN
                        nHomeStep := 10;
                    END_IF;
                10: (* 已在原点上：直接反向找下降沿；否则快搜直到 ON *)
                    IF bHomeOn THEN
                        bHomeVelExec := FALSE;
                        nHomeWait := 0;
                        nHomeStep := 12;
                    ELSE
                        nHomeVelDir := nSearchDir;
                        rHomeVel := TO_REAL(fHomeVelFast);
                        bHomeVelExec := TRUE;
                    END_IF;
                12: (* 反向慢速，原点 OFF = 下降沿 *)
                    nHomeWait := nHomeWait + 1;
                    nHomeVelDir := nLeaveDir;
                    rHomeVel := TO_REAL(fHomeVelSlow);
                    bHomeVelExec := TRUE;
                    IF (nHomeWait >= 3) AND (NOT bHomeOn) THEN
                        bHomeVelExec := FALSE;
                        fbStop.Execute := TRUE;
                        nHomeStep := 13;
                    END_IF;
                13:
                    IF NOT fbStop.Execute AND NOT fbStop.Busy THEN
                        bSetPosExec := TRUE;
                        nHomeStep := 14;
                    END_IF;
                14:
                    IF fbSetPos.Done THEN
                        bSetPosExec := FALSE;
                        bHomeDone := TRUE;
                        bHomedLatch := TRUE;
                        bHomePending := FALSE;
                        nHomeStep := 0;
                    END_IF;
                    IF fbSetPos.Error THEN
                        bSetPosExec := FALSE;
                        bHomeErr := TRUE;
                        bAlarmLatch := TRUE;
                        bHomePending := FALSE;
                        nHomeStep := 0;
                    END_IF;
            END_CASE;
        END_IF;
    END_IF;

    fbHomeVel(
        Axis := Axis,
        Execute := bHomeVelExec,
        Velocity := rHomeVel,
        Acceleration := TO_REAL(fHomeAcc),
        Deceleration := TO_REAL(fHomeDec),
        Jerk := 0.0,
        Direction := nHomeVelDir
    );
    fbSetPos(
        Axis := Axis,
        Execute := bSetPosExec,
        Position := 0.0
    );
    bHomeBusy := bHomePending OR fbHomeVel.Busy OR fbSetPos.Busy;
    IF fbHomeVel.Error THEN
        bHomeErr := TRUE;
        bAlarmLatch := TRUE;
        bHomeVelExec := FALSE;
        bHomePending := FALSE;
        nHomeStep := 0;
    END_IF;
ELSE
    IF bHomePending THEN
        IF NOT CmdHome OR NOT StatusPowerOk OR bAlarmLatch THEN
            bHomePending := FALSE;
            bHomeReset := FALSE;
            nHomeStep := 0;
            bHomeExec := FALSE;
        ELSE
            CASE nHomeStep OF
                1:
                    nHomeWait := nHomeWait + 1;
                    IF nHomeWait >= 8 THEN
                        bHomeReset := FALSE;
                        nHomeWait := 0;
                        IF fbMove.Busy OR fbHome.Busy OR fbStop.Busy THEN
                            fbStop.Execute := TRUE;
                            nHomeStep := 2;
                        ELSE
                            nHomeStep := 3;
                        END_IF;
                    END_IF;
                2:
                    IF NOT fbStop.Execute AND NOT fbStop.Busy THEN
                        nHomeWait := 0;
                        nHomeStep := 3;
                    END_IF;
                3:
                    nHomeWait := nHomeWait + 1;
                    IF nHomeWait >= 8 THEN
                        bHomeExec := TRUE;
                        bHomePending := FALSE;
                        nHomeStep := 0;
                    END_IF;
            END_CASE;
        END_IF;
    END_IF;
    fbHome(
        Axis := Axis,
        Execute := bHomeExec,
        Position := 0.0
    );
    bHomeDone := fbHome.Done;
    bHomeBusy := fbHome.Busy;
    bHomeErr := fbHome.Error;
END_IF;

IF bHomeDone AND NOT bUseControllerHoming THEN
    StatusHomeDone := TRUE;
    bHomedLatch := TRUE;
    bHomeExec := FALSE;
END_IF;
IF bHomeDone AND bUseControllerHoming THEN
    StatusHomeDone := TRUE;
END_IF;
IF bHomeErr AND NOT bUseControllerHoming THEN
    StatusHomeDone := FALSE;
    bHomeExec := FALSE;
    bHomePending := FALSE;
    bHomeReset := FALSE;
    nHomeStep := 0;
    nHomeWait := 0;
    bAlarmLatch := TRUE;
END_IF;
IF NOT CmdHome THEN
    StatusHomeDone := FALSE;
    IF NOT bHomeBusy THEN
        bHomeExec := FALSE;
        bHomeVelExec := FALSE;
        bSetPosExec := FALSE;
    END_IF;
END_IF;

StatusHomed := bHomedLatch;

rTrigMove(CLK := CmdMove);
rVelUse := SEL(Velocity > 0.0, Velocity, 10.0);
IF rTrigMove.Q AND StatusPowerOk AND NOT bAlarmLatch THEN
    StatusMoveDone := FALSE;
    bHomePending := FALSE;
    bHomeReset := FALSE;
    nHomeStep := 0;
    nHomeWait := 0;
    bHomeExec := FALSE;
    bHomeVelExec := FALSE;
    bSetPosExec := FALSE;
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

IF fbMove.Done THEN
    StatusMoveDone := TRUE;
    fbMove.Execute := FALSE;
END_IF;
IF fbMove.Error THEN
    StatusMoveDone := FALSE;
    fbMove.Execute := FALSE;
    bAlarmLatch := TRUE;
END_IF;
IF NOT CmdMove THEN
    StatusMoveDone := FALSE;
    IF NOT fbMove.Busy THEN
        fbMove.Execute := FALSE;
    END_IF;
END_IF;

bReadPosEn := NOT bHomeBusy AND NOT fbMove.Busy AND NOT fbStop.Busy AND NOT bHomePending;
fbReadPos(Axis := Axis, Enable := bReadPosEn);
IF fbReadPos.Valid THEN
    PosActual := TO_REAL(fbReadPos.Position);
END_IF;

StatusMoving := bHomeBusy OR fbMove.Busy OR fbStop.Busy OR bHomePending;
IF fbPower.Error OR bHomeErr OR fbMove.Error OR fbStop.Error THEN
    bAlarmLatch := TRUE;
END_IF;
StatusAlarm := bAlarmLatch;

bDoReset := bStopReset OR bHomeReset OR (StatusAlarm AND CmdStop);
fbReset(Axis := Axis, Execute := bDoReset);
(* ========== 【实现结束】 ========== *)
