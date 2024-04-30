from mchplnet.interfaces.uart import LNetSerial
from mchplnet.services.frame_device_info import FrameDeviceInfo


class SerialStub:
    def __init__(self):
        self.data = bytearray()
        self.get_device_info = bytearray(b"\x55\x01\x01\x00\x57")
        self.load_param = bytearray(b"\x55\x03\x01\x11\x01\x00\x6B")

    def LNetSerial_start(self):
        return

    def LNetSerial_write(self, buffer: bytearray):
        self.data = buffer
        if self.data == self.get_device_info:
            return
        if self.data == self.load_param:
            return
        assert False, "Wrong message was sent to device"

    def LNetSerial_read16(self) -> bytearray:
        # Start of frame, Data frame size
        if self.data == self.get_device_info:
            return bytearray(
                b"\x55\x2E\x01\x00\x00\x04\x00\x00\x00\xFF\x01\x51\x41\x70\x72\x31\x38\x32\x30\x31\x32\x31\x31"
                b"\x35\x35\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x96"
            )
        elif self.data == self.load_param:
            return bytearray(
                b"\x55\x05\x01\x07\x00\x00\x60\x0F\xD1"
            )
        assert False, "Unexpected message received"

    def LNetSerial_read32(self) -> bytearray:
        # Start of frame, Data frame size
        if self.data == self.get_device_info:
            return bytearray(
                b"\x55\x2E\x01\x00\x00\x04\x00\x00\x00\xFF\x01\x51\x41\x70\x72\x31\x38\x32\x30\x31\x32\x31\x31"
                b"\x35\x35\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x96"
            )
        elif self.data == self.load_param:
            return bytearray(b"\x55\x05\x01\x07\x00\x00\x60\x0F\xD1")
        assert False, "Unexpected message received"

def fake_serial(mocker, uc_width=16):
    serial_stub = SerialStub()
    mocker.patch.object(LNetSerial, "start", serial_stub.LNetSerial_start)
    mocker.patch.object(LNetSerial, "write", serial_stub.LNetSerial_write)
    if uc_width == 16:
        mocker.patch.object(LNetSerial, "read", serial_stub.LNetSerial_read16)
        mocker.patch.object(FrameDeviceInfo, "_get_processor_id", return_value=2)
    elif uc_width == 32:
        mocker.patch.object(LNetSerial, "read", serial_stub.LNetSerial_read32)
        mocker.patch.object(FrameDeviceInfo, "_get_processor_id", return_value=4)
    else:
        raise ValueError("Mocker fake_serial: wrong uC width! should be either 16 or 32 bits")
