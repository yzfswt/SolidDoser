from ctypes import *
from pathlib import Path
import os

'''
名称: 四轴485机械臂python接口库
所属: 深圳市慧灵科技有限公司
适用: windows/linux[ubuntu]
修改: 25/01/17
内容: 网络通信[3]/初始设置[7]/查询设置[4]/拖动示教[2]/碰撞设置[3]
      /停止恢复[7]/限位判断[2]/运动判断[3]/运动指令[11]/运动设置[4]
      /第五轴设置[7]/io设置[4]/脉冲夹爪[6]/485夹爪[18]/吸盘设置[4]
      /正逆输出[2]/工具设置[4]/日志设置[1]
'''

class HitbotInterface:
    # 机械臂ID
    card_number = 0
    # 机械臂反馈位置
    x, y, z, r, angle1, angle2 = [0.0] * 6
    communicate_success, initial_finish, move_flag = False, False, False
    # 编码器反馈位置
    encoder_x, encoder_y, encoder_z, encoder_r, encoder_angle1, encoder_angle2 = [0.0] * 6
    # 夹爪类型与反馈
    efg_distance, efg_type, erg_distance, erg_angle, current_clamping, current_rotation = [0.0] * 6
    # 工具尺寸
    tool_length, tool_angle = [0.0] * 2

    def __init__(self, card_number):
        self.card_number = card_number
        self.x, self.y, self.z, self.r, self.angle1, self.angle2 = [0.0] * 6
        self.efg_distance, self.efg_type, self.erg_distance, self.erg_angle = [0.0] * 4
        self.current_clamping, self.current_rotation = [0.0] * 2
        self.tool_length, self.tool_angle = [0.0] * 2

# ----- 网络通信 [total: 3] --------------------------------------------------
    def net_port_initial(self):
        ''' 
        导入机械臂SDK库文件: 
            1.与python执行文件置于同一目录下
            2.linux版直接使用.so即可
            3.windows版除.dll外, 还需要server.exe与share.dll
        注意：须在 SDK 目录（含 server.exe）下调用，或先 chdir 到该目录。
        '''
        sdk_dir = Path(__file__).resolve().parent
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(sdk_dir))
        # 与官方 demo 一致：相对路径加载，依赖当前工作目录为 SDK 目录
        self.dll = CDLL(".\\small_scara_interface.dll", 0)
        self.dll.net_port_initial.restype = c_int
        return self.dll.net_port_initial()
    
    def is_connect(self):
        return self.dll.robot_is_connect(c_int(self.card_number))

    def close_server(self):
        self.dll.robot_close_server()

# ----- 初始设置 [total: 7] --------------------------------------------------
    def initial(self, generation, z_trail):
        return self.dll.robot_initial(c_int(self.card_number), c_int(generation), c_float(z_trail))
    
    def set_arm_length(self, l1, l2):
        self.dll.robot_set_arm_length(c_int(self.card_number), c_float(l1), c_float(l2))

    def check_joint(self, joint_num, state):
        return self.dll.robot_check_joint(c_int(self.card_number), c_int(joint_num), c_bool(state))
    
    def set_Interpolation_position_buf_catch_count(self, count):
        return self.dll.robot_set_Interpolation_position_buf_catch_count(c_int(self.card_number), c_int(count))
    
    def set_robot_buf_size(self, bufsize):
        return self.dll.robot_set_robot_buf_size(c_int(self.card_number), c_int(bufsize))

    def unlock_position(self):
        return self.dll.robot_unlock_position(c_int(self.card_number))
    
    def joint_home(self, joint_num):
        return self.dll.robot_joint_home(c_int(self.card_number), c_int(joint_num))

# ----- 查询设置 [total: 4] --------------------------------------------------
    def get_scara_param(self):
        c_x, c_y, c_z, c_r, c_angle1, c_angle2 = c_float(0), c_float(0), c_float(0), c_float(0), c_float(0), c_float(0)
        c_communicate_success, c_initial_finish, c_move_flag = c_bool(False), c_bool(False), c_bool(False)
        self.dll.robot_get_scara_param(c_int(self.card_number), byref(c_x), byref(c_y), byref(c_z), byref(c_angle1),byref(c_angle2), byref(c_r), 
                                       byref(c_communicate_success),byref(c_initial_finish),byref(c_move_flag))
        self.x, self.y, self.z, self.r, self.angle1, self.angle2 = c_x.value, c_y.value, c_z.value, c_r.value, c_angle1.value, c_angle2.value
        self.communicate_success, self.initial_finish, self.move_flag = c_communicate_success.value, c_initial_finish.value, c_move_flag.value

    def get_encoder_coor(self):
        c_x, c_y, c_z, c_r, c_angle1, c_angle2 = c_float(0), c_float(0), c_float(0), c_float(0), c_float(0), c_float(0)
        self.dll.robot_get_encoder_param(c_int(self.card_number), byref(c_x), byref(c_y), byref(c_z), byref(c_angle1), byref(c_angle2), byref(c_r))
        self.encoder_x, self.encoder_y, self.encoder_z, self.encoder_r, self.encoder_angle1, self.encoder_angle2  = c_x.value, c_y.value, c_z.value, c_r.value, c_angle1.value, c_angle2.value

    def get_joint_state(self, joint_num):
        return self.dll.robot_get_joint_state(c_int(self.card_number), c_int(joint_num))
    
    def get_error_code(self):
        return self.dll.robot_get_error_code(c_int(self.card_number))
    
# ----- 拖动示教 [total: 2] --------------------------------------------------
    def set_drag_teach(self, enable):
        return self.dll.robot_set_drag_teach(c_int(self.card_number), c_bool(enable))

    def get_drag_teach(self):
        return self.dll.robot_get_drag_teach(c_int(self.card_number))

# ----- 碰撞设置 [total: 3] --------------------------------------------------
    def set_cooperation_fun_state(self, enable):
        return self.dll.robot_set_cooperation_fun_state(c_int(self.card_number), c_bool(enable))

    def get_cooperation_fun_state(self):
        return self.dll.robot_get_cooperation_fun_state(c_int(self.card_number))

    def is_collision(self):
        return self.dll.robot_is_collision(c_int(self.card_number))

# ----- 停止恢复 [total: 7] --------------------------------------------------
    def stop_move(self):
        return self.dll.robot_stop_move(c_int(self.card_number))
    
    def new_stop_move(self):
        return self.dll.robot_new_stop_move(c_int(self.card_number))
    
    def emergency_stop(self):
        return self.dll.robot_emergency_stop(c_int(self.card_number))
    
    def pause_move(self):
        return self.dll.robot_pause_move(c_int(self.card_number))

    def resume_move(self):
        return self.dll.robot_resume_move(c_int(self.card_number))
    
    def get_hard_emergency_stop_state(self):
        return self.dll.robot_get_hard_emergency_stop_state(c_int(self.card_number))
    
    def clear_hard_emergency_stop(self):
        return self.dll.robot_clear_hard_emergency_stop(c_int(self.card_number))
    
# ----- 限位判断 [total: 2] --------------------------------------------------
    def judge_in_range_xyzr(self, x,y,z,r):
        return self.dll.robot_judge_in_range_xyzr(c_int(self.card_number), c_float(x), c_float(y), c_float(z), c_float(r))
    
    def judge_in_range_a12r(self, angle1,angle2,r):
        return self.dll.robot_judge_in_range_a12r(c_int(self.card_number), c_float(angle1), c_float(angle2),  c_float(r))

# ----- 运动判断 [total: 3] --------------------------------------------------
    def wait_stop(self):
        return self.dll.robot_wait_stop(c_int(self.card_number))

    def is_stop(self):
        return self.dll.robot_is_stop(c_int(self.card_number))
    
    def is_robot_goto_target(self,target_x,target_y,target_z,target_r):
        return self.dll.is_robot_goto_target(c_int(self.card_number),c_float(target_x),c_float(target_y),c_float(target_z),c_float(target_r))

# ----- 运动指令 [total: 11] --------------------------------------------------
    def movel_xyz(self, goal_x, goal_y, goal_z, goal_r, speed):
        return self.dll.robot_movel_xyz(c_int(self.card_number), c_float(goal_x), c_float(goal_y), c_float(goal_z), c_float(goal_r), c_float(speed))

    def movel_xyz_by_offset(self, x_offset, y_offset, z_offset, r_offset, speed):
        return self.dll.robot_movel_xyz_by_offset(c_int(self.card_number), c_float(x_offset), c_float(y_offset), c_float(z_offset), c_float(r_offset), c_float(speed))

    def movej_angle(self, goal_angle1, goal_angle2, goal_z, goal_r, speed, roughly): # 过时，不推荐使用
        return self.dll.robot_movej_angle(c_int(self.card_number), c_float(goal_angle1), c_float(goal_angle2), c_float(goal_z), c_float(goal_r), c_float(speed), c_float(roughly))

    def movej_xyz(self, goal_x, goal_y, goal_z, goal_r, speed, roughly): # 过时，不推荐使用
        return self.dll.robot_movej_xyz(c_int(self.card_number), c_float(goal_x), c_float(goal_y), c_float(goal_z), c_float(goal_r), c_float(speed), c_float(roughly))
    
    def movej_xyz_lr(self, goal_x, goal_y, goal_z, goal_r, speed, roughly, lr): # 过时，不推荐使用
        return self.dll.robot_movej_xyz_lr(c_int(self.card_number), c_float(goal_x), c_float(goal_y), c_float(goal_z), c_float(goal_r), c_float(speed), c_float(roughly), c_int(lr))

    def new_movej_angle(self, goal_angle1, goal_angle2, goal_z, goal_r, speed, roughly):
        return self.dll.robot_new_movej_angle(c_int(self.card_number), c_float(goal_angle1), c_float(goal_angle2), c_float(goal_z), c_float(goal_r), c_float(speed), c_float(roughly))

    def new_movej_xyz_lr(self, goal_x, goal_y, goal_z, goal_r, speed, roughly, lr):
        return self.dll.robot_new_movej_xyz_lr(c_int(self.card_number), c_float(goal_x), c_float(goal_y), c_float(goal_z), c_float(goal_r), c_float(speed), c_float(roughly), c_int(lr))

    def xyz_move(self, direction,distance, speed):
        return self.dll.robot_xyz_move(c_int(self.card_number), c_int(direction), c_float(distance),c_float(speed))
    
    def new_move_xyz(self,  goal_x, goal_y, goal_z, goal_r, speed, lr,motiontype):
        return self.dll.robot_new_move_xyz(c_int(self.card_number), c_float(goal_x), c_float(goal_y), c_float(goal_z), c_float(goal_r), c_float(speed), c_int(lr),c_int(motiontype))

    def single_joint_move(self, axis,distance, speed):
        return self.dll.robot_single_joint_move(c_int(self.card_number), c_int(axis), c_float(distance),c_float(speed))
    
    def jog_move(self, x_a1_dir, y_a2_dir, z_dir, r_dir, speed, type):
        return self.dll.robot_jog_move(c_int(self.card_number), c_float(x_a1_dir), c_float(y_a2_dir), c_float(z_dir), c_float(r_dir), c_float(speed), c_int(type))

# ----- 运动设置 [total: 4] --------------------------------------------------
    def change_attitude(self, speed):
        return self.dll.robot_change_attitude(c_int(self.card_number), c_float(speed))
    
    def new_set_acc(self, j1_max_acc, j2_max_acc, j3_max_acc, j4_max_acc):
        return self.dll.robot_new_set_acc(c_int(self.card_number), c_float(j1_max_acc), c_float(j2_max_acc), c_float(j3_max_acc), c_float(j4_max_acc))

    def set_robot_joint_torque_value(self, jointnum,value):
        return self.dll.robot_set_robot_joint_torque_value(c_int(self.card_number), c_int(jointnum), c_int(value))
    
    def hi_position_send(self, j1_deg, j2_deg, j3_mm, j4_deg):
        return self.dll.robot_position_send(c_int(self.card_number), c_float(j1_deg), c_float(j2_deg), c_float(j3_mm), c_float(j4_deg))

# ----- 第五轴设置 [total: 7] -------------------------------------------------   
    def get_j5_positon(self, type):
        return self.dll.robot_get_j5_positon(c_int(self.card_number), c_int(type))
    
    def j5_motor_zero(self):
        return self.dll.robot_j5_motor_zero(c_int(self.card_number))

    def set_j5_motor_pos(self, deg, speed):
        self.dll.robot_set_j5_motor_pos.restype = c_float
        return self.dll.robot_set_j5_motor_pos(c_int(self.card_number), c_float(deg), c_float(speed))

    def get_j5_parameter(self):
        self.dll.robot_get_j5_parameter.restype = c_float
        return self.dll.robot_get_j5_parameter(c_int(self.card_number))
    
    def get_j5_motor_state(self):
        self.dll.robot_get_j5_motor_state.restype = c_float
        return self.dll.robot_get_j5_motor_state(c_int(self.card_number))
    
    def get_j5_motor_pos(self):
        self.dll.robot_get_j5_motor_pos.restype = c_float
        return self.dll.robot_get_j5_motor_pos(c_int(self.card_number))

    def movej_j5(self, deg, speed):
        return self.dll.robot_movej_j5(c_int(self.card_number), c_float(deg), c_float(speed))

# ----- io设置 [total: 4] -----------------------------------------------------  
    def set_digital_out(self, io_number, io_value):
        return self.dll.robot_set_digital_io_out(c_int(self.card_number), c_int(io_number), c_int(io_value))

    def get_digital_out(self, io_number):
        return self.dll.robot_get_digital_io_out(c_int(self.card_number), c_int(io_number))

    def get_digital_in(self, io_number):
        return self.dll.robot_get_digital_io_in(c_int(self.card_number), c_int(io_number))
    
    def set_stop_io(self, io_number,io_value):
        self.dll.robot_set_stop_io(c_int(self.card_number), c_int(io_number), c_int(io_value))

# ----- 脉冲夹爪 [total: 6] -----------------------------------------------------  
    def set_efg_state(self, efg_type, efg_distance):
        return self.dll.robot_set_efg_state(c_int(self.card_number), c_int(efg_type), c_float(efg_distance))

    def get_efg_state(self):
        c_efg_type = c_int(0)
        c_efg_distance = c_float(0)
        ret = self.dll.robot_get_efg_state(c_int(self.card_number), byref(c_efg_type), byref(c_efg_distance))
        self.efg_type = c_efg_type
        self.efg_distance = c_efg_distance.value
        return ret
    
    def new_set_efg_state(self, channel,efg_type, efg_distance):
        return self.dll.robot_new_set_efg_state(c_int(self.card_number), c_int(channel),c_int(efg_type), c_float(efg_distance))
    
    def new_get_efg_state(self,channel,efg_type):
        c_efg_distance = c_float(0)
        ret = self.dll.robot_new_get_efg_state(c_int(self.card_number), c_int(channel),c_int(efg_type), byref(c_efg_distance))
        self.efg_distance = c_efg_distance
        return ret

    def get_efg_state_dji(self):
        c_efg_type = c_int(0)
        c_efg_distance = c_float(0)
        ret = self.dll.robot_get_efg_state_dji(c_int(self.card_number), byref(c_efg_type), byref(c_efg_distance))
        self.efg_type = c_efg_type
        self.efg_distance = c_efg_distance
        return ret

    def set_efg_state_dji(self, efg_type, efg_distance):
        return self.dll.robot_set_efg_state_dji(c_int(self.card_number), c_int(efg_type), c_float(efg_distance))

# ----- 485夹爪 [total: 18] ------------------------------------------------------  
    def com485_initial(self, baudRate):
        return self.dll.robot_com485_initial(c_int(self.card_number), c_int(baudRate))

    def com485_send(self, data,len):
        return self.dll.robot_com485_send(c_int(self.card_number), c_char_p(data), c_char(len))

    def com485_recv(self, data):
        return self.dll.robot_com485_recv(c_int(self.card_number), c_char_p(data))
    
    def com485_set_channel(self, channel):
        return self.dll.robot_com485_set_channel(c_int(self.card_number), c_int(channel))
    
    def com485_init(self): #手动初始化
        return self.dll.robot_com485_init(c_int(self.card_number))
    
    def com485_set_rotation_speed(self, speed): #设置旋转速度
        return self.dll.robot_com485_set_rotation_speed(c_int(self.card_number), c_float(speed))
    
    def com485_set_clamping_speed(self, speed): #设置旋转速度
        return self.dll.robot_com485_set_clamping_speed(c_int(self.card_number), c_float(speed))
    
    def com485_set_clamping_distance(self, distance): #设置夹持距离
        return self.dll.robot_com485_set_clamping_distance(c_int(self.card_number), c_float(distance))
    
    def com485_get_clamping_distance(self): #获取夹持距离
        result = self.dll.robot_com485_get_clamping_distance(c_int(self.card_number))
        self.erg_distance = result
        return result
    
    def com485_set_rotation_angle(self, angle): #设置绝对旋转角度
        return self.dll.robot_com485_set_rotation_angle(c_int(self.card_number), c_float(angle))
    
    def com485_set_relative_rotation_angle(self, angle): #设置相对旋转角度
        return self.dll.robot_com485_set_relative_rotation_angle(c_int(self.card_number), c_float(angle))
    
    def com485_get_rotation_angle(self): #获取旋转角度
        result = self.dll.robot_com485_get_rotation_angle(c_int(self.card_number))
        self.erg_angle = result
        return result
    
    def com485_get_clamping_state(self): #获取夹持状态
        return self.dll.robot_com485_get_clamping_state(c_int(self.card_number))
    
    def com485_get_rotation_state(self): #获取旋转状态
        return self.dll.robot_com485_get_rotation_state(c_int(self.card_number))
    
    def com485_set_clamping_current(self, current): #设置夹持电流
        return self.dll.robot_com485_set_clamping_current(c_int(self.card_number), c_float(current))
    
    def com485_set_rotation_current(self, current): #设置旋转电流
        return self.dll.robot_com485_set_rotation_current(c_int(self.card_number), c_float(current))
    
    def com485_get_clamping_current(self): #获取夹持电流
        result = self.dll.robot_com485_get_clamping_current(c_int(self.card_number))
        self.current_clamping = result
        return result
    
    def com485_get_rotation_current(self):
        result = self.dll.robot_com485_get_rotation_current(c_int(self.card_number))
        self.current_rotation = result
        return result

# ----- 吸盘设置 [total: 4] ----------------------------------------------------- 
    def com485_suction_cup_control(self, type):
        return self.dll.robot_com485_suction_cup_control(c_int(self.card_number), c_int(type))
    
    def com485_min_vacuum_degree(self, degree):
        return self.dll.robot_com485_min_vacuum_degree(c_int(self.card_number), c_int(degree))
    
    def com485_max_vacuum_degree(self, degree):
        return self.dll.robot_com485_max_vacuum_degree(c_int(self.card_number), c_int(degree))
    
    def com485_get_draw_state(self):
        return self.dll.robot_com485_get_draw_state(c_int(self.card_number))

# ----- 正逆输出 [total: 2] ----------------------------------------------------- 
    def inverse_calculate(self, x, y, r, hand):
        c_j1, c_j2 = c_float(0), c_float(0)
        ret = self.dll.robot_inverse_calculate(c_int(self.card_number), c_float(x), c_float(y), c_float(r), c_int(hand), byref(c_j1), byref(c_j2))
        self.angle1, self.angle2 = c_j1.value, c_j2.value
        return ret
    
    def forward_calculate(self, angle1, angle2, r):
        c_x, c_y = c_float(0), c_float(0)
        ret = self.dll.robot_forward_calculate(c_int(self.card_number), c_float(angle1), c_float(angle2), c_float(r), byref(c_x), byref(c_y))
        self.x, self.y = c_x.value, c_y.value
        return ret

# ----- 工具设置 [total: 4] ----------------------------------------------------- 
    def set_tool_fun1(self, tool_length, tool_angle):
        return self.dll.robot_set_tool_fun1(c_int(self.card_number), c_float(tool_length), c_float(tool_angle))
    
    def set_tool_fun2(self, tcp_x, tcp_y):
        return self.dll.robot_set_tool_fun2(c_int(self.card_number), c_float(tcp_x), c_float(tcp_y))
    
    def set_tool_fun3(self, p1_x, p1_y, p1_r, p2_x, p2_y, p2_r):
        return self.dll.robot_set_tool_fun3(c_int(self.card_number), c_float(p1_x), c_float(p1_y), c_float(p1_r), c_float(p2_x), c_float(p2_y), c_float(p2_r))
    
    def get_tool(self):
        c_tool_length, c_tool_angle = c_float(0), c_float(0)
        ret = self.dll.robot_get_tool(c_int(self.card_number), byref(c_tool_length), byref(c_tool_angle))
        self.tool_length, self.tool_angle = c_tool_length.value, c_tool_angle.value
        return ret

# ----- 日志设置 [total: 1] -----------------------------------------------------
    def hide_logs(self, hide):
        return self.dll.robot_hide_logs(c_int(self.card_number), c_bool(hide))
