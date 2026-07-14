from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from UIInteraction.UIGenerator.MainUI import MainUI


class UIFeedbackHandler(QObject):
    def __init__(self, main_window: MainUI):
        super().__init__()
        self.main_window = main_window

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self.main_window, title, message)
