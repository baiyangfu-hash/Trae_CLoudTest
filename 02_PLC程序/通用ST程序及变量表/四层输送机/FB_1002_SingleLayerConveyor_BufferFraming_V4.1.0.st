(* ================================================================= *)
(*  功能块名称：FB_1002_SingleLayerConveyor_BufferFraming            *)
(*  功能描述：单层输送机纯逻辑控制功能块（9步自动状态机）         *)
(*  创建日期：2026-04-23                                            *)
(*  规范化修订：2026-04-25                                           *)
(*  版本号：V4.1.0                                                  *)
(*  基于版本：V4.0.1 (原名: FB_单层输送机_V4.0.1)                   *)
(*  编制人：[待填写]                                                *)
(*  审核人：[待填写]                                                *)
(*                                                                  *)
(*  遵循规范：                                                      *)
(*    - 801_PLC变量命名与功能块命名规范_DEV-V1.0.5                  *)
(*    - 810_PLC编程规范_DEV-V1.0.3                                  *)
(*    - IEC 61131-3 标准                                            *)
(*                                                                  *)
(*  架构特点：                                                      *)
(*    - 纯逻辑块: 不包含任何X/Y/M/D地址引用                         *)
(*    - 数据解耦: 通过逻辑变量接口与主控交互                          *)
(*    - 单层设计: 无ARRAY,所有信号均为单个BOOL/INT/REAL              *)
(*    - 故障安全: 内置超时保护和传感器冲突检测                        *)
(*    - 下游联动: 支持上游允许放料信号和下游放料完成信号交互          *)
(*                                                                  *)
(*  变更记录：                                                        *)
(* ---------------------------------------------------------------- *)
(*  V4.1.0 (2026-04-25) Trae                                       *)
(*  - 修正: FB名称标准化为FB_1002_SingleLayerConveyor_BufferFraming   *)
(*  - 修正: 文件头标准化为(* *)格式                                *)
(*  - 修正: 更新遵循规范至801 V1.0.5 / 810 V1.0.3                  *)
(*  - 优化: 统一注释风格(段落分隔符改为标准格式)                    *)
(* ---------------------------------------------------------------- *)
(*  V4.0.1 (2026-04-25) 初始版本                                    *)
(*  - 修正计时器使用方式 - 严格按三菱GX Works3标准                  *)
(* ================================================================= *)

FUNCTION_BLOCK FB_1002_SingleLayerConveyor_BufferFraming
//#region 系统控制信号
VAR_INPUT 
    (* ==================== 一、系统控制信号 ==================== *)
    (* 来自主控/HMI M区 - 遵循801规范: i_前缀                        *)
    i_bEnable            : BOOL;    (* 总使能信号(主控系统就绪后置位) *)

    (* ------------------- 模式选择 (互斥信号,来自HMI M区) ------------ *)
    i_bAutoMode          : BOOL;    (* 自动运行模式选择 *)
    i_bManualMode        : BOOL;    (* 手动调试模式选择 *)

    (* ------------------- 操作按钮 (来自HMI,边沿触发) ---------------- *)
    i_bStart             : BOOL;    (* 自动循环启动按钮 *)
    i_bStop              : BOOL;    (* 自动循环停止按钮 *)
    i_bReset             : BOOL;    (* 故障复位/初始化按钮 *)

    (* ==================== 二、手动操作信号 ==================== *)
    (* 6个BOOL,来自HMI - 遵循801规范: i_bLx_前缀(HMI辅助)           *)
    i_bLx_BlockDown      : BOOL;    (* 手动-阻挡气缸下降 *)
    i_bLx_BlockUp        : BOOL;    (* 手动-阻挡气缸上升 *)
    i_bLx_SeparatePush   : BOOL;    (* 手动-分料气缸推出 *)
    i_bLx_SeparateReset  : BOOL;    (* 手动-分料气缸复位 *)
    i_bLx_ConveyorFwd    : BOOL;    (* 手动-输送带正转 *)
    i_bLx_ConveyorRev    : BOOL;    (* 手动-输送带反转 *)

    (* ==================== 三、工艺参数 ==================== *)
    (* 来自HMI设定或配方                                              *)
    i_rConveyorSpeed     : REAL;    (* 输送带速度设定(Hz或m/min,给变频器用) *)
    i_iSeparateTime      : INT;     (* 分料动作保持时间(ms) *)
    i_iBlockWaitTime     : INT;     (* 阻挡气缸动作等待时间(ms) *)

    (* ==================== 四、传感器输入 ==================== *)
    (* 7个BOOL,全部来自主控映射                                      *)
    (* 放料完成感应器通过下游信号o_bFeedComplete反馈                   *)
    (* --- 分料前感应器: 检测材料是否到达分料工位入口 --- *)
    i_bPreSeparateSensor : BOOL;

    (* --- 到位感应器1/2: 双传感器冗余检测材料到位 --- *)
    i_bPositionSensor1   : BOOL;
    i_bPositionSensor2   : BOOL;

    (* --- 阻挡气缸位置反馈 --- *)
    i_bBlockCylinderUp   : BOOL;    (* 阻挡升起(释放)位置 *)
    i_bBlockCylinderDown : BOOL;    (* 阻挡下降(阻挡)位置 *)

    (* --- 分料气缸位置反馈 --- *)
    i_bSeparateCylinderUp   : BOOL; (* 分料收回位置 *)
    i_bSeparateCylinderDown : BOOL; (* 分料推出位置 *)

    (* ==================== 五、上下游联锁信号 ==================== *)
    i_bUpstreamAllowFeed : BOOL;    (* 取放料机构已取走,允许继续放料 *)
END_VAR
//#endregion 系统控制信号S



VAR_OUTPUT
    (* ==================== 一、执行器请求输出 ==================== *)
    (* 5个BOOL,全部给主控,由主控映射到Y地址                           *)
    o_bBlockSolenoid     : BOOL;    (* TRUE=下降(阻挡), FALSE=上升(释放) *)
    o_bSeparateSolenoid  : BOOL;    (* TRUE=推出(分料), FALSE=复位 *)
    o_bConveyorFwd       : BOOL;    (* 输送带正向运转 *)
    o_bConveyorSlow      : BOOL;    (* 输送带慢速运转(精确定位用) *)
    o_bConveyorRev       : BOOL;    (* 输送带反向运转(退料用) *)

    (* ==================== 二、下游信号输出 ==================== *)
    (* 给取放料机构/打胶机                                             *)
    o_bFeedComplete      : BOOL;    (* 该层放料完成,可取料 *)

    (* ==================== 三、状态/HMI显示输出 =================== *)
    o_bRunning           : BOOL;    (* 正在自动运行 *)
    o_bFault             : BOOL;    (* 本站有故障(报警激活) *)
    o_iCurrentState      : INT;     (* 当前状态码(0=空闲,1-8=步序,99=故障) *)

    (* ==================== 四、报警输出 ==================== *)
    (* 给公共报警管理器                                                 *)
    o_iAlarmCode         : INT;     (* 当前有效报警代码(0=无报警,1-7=报警类型) *)
                                    (* 1=阻挡下降超时,2=上升超时,                *)
                                    (* 3=分料推出超时,4=复位超时,                *)
                                    (* 5=输送超时,6=传感器冲突,7=变频器故障        *)
END_VAR


(* ==================== 内部变量定义 ==================== *)
(* 遵循801规范: 不加前缀,直接 类型_描述                               *)
VAR
    (* -------------------- 一、状态机变量 ------------------------- *)
    iStep                : INT;     (* 当前步序 (0-8) *)

    (* 运行标志 *)
    bRunning             : BOOL;    (* 正在自动运行标志 *)
    bFault               : BOOL;    (* 故障标志 *)

    (* 启动触发锁存 (防止重复触发) *)
    bStartTriggered       : BOOL;    (* 启动信号锁存 *)

    (* ================= 二、计时器相关变量 =============== *)
    (* 采用"TON实例+独立接口变量"模式 (兼容三菱GX Works3风格)       *)
    (* 命名规则: tXxx=实例, i_bTime_xxx=输入, q_bTq_xxx=输出          *)
    (*           符合801规范§4.3.3 V1.0.5的扩展命名规则                 *)

    (* TON计时器实例 (在VAR区声明) *)
    tTimerAction         : TON;     (* 动作等待定时器(阻挡/分料) *)
    tTimerConveyor       : TON;     (* 输送超时定时器 *)
    tTimerReset          : TON;     (* 复位等待定时器 *)
    tTimerPulse          : TON;     (* 放料完成脉冲定时器(500ms) *)
    tTimerInit           : TON;     (* 初始化总超时定时器 *)

    (* 启动输入: 写入TRUE=启动, 写入FALSE=停止 *)
    i_bTime_Action       : BOOL;    (* 动作定时器启动 *)
    i_bTime_Conveyor     : BOOL;    (* 输送定时器启动 *)
    i_bTime_Reset        : BOOL;    (* 复位定时器启动 *)
    i_bTime_Pulse        : BOOL;    (* 脉冲定时器启动 *)
    i_bTime_Init         : BOOL;    (* 初始化定时器启动 *)

    (* 到时输出: 读取判断是否到时 *)
    q_bTq_Action         : BOOL;    (* 动作定时器到时 *)
    q_bTq_Conveyor       : BOOL;    (* 输送定时器到时 *)
    q_bTq_Reset          : BOOL;    (* 复位定时器到时 *)
    q_bTq_Pulse          : BOOL;    (* 脉冲定时器到时 *)
    q_bTq_Init           : BOOL;    (* 初始化定时器到时 *)

    (* 复位信号: 强制清零当前值 *)
    i_bTrst_Action       : BOOL;    (* 动作定时器复位 *)
    i_bTrst_Conveyor     : BOOL;    (* 输送定时器复位 *)

    (* 预设值/当前值: 可选,用于调试显示 *)
    i_pTimer_Action      : INT;     (* 动作定时器预设值(ms) *)
    i_pTimer_Conveyor    : INT;     (* 输送定时器预设值(ms) *)
    q_eTimer_Action      : INT;     (* 动作定时器当前值(ms) *)
    q_eTimer_Conveyor    : INT;     (* 输送定时器当前值(ms) *)

    (* ================= 三、系统级内部变量 =============== *)
    bInitComplete        : BOOL;    (* 上电初始化完成标志 *)
    bInitInProgress      : BOOL;    (* 正在执行初始化 *)

    (* 报警相关 *)
    iActiveAlarm         : INT;     (* 当前活跃报警代码 *)

    (* 传感器冲突检测 *)
    bBlockConflict       : BOOL;    (* 阻挡上下位同时为TRUE *)
    bSeparateConflict    : BOOL;    (* 分料上下位同时为TRUE *)

    (* 手动操作互锁 *)
    bManualAllow         : BOOL;    (* 允许手动操作标志 *)
END_VAR


(* ==================== 常量定义 ==================== *)
(* 状态机步序 + 报警码 + 定时参数                                        *)
VAR CONSTANT
    (* ---------- 状态机步序常量 (9步: 0空闲 + 8工作步) --------- *)
    STP_IDLE             : INT := 0;   (* 空闲待机 *)
    STP_DETECT_MATERIAL  : INT := 1;   (* 等待分料前感应器信号 *)
    STP_BLOCK_DOWN       : INT := 2;   (* 阻挡气缸下降到位 *)
    STP_CONVEYOR_FWD     : INT := 3;   (* 输送带正转运料 *)
    STP_POSITION_CHECK   : INT := 4;   (* 等待双传感器到位确认 *)
    STP_BLOCK_UP         : INT := 5;   (* 阻挡气缸上升释放 *)
    STP_SEPARATE_ACTION  : INT := 6;   (* 分料气缸推出分离 *)
    STP_SLOW_FEED        : INT := 7;   (* 慢速精确送出 *)
    STP_FEED_COMPLETE    : INT := 8;   (* 放料完成,等待取料 *)

    (* ---------- 报警码常量 (1~7段,0=无报警) ---------------- *)
    ALM_BLOCK_DOWN_TIMEOUT   : INT := 1;
    ALM_BLOCK_UP_TIMEOUT    : INT := 2;
    ALM_SEPARATE_PUSH_TIMEOUT : INT := 3;
    ALM_SEPARATE_RESET_TIMEOUT : INT := 4;
    ALM_CONVEYOR_TIMEOUT    : INT := 5;
    ALM_SENSOR_CONFLICT     : INT := 6;
    ALM_INVERTER_FAULT      : INT := 7;

    (* ---------- 默认定时参数 (单位: ms,可通过输入参数覆盖) ---- *)
    T_DEF_BLOCK_ACTION_TIME     : INT := 800;    (* 阻挡气缸动作时间 *)
    T_DEF_SEPARATE_ACTION_TIME  : INT := 1000;   (* 分料气缸动作时间 *)
    T_DEF_CONVEYOR_TIMEOUT_TIME : INT := 5000;   (* 输送带超时保护 *)
    T_DEF_POSITION_STABLE_TIME  : INT := 500;    (* 到位后稳定等待 *)
    T_DEF_SLOW_FEED_TIME        : INT := 2000;   (* 慢速送出时间 *)
    T_DEF_RESET_WAIT_TIME       : INT := 500;    (* 复位等待时间 *)
    T_DEF_INIT_TIMEOUT          : INT := 10000;  (* 初始化总超时(10s) *)
    T_DEF_FEED_PULSE_TIME       : INT := 500;    (* 放料完成脉冲宽度(ms) *)
END_VAR


(* *************************************************************************)
(*                        主程序执行顺序说明                             *)
(*                                                                       *)
(*   第一部分: 使能与初始化处理                                         *)
(*   第二部分: 传感器冲突检测                                           *)
(*   第三部分: 模式分发 (自动/手动)                                     *)
(*   第四部分: 停止与复位处理                                           *)
(*   第五部分: TON统一实例化 (模仿TIMER_100_FB_M_x调用)                 *)
(*   第六部分: 状态机逻辑 (只操作q_bTq_xxx接口,不直接调用TON)           *)
(*   第七部分: 状态输出汇总                                           *)
(* *************************************************************************)


(* ==================== 第一部分: 使能与初始化处理 ========== *)

(* 使能失效时的安全处理 *)
IF NOT i_bEnable THEN
    (* 清零所有输出 *)
    o_bBlockSolenoid    := FALSE;
    o_bSeparateSolenoid := FALSE;
    o_bConveyorFwd      := FALSE;
    o_bConveyorSlow     := FALSE;
    o_bConveyorRev      := FALSE;
    o_bFeedComplete     := FALSE;

    (* 清零状态 *)
    iStep               := STP_IDLE;
    bRunning            := FALSE;
    bFault              := FALSE;
    bStartTriggered     := FALSE;
    iActiveAlarm        := 0;
    bInitComplete       := FALSE;
    bInitInProgress     := FALSE;

    (* 清零输出状态 *)
    o_bRunning          := FALSE;
    o_bFault            := FALSE;
    o_iCurrentState     := STP_IDLE;
    o_iAlarmCode        := 0;

    (* 停止所有计时器 *)
    i_bTime_Action   := FALSE;
    i_bTime_Conveyor := FALSE;
    i_bTime_Reset    := FALSE;
    i_bTime_Pulse    := FALSE;
    i_bTime_Init     := FALSE;

    RETURN;  (* 退出功能块,不执行后续逻辑 *)
END_IF;


(* ==================== 第二部分: 初始化流程 ================= *)
(* 上电或复位后首次使能时执行                                          *)

IF NOT bInitComplete THEN
    bInitInProgress := TRUE;

    (* 启动初始化计时器 *)
    i_bTime_Init := TRUE;

    (* 执行初始化: 气缸回到安全位置 *)
    o_bBlockSolenoid    := FALSE;  (* 阻挡电磁阀OFF -> 阻挡上升到上位 *)
    o_bSeparateSolenoid := FALSE;  (* 分料电磁阀OFF -> 分料气缸复位到上位 *)
    o_bConveyorFwd      := FALSE;  (* 输送带全部停止 *)
    o_bConveyorSlow     := FALSE;
    o_bConveyorRev      := FALSE;
    iStep               := STP_IDLE;
    bFault              := FALSE;
    iActiveAlarm        := 0;

    (* 检查初始化条件: 阻挡在上位 AND 分料在上位 OR 超时强制完成 *)
    IF (i_bBlockCylinderUp AND i_bSeparateCylinderUp) OR q_bTq_Init THEN
        bInitComplete   := TRUE;
        bInitInProgress := FALSE;
        i_bTime_Init := FALSE;  (* 停止初始化计时器 *)
    END_IF;

    (* 初始化期间不执行自动/手动逻辑 *)
    o_bRunning      := FALSE;
    o_iCurrentState := STP_IDLE;
    RETURN;
END_IF;


(* ==================== 第三部分: 传感器冲突检测 ============== *)
(* 所有模式共用                                                          *)

(* 阻挡气缸上下位同时为TRUE -> 传感器故障或接线错误 *)
bBlockConflict := i_bBlockCylinderUp AND i_bBlockCylinderDown;

(* 分料气缸上下位同时为TRUE -> 传感器故障或接线错误 *)
bSeparateConflict := i_bSeparateCylinderUp AND i_bSeparateCylinderDown;

(* 记录传感器冲突报警 *)
IF bBlockConflict OR bSeparateConflict THEN
    iActiveAlarm := ALM_SENSOR_CONFLICT;
    bFault      := TRUE;
ELSIF iActiveAlarm = ALM_SENSOR_CONFLICT THEN
    (* 冲突消失且当前只有此报警 -> 清除 *)
    iActiveAlarm := 0;
    bFault      := FALSE;
END_IF;


(* ==================== 第四部分: 模式分发 (自动/手动) ============ *)

IF i_bAutoMode THEN
    (* ===== 自动模式: 执行9步状态机 ===== *)
    CALL_AutoModeStateMachine();

ELSIF i_bManualMode THEN
    (* ===== 手动模式: 执行手动点动控制 ===== *)
    CALL_ManualModeControl();

ELSE
    (* 无效模式: 停止所有输出 *)
    o_bBlockSolenoid    := FALSE;
    o_bSeparateSolenoid := FALSE;
    o_bConveyorFwd      := FALSE;
    o_bConveyorSlow     := FALSE;
    o_bConveyorRev      := FALSE;
    o_bFeedComplete     := FALSE;

    IF NOT bFault THEN
        iStep := STP_IDLE;
    END_IF;
    bRunning := FALSE;

    (* 无效模式下也停止所有计时器 *)
    i_bTime_Action   := FALSE;
    i_bTime_Conveyor := FALSE;
    i_bTime_Reset    := FALSE;
    i_bTime_Pulse    := FALSE;
END_IF;


(* ==================== 第五部分: 停止与复位处理 ================ *)

(* 全局停止: 停止自动循环 *)
IF i_bStop THEN
    IF bRunning AND NOT bFault THEN
        iStep           := STP_IDLE;
        bRunning        := FALSE;
        bStartTriggered := FALSE;

        (* 停止该层输出 *)
        o_bBlockSolenoid    := FALSE;
        o_bSeparateSolenoid := FALSE;
        o_bConveyorFwd      := FALSE;
        o_bConveyorSlow     := FALSE;
        o_bConveyorRev      := FALSE;

        (* 停止所有计时器 *)
        i_bTime_Action   := FALSE;
        i_bTime_Conveyor := FALSE;
        i_bTime_Reset    := FALSE;
        i_bTime_Pulse    := FALSE;
    END_IF;
END_IF;

(* 全局复位: 清除所有报警和故障 *)
IF i_bReset THEN
    IF bFault THEN
        (* 清除报警和故障标志 *)
        iActiveAlarm := 0;
        bFault      := FALSE;

        (* 归零步序 *)
        iStep           := STP_IDLE;
        bRunning        := FALSE;
        bStartTriggered := FALSE;

        (* 安全输出状态 *)
        o_bBlockSolenoid    := FALSE;
        o_bSeparateSolenoid := FALSE;
        o_bConveyorFwd      := FALSE;
        o_bConveyorSlow     := FALSE;
        o_bConveyorRev      := FALSE;
        o_bFeedComplete     := FALSE;

        (* 停止所有计时器 *)
        i_bTime_Action   := FALSE;
        i_bTime_Conveyor := FALSE;
        i_bTime_Reset    := FALSE;
        i_bTime_Pulse    := FALSE;

        (* 要求重新初始化 *)
        bInitComplete := FALSE;
    END_IF;
END_IF;


(* ============ 第五部分(续): TON统一实例化 ===================== *)
(* 严格模仿三菱TIMER_100_FB_M_x模式                                   *)
(* 此处统一调用所有TON实例(类似程序开头的TIMER调用)                     *)
(* 使用i_bTime_xxx控制IN, 将.Q映射到q_bTq_xxx                       *)

(* --- TON_1: 动作定时器 (阻挡/分料动作等待) --- *)
tTimerAction(
    IN  := i_bTime_Action,
    PT  := T#MS * (
            IF iStep = STP_BLOCK_DOWN AND i_iBlockWaitTime > 0
                THEN i_iBlockWaitTime
            ELSIF iStep = STP_SEPARATE_ACTION AND i_iSeparateTime > 0
                THEN i_iSeparateTime
            ELSIF iStep = STP_POSITION_CHECK
                THEN T_DEF_POSITION_STABLE_TIME
            ELSE
                T_DEF_BLOCK_ACTION_TIME
            END
        )
);

(* --- TON_2: 输送定时器 (输送超时保护) --- *)
tTimerConveyor(
    IN  := i_bTime_Conveyor,
    PT  := T#MS * (
            IF iStep = STP_SLOW_FEED
                THEN T_DEF_SLOW_FEED_TIME
            ELSE
                T_DEF_CONVEYOR_TIMEOUT_TIME
            END
        )
);

(* --- TON_3: 复位定时器 (暂未使用,预留) --- *)
tTimerReset(
    IN  := i_bTime_Reset,
    PT  := T#MS * T_DEF_RESET_WAIT_TIME
);

(* --- TON_4: 放料完成脉冲定时器 (500ms脉冲) --- *)
tTimerPulse(
    IN  := i_bTime_Pulse,
    PT  := T#MS * T_DEF_FEED_PULSE_TIME
);

(* --- TON_5: 初始化定时器 (10s总超时) --- *)
tTimerInit(
    IN  := i_bTime_Init,
    PT  := T#MS * T_DEF_INIT_TIMEOUT
);

(* 映射输出接口 (将TON的.Q/.ET映射到标准接口变量) *)

(* 到时输出: .Q -> q_bTq_xxx *)
q_bTq_Action     := tTimerAction.Q;
q_bTq_Conveyor   := tTimerConveyor.Q;
q_bTq_Reset      := tTimerReset.Q;
q_bTq_Pulse      := tTimerPulse.Q;
q_bTq_Init       := tTimerInit.Q;

(* 当前值: .ET -> q_eTimer_xxx (转换为ms) *)
q_eTimer_Action   := UINT_TO_INT(TIME_TO_UINT(tTimerAction.ET)) / 10;
q_eTimer_Conveyor := UINT_TO_INT(TIME_TO_UINT(tTimerConveyor.ET)) / 10;

(* 预设值记录: PT -> i_pTimer_xxx (用于调试显示) *)
i_pTimer_Action   := UINT_TO_INT(TIME_TO_UINT(tTimerAction.PT)) / 10;
i_pTimer_Conveyor := UINT_TO_INT(TIME_TO_UINT(tTimerConveyor.PT)) / 10;


(* ==================== 第六部分: 状态机逻辑 ==================== *)
(* 只操作q_bTq_xxx接口,不直接调用TON                                    *)
(* 类似原始程序的CASE Step_S OF ... END_CASE部分                        *)

(* 9步状态机主体 (仅使用q_bTq_xxx判断到时) *)
CASE iStep OF

(* ================================================================= *)
(* 步骤0: 空闲待机                                                       *)
(* 条件: 启动触发 + 分料前有材料 + 上游允许放料                         *)
(* ================================================================= *)
STP_IDLE:
    bRunning := FALSE;

    (* 安全输出状态 *)
    o_bBlockSolenoid    := FALSE;
    o_bSeparateSolenoid := FALSE;
    o_bConveyorFwd      := FALSE;
    o_bConveyorSlow     := FALSE;
    o_bConveyorRev      := FALSE;
    o_bFeedComplete     := FALSE;

    (* 停止所有计时器 *)
    i_bTime_Action   := FALSE;
    i_bTime_Conveyor := FALSE;
    i_bTime_Pulse    := FALSE;

    (* 启动条件: 收到启动触发 + 分料前有材料到位 + 上游允许放料 *)
    IF bStartTriggered AND i_bPreSeparateSensor AND i_bUpstreamAllowFeed THEN
        iStep    := STP_DETECT_MATERIAL;
        bRunning := TRUE;
        i_bTime_Conveyor := TRUE;  (* 启动输送计时器 *)
    END_IF;

(* ================================================================= *)
(* 步骤1: 检测材料到位 (双重确认)                                      *)
(* 转出条件: 分料前感应器稳定信号                                      *)
(* 超时条件: 材料未到达 -> ALM_CONVEYOR_TIMEOUT                           *)
(* ================================================================= *)
STP_DETECT_MATERIAL:
    IF i_bPreSeparateSensor THEN
        (* 材料确认到位,进入阻挡下降 *)
        iStep := STP_BLOCK_DOWN;
        i_bTime_Conveyor := FALSE;  (* 停止输送计时器 *)
        i_bTime_Action := TRUE;     (* 启动动作计时器 *)
    ELSIF q_bTq_Conveyor THEN
        (* 超时: 材料未到达 *)
        iActiveAlarm := ALM_CONVEYOR_TIMEOUT;
        bFault       := TRUE;
        iStep        := STP_IDLE;
        bRunning     := FALSE;
        i_bTime_Conveyor := FALSE;
    END_IF;

(* ================================================================= *)
(* 步骤2: 阻挡下降 (等待气缸下位信号或超时)                            *)
(* 动作: 保持o_bBlockSolenoid=TRUE                                    *)
(* 转出条件: i_bBlockCylinderDown                                     *)
(* 超时条件: ALM_BLOCK_DOWN_TIMEOUT                                    *)
(* ================================================================= *)
STP_BLOCK_DOWN:
    o_bBlockSolenoid := TRUE;  (* 保持下降 *)

    IF i_bBlockCylinderDown THEN
        (* 阻挡到位,转入输送 *)
        iStep := STP_CONVEYOR_FWD;
        o_bConveyorFwd := TRUE;
        i_bTime_Action := FALSE;
        i_bTime_Conveyor := TRUE;
    ELSIF q_bTq_Action THEN
        (* 超时: 阻挡未到位 *)
        iActiveAlarm := ALM_BLOCK_DOWN_TIMEOUT;
        bFault       := TRUE;
        o_bBlockSolenoid := FALSE;
        iStep        := STP_IDLE;
        bRunning     := FALSE;
        i_bTime_Action := FALSE;
    END_IF;

(* ================================================================= *)
(* 步骤3: 输送正转 (将材料送到到位传感器位置)                          *)
(* 动作: 保持o_bConveyorFwd=TRUE                                       *)
(* 转出条件: i_bPositionSensor1 AND i_bPositionSensor2 (双传感器冗余)     *)
(* 超时条件: ALM_CONVEYOR_TIMEOUT                                      *)
(* ================================================================= *)
STP_CONVEYOR_FWD:
    o_bConveyorFwd := TRUE;  (* 保持正转 *)

    IF i_bPositionSensor1 AND i_bPositionSensor2 THEN
        iStep := STP_POSITION_CHECK;
        o_bConveyorFwd := FALSE;
        i_bTime_Conveyor := FALSE;
        i_bTime_Action := TRUE;
    ELSIF q_bTq_Conveyor THEN
        (* 超时: 输送未到位 *)
        iActiveAlarm := ALM_CONVEYOR_TIMEOUT;
        bFault       := TRUE;
        o_bConveyorFwd := FALSE;
        iStep        := STP_IDLE;
        bRunning     := FALSE;
        i_bTime_Conveyor := FALSE;
    END_IF;

(* ================================================================= *)
(* 步骤4: 到位检测 (短暂稳定等待后进入阻挡上升)                        *)
(* 动作: 保持阻挡,全部输出关闭,等待稳定                                *)
(* 转出条件: 定时器到期                                               *)
(* ================================================================= *)
STP_POSITION_CHECK:
    (* 全部输出保持关闭,等待稳定,但保持阻挡 *)
    o_bBlockSolenoid := TRUE;

    IF q_bTq_Action THEN
        iStep := STP_BLOCK_UP;
        o_bBlockSolenoid := FALSE;  (* 开始阻挡上升(释放) *)
    END_IF;

(* ================================================================= *)
(* 步骤5: 阻挡上升 (释放材料,准备分料)                                 *)
(* 动作: 保持o_bBlockSolenoid=FALSE (上升状态)                         *)
(* 转出条件: i_bBlockCylinderUp                                        *)
(* 超时条件: ALM_BLOCK_UP_TIMEOUT                                      *)
(* ================================================================= *)
STP_BLOCK_UP:
    o_bBlockSolenoid := FALSE;  (* 保持上升状态 *)

    IF i_bBlockCylinderUp THEN
        (* 阻挡已上升,进入分料 *)
        iStep := STP_SEPARATE_ACTION;
        o_bSeparateSolenoid := TRUE;  (* 推出分料 *)
    ELSIF q_bTq_Action THEN
        (* 超时: 阻挡未上升 *)
        iActiveAlarm := ALM_BLOCK_UP_TIMEOUT;
        bFault       := TRUE;
        iStep        := STP_IDLE;
        bRunning     := FALSE;
        i_bTime_Action := FALSE;
    END_IF;

(* ================================================================= *)
(* 步骤6: 分料动作 (分料气缸推出,将材料分离)                           *)
(* 动作: 保持o_bSeparateSolenoid=TRUE                                  *)
(* 转出条件: i_bSeparateCylinderDown                                   *)
(* 超时条件: ALM_SEPARATE_PUSH_TIMEOUT                                  *)
(* ================================================================= *)
STP_SEPARATE_ACTION:
    o_bSeparateSolenoid := TRUE;  (* 保持推出 *)

    IF i_bSeparateCylinderDown THEN
        (* 分料到位,转入慢速送出 *)
        iStep := STP_SLOW_FEED;
        o_bSeparateSolenoid := FALSE;
        o_bConveyorSlow := TRUE;
        i_bTime_Action := FALSE;
        i_bTime_Conveyor := TRUE;
    ELSIF q_bTq_Action THEN
        (* 超时: 分料未到位 *)
        iActiveAlarm := ALM_SEPARATE_PUSH_TIMEOUT;
        bFault       := TRUE;
        o_bSeparateSolenoid := FALSE;
        iStep        := STP_IDLE;
        bRunning     := FALSE;
        i_bTime_Action := FALSE;
    END_IF;

(* ================================================================= *)
(* 步骤7: 慢速送出 (精确送出到取料位置)                                 *)
(* 动作: o_bConveyorSlow=TRUE, o_bSeparateSolenoid=FALSE(持续复位)       *)
(* 转出条件: 定时器到期 + 分料已复位验证                                *)
(* 超时/异常: ALM_SEPARATE_RESET_TIMEOUT                                *)
(* ================================================================= *)
STP_SLOW_FEED:
    o_bConveyorSlow     := TRUE;
    o_bSeparateSolenoid := FALSE;

    IF q_bTq_Conveyor THEN
        (* 验证分料气缸是否已复位 *)
        IF NOT i_bSeparateCylinderDown OR i_bSeparateCylinderUp THEN
            (* 正常: 分料已复位或在下位信号消失 *)
            iStep := STP_FEED_COMPLETE;
            o_bConveyorSlow := FALSE;
            o_bFeedComplete := TRUE;
            i_bTime_Conveyor := FALSE;
            i_bTime_Pulse := TRUE;
        ELSE
            (* 异常: 分料气缸卡在推出位置 *)
            iActiveAlarm := ALM_SEPARATE_RESET_TIMEOUT;
            bFault       := TRUE;
            o_bConveyorSlow := FALSE;
            iStep        := STP_IDLE;
            bRunning     := FALSE;
            i_bTime_Conveyor := FALSE;
        END_IF;
    END_IF;

(* ================================================================= *)
(* 步骤8: 放料完成 (等待下游取料完成后回到空闲)                         *)
(* 动作: 保持o_bFeedComplete=TRUE (脉冲500ms或直到下游确认)               *)
(* 转出条件: 启动触发被消耗(下一轮启动可重新开始)                        *)
(* ================================================================= *)
STP_FEED_COMPLETE:
    (* 放料完成脉冲控制: 保持500ms后自动结束 *)
    IF q_bTq_Pulse THEN
        iStep           := STP_IDLE;
        bRunning        := FALSE;
        o_bFeedComplete := FALSE;
        bStartTriggered := FALSE;
        i_bTime_Pulse := FALSE;
    ELSE
        o_bFeedComplete := TRUE;
    END_IF;

ELSE
    (* 无效步序: 强制归零 *)
    iStep   := STP_IDLE;
    bRunning := FALSE;
    i_bTime_Action   := FALSE;
    i_bTime_Conveyor := FALSE;
    i_bTime_Reset    := FALSE;
    i_bTime_Pulse    := FALSE;

END_CASE;


(* ==================== 第七部分: 状态输出汇总 ================= *)

(* 运行中标志 *)
o_bRunning := bRunning;

(* 故障标志 *)
o_bFault := bFault;

(* 当前状态: 有故障则返回99,否则返回当前步序 *)
IF bFault THEN
    o_iCurrentState := 99;
ELSE
    o_iCurrentState := iStep;
END_IF;

(* 报警代码输出 *)
o_iAlarmCode := iActiveAlarm;


(* ***************************** 子程序区域 ***************************** *)


(* ==================== 子程序: 自动模式状态机 ================= *)
(* 注意: 实际的状态机逻辑已在第六部分的CASE语句中实现                   *)
(* 此子程序保留用于未来扩展或复杂逻辑封装                              *)
METHOD CALL_AutoModeStateMachine : VOID
    (* 状态机主体已在主程序第六部分实现,此处无需重复代码 *)
END_METHOD


(* ==================== 子程序: 手动模式控制 ================= *)
(* 6个手动操作,带互锁和安全限制                                        *)
METHOD CALL_ManualModeControl : VOID

    (* 故障层禁止手动操作 *)
    IF bFault THEN
        bManualAllow      := FALSE;
        o_bBlockSolenoid  := FALSE;
        o_bSeparateSolenoid := FALSE;
        o_bConveyorFwd    := FALSE;
        o_bConveyorSlow   := FALSE;
        o_bConveyorRev    := FALSE;
        iStep             := STP_IDLE;

        (* 停止所有计时器 *)
        i_bTime_Action   := FALSE;
        i_bTime_Conveyor := FALSE;
        i_bTime_Reset    := FALSE;
        i_bTime_Pulse    := FALSE;

        RETURN;
    END_IF;

    bManualAllow := TRUE;
    bRunning     := FALSE;
    iStep        := STP_IDLE;
    o_bFeedComplete := FALSE;

    (* 停止所有自动计时器 *)
    i_bTime_Action   := FALSE;
    i_bTime_Conveyor := FALSE;
    i_bTime_Pulse    := FALSE;

    (* ------ 手动操作 - 阻挡气缸控制 (互锁: 下降/上升不能同时) ------ *)
    IF i_bLx_BlockDown AND NOT i_bLx_BlockUp THEN
        o_bBlockSolenoid := TRUE;  (* 下降 *)
    ELSIF i_bLx_BlockUp AND NOT i_bLx_BlockDown THEN
        o_bBlockSolenoid := FALSE;  (* 上升 *)
    ELSE
        (* 无操作: 保持当前位置 *)
    END_IF;

    (* ------ 手动操作 - 分料气缸控制 (互锁: 推出/复位不能同时) ------ *)
    IF i_bLx_SeparatePush AND NOT i_bLx_SeparateReset THEN
        o_bSeparateSolenoid := TRUE;  (* 推出 *)
    ELSIF i_bLx_SeparateReset AND NOT i_bLx_SeparatePush THEN
        o_bSeparateSolenoid := FALSE;  (* 复位 *)
    ELSE
        (* 无操作 *)
    END_IF;

    (* ------ 手动操作 - 输送带控制 (互锁: 正转/反转不能同时,慢速可叠加) -- *)
    IF i_bLx_ConveyorFwd AND NOT i_bLx_ConveyorRev THEN
        o_bConveyorFwd := TRUE;
        o_bConveyorRev := FALSE;
    ELSIF i_bLx_ConveyorRev AND NOT i_bLx_ConveyorFwd THEN
        o_bConveyorFwd := FALSE;
        o_bConveyorRev := TRUE;
    ELSE
        o_bConveyorFwd := FALSE;
        o_bConveyorRev := FALSE;
    END_IF;

    (* 慢速可作为独立控制或与正转叠加(根据实际工艺需求调整) *)
    o_bConveyorSlow := FALSE;  (* 手动模式下默认不用慢速,可按需修改 *)

END_FUNCTION_BLOCK
