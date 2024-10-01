"""This module contain the implementation of SerialStub and connection functions.

This module is to be used by the Mocker to fake a working serial connection with either 16 or 32 bit devices.
"""

from mchplnet.interfaces.uart import LNetSerial

BIT_LENGTH_16 = 16
BIT_LENGTH_32 = 32


class SerialStub:
    """Fakes a serial connection for 16 and 32 bit devices."""

    def __init__(self):
        """Constructor of the SerialStub class.

        Expected get_device_info and load_param bytestream are initialized here.
        """
        self.data = bytearray()
        self.get_device_info = bytearray(b"\x55\x01\x01\x00\x57")
        self.load_param = bytearray(b"\x55\x03\x01\x11\x01\x00\x6b")

    def lnet_serial_start(self):
        """Mocker for the start interface function.

        As we are dealing with no real device, we just return.
        """
        return

    def lnet_serial_write(self, buffer: bytearray):
        """Assert the received byte stream with implemented LNET functions."""
        self.data = buffer
        if self.data == self.get_device_info:
            return
        if self.data == self.load_param:
            return
        assert False, "Wrong message was sent to device"

    def lnet_serial_read16(self) -> bytearray:
        """Return the respective expected byte stream according to the previous received command."""
        # Start of frame, Data frame size
        if self.data == self.get_device_info:
            return bytearray(
                b"\x55.\x01\x00\x00\x05\x00\x01\x00\xff\x10\x82Nov2320231500\x00\x00\x00\x00"
                b"\x00\x00\xccJ\x14K\xc0\xff\xff\x01\x00\x00\x00\x00\x00\x00\xf4R\x00\x00\xba"
            )
        elif self.data == self.load_param:
            return bytearray(
                b"\x55\x1f\x01\x11\x00\x00\x04\x00\x00\x98:\x00\x004\x10\x00\x00\xe0\x05\x00"
                b"\x00\x00\x00\x00\x00\x98:\x00\x00\x98:\x00\x00\x82\xab"
            )
        assert False, "Unexpected message received"

    def lnet_serial_read32(self) -> bytearray:
        """Return the respective expected byte stream according to the previous received command."""
        # Start of frame, Data frame size
        if self.data == self.get_device_info:
            return bytearray(
                b"\x55.\x01\x00\x00\x05\x00\x01\x00\xff \x82Mar 320191220Mar 320191220\x01"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00 T"
            )
        elif self.data == self.load_param:
            return bytearray(
                b"\x55\x1f\x01\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa8\x00\x00 \x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00 \x00\x00\x82\x10"
            )
        assert False, "Unexpected message received"


def fake_serial(mocker, uc_width=BIT_LENGTH_16):
    """Fakes a serial port for 16/32 bit devices.

    The methods being faked by this function are start, read and write.

    Args:
        mocker: Mocker inheritance
        uc_width: bit size of the device to be mocked
    Return:
        None
    """
    serial_stub = SerialStub()
    mocker.patch.object(LNetSerial, "start", serial_stub.lnet_serial_start)
    mocker.patch.object(LNetSerial, "write", serial_stub.lnet_serial_write)
    if uc_width == BIT_LENGTH_16:
        mocker.patch.object(LNetSerial, "read", serial_stub.lnet_serial_read16)
    elif uc_width == BIT_LENGTH_32:
        mocker.patch.object(LNetSerial, "read", serial_stub.lnet_serial_read32)
    else:
        raise ValueError(
            "Mocker fake_serial: wrong uC width! should be either 16 or 32 bits"
        )
