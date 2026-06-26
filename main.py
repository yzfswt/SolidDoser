from PySide6.QtWidgets import QApplication
from UIInteraction.UIGenerator.MainUI import MainUI
from Common.ActionLogger import get_action_logger
from UIInteraction.ControlActions.InputActionManager import InputActionManager
from BusinessActions.DeviceManager import DeviceManager
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import QTimer, Qt, QObject, Signal
import sys
from UIInteraction.ControlActions.ButtonActionManager import ButtonActionManager
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage
from BusinessActions.UIFeedback.UIFeedbackHandler import UIFeedbackHandler
from UIInteraction.ControlActions.DisplayActionManager import DisplayActionManager
from UIInteraction.RealTimeUpdate.RealTimeUpdate import RealTimeUpdate
from UDP_recivecmd import UDPSignalReceiver
from ActionSequence.execute_sequence import Import_Process_UDP, Import_Parament_UDP, Import_Process_By_Path_UDP
import socket
import json


class UdpCommandBridge(QObject):
    """将 UDP 线程命令桥接到 Qt 主线程执行。"""

    execute_process_requested = Signal()


def send_udp_response(host, port, message):
    """
    发送UDP响应消息
    
    :param host: 目标主机地址
    :param port: 目标端口
    :param message: 要发送的消息字典
    """
    try:
        # 创建UDP套接字
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 将消息转换为JSON字符串并编码
        json_message = json.dumps(message, ensure_ascii=False)
        udp_socket.sendto(json_message.encode('utf-8'), (host, port))
        print(f"✅ 已发送UDP响应到 {host}:{port}: {json_message}")
        
        # 关闭套接字
        udp_socket.close()
        return True
    except Exception as e:
        print(f"❌ 发送UDP响应失败: {e}")
        return False

if __name__ == "__main__":
    # 创建应用程序实例
    app = QApplication(sys.argv)
    get_action_logger().record("应用启动")
    
    # 创建MainUI实例
    main_window = MainUI()
    #实例化参数管理器
    param_storage = ParameterStorage()
    main_window.bind_tray_model(param_storage.tray)
    main_window.bind_tip_rack_model(param_storage.tip_rack)
    main_window.bind_robot_debug(param_storage)
    # 实例化UI反馈处理器
    ui_feedback = UIFeedbackHandler(main_window)
    
    device_manager = DeviceManager(param_storage)
    # 实例化输入管理器，验证输入限制效果
    input_manager = InputActionManager(main_window,param_storage)
    # 实例化按钮控件管理器
    button_manager = ButtonActionManager(main_window,device_manager,param_storage,ui_feedback)
    # 实例化显示动作管理器
    display_manager = DisplayActionManager(main_window, param_storage, button_manager)
    # 实例化实时更新实例
    real_time_update = RealTimeUpdate(device_manager,param_storage)
    
    # 设置窗口标题
    main_window.setWindowTitle("SolidDoser 控制软件")
    
    # 显示窗口
    main_window.show()
    # 建立udp监听
    udp_receiver = UDPSignalReceiver(host="127.0.0.1", port=8888)
    # 设置信号处理函数
    def on_udp_import_process(message=None):
        get_action_logger().record("UDP：工艺流程导入触发")
        Import_Process_UDP(main_window.table_process)

    udp_receiver.set_signal_handler(on_udp_import_process)
    # 启动监听
    udp_receiver.start_listening()
    #建立第二个UDP监听线程
    udp_receiver2 = UDPSignalReceiver(host="0.0.0.0", port=8889)
    # 创建一个闭包函数，预先设定send_udp_response的参数
    def create_response_sender():
        def send_response(message=None):
            if message is None:
                # 如果没有提供消息，发送默认响应
                return send_udp_response("127.0.0.1", udp_receiver2.back_port, {"status": "success"})
            else:
                # 如果提供了消息，直接发送该消息
                return send_udp_response("127.0.0.1", udp_receiver2.back_port, message)
        return send_response
    
    # 获取预先设定了参数的闭包函数
    response_sender = create_response_sender()

    # UDP -> Qt 主线程 执行桥
    udp_bridge = UdpCommandBridge()
    udp_bridge.execute_process_requested.connect(button_manager.execute_process_async)
    
    def on_udp_param(message=None):
        if message is not None:
            msg = str(message)
            if len(msg) > 200:
                msg = msg[:200] + "..."
            get_action_logger().record(f"UDP：参数下发 {msg}")
        else:
            get_action_logger().record("UDP：参数下发（OK）")
        # 新增UDP协议：按路径导入工艺文件
        if message:
            stripped_message = str(message).strip()

            if stripped_message.startswith("IMPORT_PROCESS_FILE(") and stripped_message.endswith(")"):
                path_param = stripped_message[len("IMPORT_PROCESS_FILE("):-1].strip()
                result = Import_Process_By_Path_UDP(main_window.table_process, path_param)
                response = {
                    "status": "success" if result.get("success") else "error",
                    "command": "IMPORT_PROCESS_FILE",
                    "message": result.get("message", ""),
                    "steps_count": result.get("steps_count", 0)
                }
                response_sender(response)
                return

            # 新增UDP协议：触发工艺流程执行（等价于点击执行按钮）
            if stripped_message == "EXECUTE_PROCESS_FILE":
                try:
                    # 由 UDP 监听线程发起，转到 Qt 主线程执行
                    udp_bridge.execute_process_requested.emit()
                    response_sender({
                        "status": "success",
                        "command": "EXECUTE_PROCESS_FILE",
                        "message": "已触发工艺流程执行"
                    })
                except Exception as e:
                    response_sender({
                        "status": "error",
                        "command": "EXECUTE_PROCESS_FILE",
                        "message": f"触发执行失败：{e}"
                    })
                return

        Import_Parament_UDP(message, device_manager, response_sender)

    udp_receiver2.set_signal_handler(on_udp_param)
    # 启动监听
    udp_receiver2.start_listening()

    def on_app_about_to_quit():
        udp_receiver.stop_listening()
        udp_receiver2.stop_listening()
        get_action_logger().persist()

    app.aboutToQuit.connect(on_app_about_to_quit)

    # 运行应用程序主循环
    sys.exit(app.exec())
