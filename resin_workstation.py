import json
import socket
import threading
import time
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from functools import wraps

from pylabrobot.resources import Deck, Resource as PLRResource
from unilabos.devices.workstation.workstation_base import WorkstationBase
from unilabos.ros.nodes.presets.workstation import ROS2WorkstationNode
from unilabos.utils.log import logger


@dataclass
class ReactorState:
    """
    反应器状态类
    """
    reactor_id: int  # 反应器编号
    current_temperature: float = 0.0  # 当前温度
    target_temperature: float = 0.0  # 目标温度
    stirring_status: bool = False  # 搅拌状态
    stirring_speed: float = 0.0  # 搅拌转速
    n2_status: bool = False  # 氮气状态
    air_status: bool = False  # 空气状态
    status: str = "idle"  # 运行状态：idle, running, error
    error_message: str = ""  # 错误信息


@dataclass
class PostProcessState:
    """
    后处理系统状态类
    """
    post_process_id: int  # 后处理编号
    cleaning_status: bool = False  # 清洗状态
    discharge_status: bool = False  # 排液状态
    transferring_status: bool = False  # 溶液转移状态
    start_bottle: str = ""  # 当前转移起始瓶
    end_bottle: str = ""  # 当前转移终点瓶
    current_volume: float = 0.0  # 当前转移体积
    target_volume: float = 0.0  # 目标转移体积
    status: str = "idle"  # 运行状态：idle, running, error
    error_message: str = ""  # 错误信息


@dataclass
class DeviceState:
    """
    设备整体状态类
    """
    connected: bool = False  # 连接状态
    operation_mode: str = "local"  # 操作模式：local, remote
    device_status: str = "idle"  # 设备状态：idle, running, error
    reactors: Dict[int, ReactorState] = None  # 反应器状态字典
    post_processes: Dict[int, PostProcessState] = None  # 后处理系统状态字典
    last_updated: str = ""  # 最后更新时间
    error_message: str = ""  # 设备级错误信息
    solution_add_status: str = "idle"  # 溶液添加状态：idle, running, error
    current_solution_id: int = 0  # 当前添加的溶液编号
    current_volume: float = 0.0  # 当前添加的体积
    target_volume: float = 0.0  # 目标添加体积
    current_reactor_id: int = 0  # 当前添加的反应器编号
    
    def __post_init__(self):
        if self.reactors is None:
            self.reactors = {}
        if self.post_processes is None:
            self.post_processes = {}
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")


class UDPClient:
    """
    UDP客户端类，用于与设备进行通信
    """
    def __init__(self, address: str = "127.0.0.1", port: int = 8888, timeout: float = 5.0):
        self.address = address
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self.lock = threading.Lock()
        self.status_callback = None  # 状态更新回调函数
        self.listen_thread = None  # 状态监听线程
        self.listen_running = False  # 监听线程运行状态
        
        # 命令类型配置：立即响应/长时间运行
        self._immediate_response_commands = {
            "TOGGLE_LOCAL_REMOTE_CONTROL",
            "GET_DEVICE_STATE",
            "GET_REACTOR_STATE",
            "GET_POST_PROCESS_STATE",
            "REACTOR_N2_ON",
            "REACTOR_N2_OFF",
            "REACTOR_AIR_ON",
            "REACTOR_AIR_OFF",
            "TEMP_SET",
            "START_STIR",
            "STOP_STIR",
            "POST_PROCESS_DISCHARGE_ON",
            "POST_PROCESS_DISCHARGE_OFF"
        }
        
        self._long_running_commands = {
            "REACTOR_SOLUTION_ADD",
            "POST_PROCESS_SOLUTION_ADD",
            "POST_PROCESS_CLEAN",
            "WAIT"
        }
        
        # 任务管理相关属性
        self.tasks = {}  # 任务ID到任务信息的映射
        self.task_callbacks = {}  # 任务ID到回调函数的映射
        self._task_counter = 0  # 任务计数器，用于生成唯一任务ID
        self._task_lock = threading.Lock()  # 任务管理锁
    
    def connect(self) -> bool:
        """
        连接到UDP服务器
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        try:
            # UDP是无连接协议，这里只是初始化socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)
            self.connected = True
            logger.info(f"UDP客户端已初始化，目标地址: {self.address}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"UDP客户端初始化失败: {e}")
            self.connected = False
            return False
    
    def set_status_callback(self, callback):
        """
        设置状态更新回调函数
        
        Args:
            callback: 回调函数，接收状态数据作为参数
        """
        self.status_callback = callback
    
    def start_listen(self):
        """
        启动状态监听线程
        """
        if self.listen_running:
            logger.warning("状态监听线程已在运行")
            return
            
        self.listen_running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info("UDP状态监听线程已启动")
    
    def stop_listen(self):
        """
        停止状态监听线程
        """
        self.listen_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1.0)
            self.listen_thread = None
        logger.info("UDP状态监听线程已停止")
    
    def _listen_loop(self):
        """
        状态监听循环，接收服务器主动推送的状态更新
        """
        while self.listen_running and self.connected and self.socket:
            try:
                # 设置较短的超时，以便定期检查listen_running状态
                self.socket.settimeout(0.5)
                response_data, _ = self.socket.recvfrom(1024)
                
                # 尝试解析JSON响应
                try:
                    response = json.loads(response_data.decode('utf-8'))
                    logger.debug(f"收到UDP状态更新: {response}")
                    
                    # 检查是否包含任务ID
                    task_id = response.get("task_id")
                    
                    if task_id:
                        # 处理任务相关的状态更新
                        task_status = response.get("status")
                        task_data = response.get("data", {})
                        
                        logger.debug(f"收到任务更新: 任务ID={task_id}, 状态={task_status}, 数据={task_data}")
                        
                        # 更新任务状态
                        with self._task_lock:
                            if task_id in self.tasks:
                                self.tasks[task_id]["status"] = task_status
                                self.tasks[task_id]["data"] = task_data
                                self.tasks[task_id]["updated_at"] = time.time()
                        
                        # 调用任务回调函数
                        with self._task_lock:
                            if task_id in self.task_callbacks:
                                callback = self.task_callbacks[task_id]
                                try:
                                    callback(task_id, task_status, task_data)
                                except Exception as e:
                                    logger.error(f"任务回调执行失败: {e}")
                    
                    # 如果是状态更新消息，调用回调函数
                    if response.get("type") == "status_update" and self.status_callback:
                        self.status_callback(response.get("data", {}))
                except json.JSONDecodeError:
                    logger.error(f"UDP响应格式错误: {response_data}")
            except socket.timeout:
                # 超时是正常的，继续监听
                continue
            except Exception as e:
                logger.error(f"UDP监听错误: {e}")
                # 短暂暂停后继续监听
                time.sleep(0.5)
    
    def disconnect(self) -> bool:
        """
        断开UDP连接
        
        Returns:
            bool: 断开成功返回True，否则返回False
        """
        try:
            # 停止监听线程
            self.stop_listen()
            
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            logger.info("UDP客户端已断开连接")
            
            # 清空任务列表和回调
            with self._task_lock:
                self.tasks.clear()
                self.task_callbacks.clear()
            
            return True
        except Exception as e:
            logger.error(f"UDP客户端断开连接失败: {e}")
            return False
    
    def _generate_task_id(self) -> str:
        """
        生成唯一的任务ID
        
        Returns:
            str: 唯一的任务ID
        """
        with self._task_lock:
            self._task_counter += 1
            return f"task_{self._task_counter}_{int(time.time() * 1000)}"
    
    def register_task(self, command: str, params: Dict[str, Any] = None) -> str:
        """
        注册一个新任务
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            str: 任务ID
        """
        task_id = self._generate_task_id()
        with self._task_lock:
            self.tasks[task_id] = {
                "command": command,
                "params": params or {},
                "status": "registered",
                "created_at": time.time(),
                "updated_at": time.time()
            }
        logger.debug(f"注册新任务: ID={task_id}, 命令={command}")
        return task_id
    
    def set_task_callback(self, task_id: str, callback) -> bool:
        """
        设置任务的回调函数
        
        Args:
            task_id: 任务ID
            callback: 回调函数，格式: callback(task_id, status, data)
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        with self._task_lock:
            if task_id in self.tasks:
                self.task_callbacks[task_id] = callback
                logger.debug(f"设置任务回调: ID={task_id}")
                return True
            else:
                logger.error(f"任务不存在: ID={task_id}")
                return False
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        with self._task_lock:
            return self.tasks.get(task_id, {})
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有任务信息
        """
        with self._task_lock:
            return self.tasks.copy()
    
    def clear_task(self, task_id: str) -> bool:
        """
        清除任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        with self._task_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                if task_id in self.task_callbacks:
                    del self.task_callbacks[task_id]
                logger.debug(f"清除任务: ID={task_id}")
                return True
            else:
                logger.error(f"任务不存在: ID={task_id}")
                return False
    
    def clear_all_tasks(self) -> None:
        """
        清除所有任务信息
        """
        with self._task_lock:
            self.tasks.clear()
            self.task_callbacks.clear()
            logger.debug("清除所有任务")
    
    def send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送命令到UDP服务器
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            Dict[str, Any]: 服务器响应
        """
        with self.lock:
            if not self.connected or not self.socket:
                logger.error("UDP客户端未连接")
                return {"status": "error", "message": "UDP客户端未连接"}
            
            try:
                # 构建函数调用格式命令
                params = params or {}
                
                # 处理参数，转换为函数调用格式
                param_list = []
                for key, value in params.items():
                    # 处理反应器ID，转换为reactor_1格式
                    if key == "reactor_id" or key == "post_process_id":
                        param_list.append(f"{key[:-3]}_{value}")
                    else:
                        # 根据参数类型格式化
                        if isinstance(value, str):
                            param_list.append(value)
                        else:
                            param_list.append(str(value))
                
                # 构建命令字符串，格式：S COMMAND_NAME(param1,param2,...)
                cmd_str = f"S {command}({','.join(param_list)})"
                
                # 发送命令
                data = cmd_str.encode('utf-8')
                self.socket.sendto(data, (self.address, self.port))
                print(f"发送UDP命令: {cmd_str}, 目标地址: {self.address}:{self.port}")
                logger.debug(f"发送UDP命令: {cmd_str}")
                
                # 根据命令类型决定是否等待响应
                if command in self._immediate_response_commands:
                    # 立即响应命令，设置合理的超时时间
                    try:
                        self.socket.settimeout(2.0)
                        response_data, _ = self.socket.recvfrom(1024)
                        
                        # 尝试解析响应，假设响应仍然是JSON格式
                        try:
                            response = json.loads(response_data.decode('utf-8'))
                            logger.debug(f"收到UDP响应: {response}")
                        except json.JSONDecodeError:
                            # 如果响应不是JSON格式，返回成功状态
                            response = {"status": "success", "message": "命令执行成功"}
                            logger.debug(f"收到UDP响应: {response_data.decode('utf-8')}")
                        
                        # 恢复监听线程的超时时间
                        self.socket.settimeout(0.5)
                        return response
                    except socket.timeout:
                        logger.error(f"UDP命令超时: {command}")
                        # 恢复监听线程的超时时间
                        self.socket.settimeout(0.5)
                        return {"status": "error", "message": "命令超时"}
                elif command in self._long_running_commands:
                    # 长时间运行命令，发送后立即返回成功，不等待响应
                    # 服务器会通过状态更新推送执行结果
                    logger.debug(f"长时间运行命令已发送，等待状态更新: {command}")
                    # 恢复监听线程的超时时间
                    self.socket.settimeout(0.5)
                    return {"status": "success", "message": "命令已接收，正在执行", "type": "async"}
                else:
                    # 未知命令类型，默认按立即响应处理
                    try:
                        self.socket.settimeout(2.0)
                        response_data, _ = self.socket.recvfrom(1024)
                        
                        # 尝试解析响应
                        try:
                            response = json.loads(response_data.decode('utf-8'))
                            logger.debug(f"收到UDP响应: {response}")
                        except json.JSONDecodeError:
                            response = {"status": "success", "message": "命令执行成功"}
                            logger.debug(f"收到UDP响应: {response_data.decode('utf-8')}")
                        
                        self.socket.settimeout(0.5)
                        return response
                    except socket.timeout:
                        logger.error(f"UDP命令超时: {command}")
                        self.socket.settimeout(0.5)
                        return {"status": "error", "message": "命令超时"}
            except Exception as e:
                logger.error(f"UDP命令执行失败: {command}, 错误: {e}")
                # 恢复监听线程的超时时间
                self.socket.settimeout(0.5)
                return {"status": "error", "message": str(e)}


class ResinWorkstation(WorkstationBase):
    """
    Resin工作站驱动类
    """
    def __init__(self, 
        config: dict = None, 
        deck=None, 
        address: str = "192.168.3.207",
        port: int = 8889,
        debug_mode: bool = False,
        *args,
        **kwargs):
        
        if deck is None and config:
            deck = config.get('deck')
        super().__init__(deck=deck, *args, **kwargs)
        self.debug_mode = debug_mode

        # UDP客户端初始化
        self.udp_client = UDPClient(address, port)
        self.connected = False
        
        # 设备状态
        self.success = False
        self.operation_mode = "local"  # local or remote
        
        # 初始化设备状态对象
        self._device_state = DeviceState()
        # 设置UDP客户端的状态更新回调
        self.udp_client.set_status_callback(self._handle_status_update)

    def post_init(self, ros_node: ROS2WorkstationNode):
        """
        初始化后设置
        
        Args:
            ros_node: ROS节点实例
        """
        self._ros_node = ros_node
        ROS2WorkstationNode.run_async_func(self._ros_node.update_resource, True, **{
            "resources": [self.deck]
        })

    # ====================== 设备连接管理 ======================
    def connect_device(self, address: str = None, port: int = None) -> bool:
        """
        连接设备
        
        Args:
            address: 设备IP地址
            port: 设备端口
            
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        if address:
            self.udp_client.address = address
        if port:
            self.udp_client.port = port
        
        self.connected = self.udp_client.connect()
        
        # 如果连接成功，启动状态监听
        if self.connected:
            self.udp_client.start_listen()
            # 更新设备状态
            self._device_state.connected = True
            self._device_state.operation_mode = self.operation_mode
        
        return self.connected

    def disconnect_device(self) -> bool:
        """
        断开设备连接
        
        Returns:
            bool: 断开成功返回True，否则返回False
        """
        success = not self.udp_client.disconnect()
        self.connected = not success
        
        # 更新设备状态
        self._device_state.connected = False
        self._device_state.device_status = "idle"
        
        return success

    def toggle_local_remote_control(self, mode: str) -> bool:
        """
        切换本地/远程控制模式
        
        Args:
            mode: 控制模式，"local"或"remote"
            
        Returns:
            bool: 切换成功返回True，否则返回False
        """
        if mode not in ["local", "remote"]:
            logger.error(f"无效的控制模式: {mode}")
            return False
        
        try:
            response = self.udp_client.send_command("TOGGLE_LOCAL_REMOTE_CONTROL", {"mode": mode})
            if response.get("status") == "success":
                self.operation_mode = mode
                return True
            else:
                logger.error(f"切换控制模式失败: {response.get('message')}")
                return False
        except Exception as e:
            logger.error(f"切换控制模式异常: {e}")
            return False
    
    # ====================== 状态查询方法 ======================
    def _get_device_state(self) -> DeviceState:
        """
        获取设备整体状态
        
        Returns:
            DeviceState: 设备整体状态对象
        """        
        # 发送状态查询命令
        response = self.udp_client.send_command("GET_DEVICE_STATE")
        if response.get("status") == "success":
            # 更新设备状态
            self.update_state(response.get("data", {}))
        
        return self._device_state
    
    def _get_reactor_state(self, reactor_id: int) -> Optional[ReactorState]:
        """
        获取单个反应器状态
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            Optional[ReactorState]: 反应器状态对象，若不存在则返回None
        """
        # 如果是调试模式，直接返回当前状态
        if self.debug_mode:
            return self._device_state.reactors.get(reactor_id)
        
        # 发送反应器状态查询命令
        response = self.udp_client.send_command("GET_REACTOR_STATE", {"reactor_id": reactor_id})
        if response.get("status") == "success":
            # 更新反应器状态
            self.update_state({"reactors": {reactor_id: response.get("data", {})}})
        
        return self._device_state.reactors.get(reactor_id)
    
    def _get_post_process_state(self, post_process_id: int) -> Optional[PostProcessState]:
        """
        获取单个后处理系统状态
        
        Args:
            post_process_id: 后处理编号
            
        Returns:
            Optional[PostProcessState]: 后处理系统状态对象，若不存在则返回None
        """
        # 如果是调试模式，直接返回当前状态
        if self.debug_mode:
            return self._device_state.post_processes.get(post_process_id)
        
        # 发送后处理状态查询命令
        response = self.udp_client.send_command("GET_POST_PROCESS_STATE", {"post_process_id": post_process_id})
        if response.get("status") == "success":
            # 更新后处理状态
            self.update_state({"post_processes": {post_process_id: response.get("data", {})}})
        
        return self._device_state.post_processes.get(post_process_id)
    
    def update_state(self, state_data: Dict[str, Any]) -> None:
        """
        更新设备状态
        
        Args:
            state_data: 状态数据字典
        """
        if not state_data:
            return
        
        # 更新设备基本状态
        if "connected" in state_data:
            self._device_state.connected = state_data["connected"]
        if "operation_mode" in state_data:
            self._device_state.operation_mode = state_data["operation_mode"]
        if "device_status" in state_data:
            self._device_state.device_status = state_data["device_status"]
        if "error_message" in state_data:
            self._device_state.error_message = state_data["error_message"]
        if "solution_add_status" in state_data:
            self._device_state.solution_add_status = state_data["solution_add_status"]
        if "current_solution_id" in state_data:
            self._device_state.current_solution_id = state_data["current_solution_id"]
        if "current_volume" in state_data:
            self._device_state.current_volume = state_data["current_volume"]
        if "target_volume" in state_data:
            self._device_state.target_volume = state_data["target_volume"]
        if "current_reactor_id" in state_data:
            self._device_state.current_reactor_id = state_data["current_reactor_id"]
        
        # 更新反应器状态
        if "reactors" in state_data:
            for reactor_id, reactor_state_data in state_data["reactors"].items():
                reactor_id = int(reactor_id)
                # 如果反应器不存在，创建新的ReactorState对象
                if reactor_id not in self._device_state.reactors:
                    self._device_state.reactors[reactor_id] = ReactorState(reactor_id=reactor_id)
                
                # 更新反应器状态属性
                reactor = self._device_state.reactors[reactor_id]
                for key, value in reactor_state_data.items():
                    if hasattr(reactor, key):
                        setattr(reactor, key, value)
        
        # 更新后处理系统状态
        if "post_processes" in state_data:
            for post_process_id, post_process_state_data in state_data["post_processes"].items():
                post_process_id = int(post_process_id)
                # 如果后处理系统不存在，创建新的PostProcessState对象
                if post_process_id not in self._device_state.post_processes:
                    self._device_state.post_processes[post_process_id] = PostProcessState(post_process_id=post_process_id)
                
                # 更新后处理系统状态属性
                post_process = self._device_state.post_processes[post_process_id]
                for key, value in post_process_state_data.items():
                    if hasattr(post_process, key):
                        setattr(post_process, key, value)
        
        # 更新最后更新时间
        self._device_state.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"设备状态已更新: {self._device_state}")
    
    def _handle_status_update(self, state_data: Dict[str, Any]) -> None:
        """
        处理UDP服务器主动推送的状态更新
        
        Args:
            state_data: 状态数据字典
        """
        self.update_state(state_data)

    # ====================== 指令集实现 ======================
    def _send_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """
        发送命令的通用方法
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            bool: 命令执行成功返回True，否则返回False
        """
        if not self.connected:
            logger.error("设备未连接，无法发送命令")
            return False
        
        response = self.udp_client.send_command(command, params)
        
        # 对于异步命令（长时间运行命令），发送成功即返回True
        # 对于同步命令，等待并检查响应状态
        if response.get("type") == "async":
            # 异步命令，发送成功即返回True
            logger.info(f"异步命令已发送: {command}, 等待状态更新")
            return True
        
        # 更新设备状态（无论命令是否成功，都更新状态）
        self._get_device_state()
        
        if response.get("status") == "success":
            return True
        else:
            logger.error(f"命令执行失败: {command}, 错误: {response.get('message')}")
            return False

    # ========== 移液操作指令集 ==========
    def reactor_solution_add(self, solution_id: int, volume: float, reactor_id: int) -> bool:
        """
        向反应器添加溶液
        
        Args:
            solution_id: 溶液编号
            volume: 加入体积
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "solution_id": solution_id,
            "volume": volume,
            "reactor_id": reactor_id
        }
        return self._send_command("REACTOR_SOLUTION_ADD", params)

    def post_process_solution_add(self, start_bottle: str, end_bottle: str, volume: float, 
                                 inject_speed: float, suck_speed: float = 4.0) -> bool:
        """
        后处理溶液转移
        
        Args:
            start_bottle: 出发瓶
            end_bottle: 终点瓶
            volume: 加入体积
            inject_speed: 注入速度
            suck_speed: 吸入速度，默认4.0
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "start_bottle": start_bottle,
            "end_bottle": end_bottle,
            "volume": volume,
            "inject_speed": inject_speed,
            "suck_speed": suck_speed
        }
        return self._send_command("POST_PROCESS_SOLUTION_ADD", params)

    def post_process_clean(self, post_process_id: int) -> bool:
        """
        自动清洗程序
        
        Args:
            post_process_id: 后处理编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "post_process_id": post_process_id
        }
        return self._send_command("POST_PROCESS_CLEAN", params)

    # ========== 反应器操作指令集 ==========
    def reactor_n2_on(self, reactor_id: int) -> bool:
        """
        打开反应器氮气
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id
        }
        return self._send_command("REACTOR_N2_ON", params)

    def reactor_n2_off(self, reactor_id: int) -> bool:
        """
        关闭反应器氮气
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id
        }
        return self._send_command("REACTOR_N2_OFF", params)

    def reactor_air_on(self, reactor_id: int) -> bool:
        """
        打开反应器空气
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id
        }
        return self._send_command("REACTOR_AIR_ON", params)

    def reactor_air_off(self, reactor_id: int) -> bool:
        """
        关闭反应器空气
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id
        }
        return self._send_command("REACTOR_AIR_OFF", params)

    def temp_set(self, reactor_id: int, temperature: float) -> bool:
        """
        设置温度
        
        Args:
            reactor_id: 反应器编号
            temperature: 温度
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id,
            "temperature": temperature
        }
        return self._send_command("TEMP_SET", params)

    # ========== 搅拌器操作指令集 ==========
    def start_reactor_stirrer(self, reactor_id: int, speed: float) -> bool:
        """
        启动反应器搅拌器
        
        Args:
            reactor_id: 反应器编号
            speed: 转速
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id,
            "speed": speed
        }
        return self._send_command("START_STIR", params)

    def stop_reactor_stirrer(self, reactor_id: int) -> bool:
        """
        停止反应器搅拌器
        
        Args:
            reactor_id: 反应器编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "reactor_id": reactor_id
        }
        return self._send_command("STOP_STIR", params)

    # ========== 后处理排液操作指令集 ==========
    def post_process_discharge_on(self, post_process_id: int) -> bool:
        """
        打开后处理排液
        
        Args:
            post_process_id: 后处理编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "post_process_id": post_process_id
        }
        return self._send_command("POST_PROCESS_DISCHARGE_ON", params)

    def post_process_discharge_off(self, post_process_id: int) -> bool:
        """
        关闭后处理排液
        
        Args:
            post_process_id: 后处理编号
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "post_process_id": post_process_id
        }
        return self._send_command("POST_PROCESS_DISCHARGE_OFF", params)

    # ========== 其他指令 ==========
    def wait(self, seconds: int) -> bool:
        """
        等待指定时间
        
        Args:
            seconds: 等待时间（秒）
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        params = {
            "seconds": seconds
        }
        return self._send_command("WAIT", params)

    # ====================== 设备状态查询 ======================
    # ====================== 任务管理方法 ======================
    def register_task(self, command: str, params: Dict[str, Any] = None) -> str:
        """
        注册一个新任务
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            str: 任务ID
        """
        return self.udp_client.register_task(command, params)
    
    def set_task_callback(self, task_id: str, callback) -> bool:
        """
        设置任务的回调函数
        
        Args:
            task_id: 任务ID
            callback: 回调函数，格式: callback(task_id, status, data)
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        return self.udp_client.set_task_callback(task_id, callback)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        return self.udp_client.get_task_status(task_id)
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有任务信息
        """
        return self.udp_client.get_all_tasks()
    
    def clear_task(self, task_id: str) -> bool:
        """
        清除任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        return self.udp_client.clear_task(task_id)
    
    def clear_all_tasks(self) -> None:
        """
        清除所有任务信息
        """
        self.udp_client.clear_all_tasks()
    
    @property
    def device_status(self) -> Dict[str, Any]:
        """
        获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态信息
        """
        # 获取最新设备状态
        self._get_device_state()
        
        # 将DeviceState对象转换为字典
        status_dict = asdict(self._device_state)
        
        # 添加额外的设备信息
        status_dict.update({
            "address": self.udp_client.address,
            "port": self.udp_client.port
        })
        
        # 如果是调试模式，覆盖相关状态
        if self.debug_mode:
            status_dict.update({
                "status": "debug",
                "connected": True
            })
        else:
            # 更新连接状态
            status_dict["connected"] = self.connected
        
        return status_dict