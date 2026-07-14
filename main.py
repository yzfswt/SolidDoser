from PySide6.QtWidgets import QApplication

from UIInteraction.UIGenerator.MainUI import MainUI

from Common.ActionLogger import get_action_logger

from BusinessActions.DeviceManager import DeviceManager

from PySide6.QtCore import QObject, Signal

import sys

from UIInteraction.ControlActions.ButtonActionManager import ButtonActionManager

from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

from BusinessActions.UIFeedback.UIFeedbackHandler import UIFeedbackHandler

from UDP_recivecmd import UDPSignalReceiver

from ActionSequence.execute_sequence import Import_Process_UDP, Import_Parament_UDP, Import_Process_By_Path_UDP

import socket

import json





class UdpCommandBridge(QObject):

    """将 UDP 线程命令桥接到 Qt 主线程执行。"""



    execute_process_requested = Signal()





def send_udp_response(host, port, message):

    try:

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        json_message = json.dumps(message, ensure_ascii=False)

        udp_socket.sendto(json_message.encode("utf-8"), (host, port))

        print(f"✅ 已发送UDP响应到 {host}:{port}: {json_message}")

        udp_socket.close()

        return True

    except Exception as e:

        print(f"❌ 发送UDP响应失败: {e}")

        return False



if __name__ == "__main__":

    app = QApplication(sys.argv)

    get_action_logger().record("应用启动")



    main_window = MainUI()

    param_storage = ParameterStorage()

    main_window.bind_solid_doser_motion_debug(param_storage)

    ui_feedback = UIFeedbackHandler(main_window)

    device_manager = DeviceManager(param_storage)

    button_manager = ButtonActionManager(main_window, device_manager, param_storage, ui_feedback)



    main_window.setWindowTitle("SolidDoser 控制软件")

    main_window.show()



    udp_receiver = UDPSignalReceiver(host="127.0.0.1", port=8888)



    def on_udp_import_process(message=None):

        get_action_logger().record("UDP：工艺流程导入触发")

        Import_Process_UDP(main_window.table_process)



    udp_receiver.set_signal_handler(on_udp_import_process)

    udp_receiver.start_listening()



    udp_receiver2 = UDPSignalReceiver(host="0.0.0.0", port=8889)



    def create_response_sender():

        def send_response(message=None):

            if message is None:

                return send_udp_response("127.0.0.1", udp_receiver2.back_port, {"status": "success"})

            return send_udp_response("127.0.0.1", udp_receiver2.back_port, message)

        return send_response



    response_sender = create_response_sender()

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

        if message:

            stripped_message = str(message).strip()

            if stripped_message.startswith("IMPORT_PROCESS_FILE(") and stripped_message.endswith(")"):

                path_param = stripped_message[len("IMPORT_PROCESS_FILE("):-1].strip()

                result = Import_Process_By_Path_UDP(main_window.table_process, path_param)

                response = {

                    "status": "success" if result.get("success") else "error",

                    "command": "IMPORT_PROCESS_FILE",

                    "message": result.get("message", ""),

                    "steps_count": result.get("steps_count", 0),

                }

                response_sender(response)

                return

            if stripped_message == "EXECUTE_PROCESS_FILE":

                try:

                    udp_bridge.execute_process_requested.emit()

                    response_sender({

                        "status": "success",

                        "command": "EXECUTE_PROCESS_FILE",

                        "message": "已触发工艺流程执行",

                    })

                except Exception as e:

                    response_sender({

                        "status": "error",

                        "command": "EXECUTE_PROCESS_FILE",

                        "message": f"触发执行失败：{e}",

                    })

                return

        Import_Parament_UDP(message, device_manager, response_sender)



    udp_receiver2.set_signal_handler(on_udp_param)

    udp_receiver2.start_listening()



    def on_app_about_to_quit():

        udp_receiver.stop_listening()

        udp_receiver2.stop_listening()

        get_action_logger().persist()



    app.aboutToQuit.connect(on_app_about_to_quit)

    sys.exit(app.exec())

