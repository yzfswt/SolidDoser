"""SolidDoser 轻量启动：流程导入 + 调试。"""
import logging
import sys

from PySide6.QtWidgets import QApplication

from BusinessActions.DeviceManager import DeviceManager
from BusinessActions.UIFeedback.UIFeedbackHandler import UIFeedbackHandler
from UIInteraction.ControlActions.ButtonActionManager import ButtonActionManager
from UIInteraction.UIGenerator.MainUI import MainUI
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainUI()
    param_storage = ParameterStorage()
    main_window.bind_solid_doser_motion_debug(param_storage)
    ui_feedback = UIFeedbackHandler(main_window)
    device_manager = DeviceManager(param_storage)
    ButtonActionManager(main_window, device_manager, param_storage, ui_feedback)
    main_window.setWindowTitle("SolidDoser 控制软件")
    main_window.show()
    sys.exit(app.exec())
