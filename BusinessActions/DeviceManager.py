from UIInteraction.ParameterManagement.ParameterStorage import ParameterStorage


class DeviceManager:
    def __init__(self, parameter_storage: ParameterStorage):
        self.parameter_storage = parameter_storage
        self.simulation_mode = False

    def stop_monitor_thread(self):
        pass

    def toggle_simulation_mode(self):
        self.simulation_mode = not self.simulation_mode
        print(f"仿真模式已{'开启' if self.simulation_mode else '关闭'}")
        return self.simulation_mode
