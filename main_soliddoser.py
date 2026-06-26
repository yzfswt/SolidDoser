"""SolidDoser 轻量启动：料盘/枪头架/机器人/清洁工位调试界面。"""
import logging
import sys

from PySide6.QtWidgets import QApplication

from BusinessActions.Robot.studio_dispatch import studio_dispatch_enabled
from Drivers.Robot.hitbot_studio_bridge import get_studio_bridge
from Drivers.SerialServer.zlan5212di_transport import warmup_async
from UIInteraction.UIGenerator.MainUI import MainUI
from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if studio_dispatch_enabled():
        get_studio_bridge().start()
    main_window = MainUI()
    param_storage = ParameterStorage()
    main_window.bind_tray_model(param_storage.tray)
    main_window.bind_tip_rack_model(param_storage.tip_rack)
    main_window.bind_robot_debug(param_storage)
    main_window.bind_cleaning_station_debug(param_storage)
    main_window.setWindowTitle("SolidDoser 控制软件")
    main_window.show()
    warmup_async()
    sys.exit(app.exec())
