from UIInteraction.ParameterManagement.BalanceModel import BalanceState
from UIInteraction.ParameterManagement.ScannerModel import ScannerState
from UIInteraction.ParameterManagement.SolidDoserMotionModel import SolidDoserMotionState


class ParameterStorage:
    def __init__(self):
        self.is_local_control = True
        self.is_system_busy = False
        self.process_execution_running = False
        self.process_execution_filename = ""
        self.process_execution_current_step = 0
        self.process_execution_total_steps = 0
        self.process_execution_current_command = ""
        self.solid_doser_motion = SolidDoserMotionState()
        self.scanner = ScannerState()
        self.balance = BalanceState()
