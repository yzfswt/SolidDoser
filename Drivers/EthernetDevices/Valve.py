
from Drivers.EthernetDevices.SRND_16_IO import SRND_16_IO


class Valve:
    def __init__(self, io_control: SRND_16_IO,address:int):
        self.io_control=io_control
        self.address=address
    def open(self):
        self.io_control.write_io_coil(self.address,True)
    def close(self):
        self.io_control.write_io_coil(self.address,False)
    def change_state(self):
        current_state = self.io_control.read_io_coil(self.address)
        self.io_control.write_io_coil(self.address, not current_state)
    def get_state(self):
        return self.io_control.read_io_coil(self.address)
