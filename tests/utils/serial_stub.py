"""This module contain the implementation of SerialStub and connection functions.

This module is to be used by the Mocker to fake a working serial connection with either 16 or 32 bit devices.
"""
import time

from mchplnet.interfaces.uart import LNetSerial
from mchplnet.lnetframe import LNetFrame

BIT_LENGTH_16 = 16
BIT_LENGTH_32 = 32

class FrameBuilder(LNetFrame):
    """FrameBuilder class to build LNet frames."""

    def _get_data(self):
        no_error = 0x00
        return self.data.extend([self.service_id, no_error, *self.value])

    def __init__(self, service_id: int, uc_width: int, value: None|bytes):

        super().__init__()
        self.service_id = service_id
        self.uc_width = uc_width
        self.value = bytearray() if value is None else value

    def _deserialize(self):
        uc_width = 2 if self.uc_width == BIT_LENGTH_16 else 4  # 16-bit or 32-bit address
        if self.service_id == 0x0A:
            # Frame format: [SYNC(1)][SIZE(1)][NODE(1)][SERVICE_ID(1)=0x0A][ADDR(2/4)][SIZE(1)][DATA(N)][CRC(2)]
            frame = self.received
            addr_start = 4
            addr_end = addr_start + uc_width
            addr = int.from_bytes(frame[addr_start:addr_end], 'little')

            # Extract the value from the frame
            value_start = addr_end + 1
            value_bytes = frame[value_start:-1]  # Exclude CRC
            value = int.from_bytes(value_bytes, 'little')
            return addr, value
        if self.service_id == 0x09:
            # Extract address and size from the frame
            # Frame format: [SYNC(1)][SIZE(1)][NODE(1)][SERVICE_ID(1)=0x09][ADDR(2/4)][SIZE(1)][TYPE(1)][CRC(2)]
            frame = self.received
            addr_start = 4
            addr_end = addr_start + uc_width
            addr = int.from_bytes(frame[addr_start:addr_end], 'little')
            size = frame[addr_end]
            return addr, size
        return 0, 0

    def _check_frame_protocol(self):
        return True

class SerialStub:
    """Fakes a serial connection for 16 and 32 bit devices."""

    def __init__(self, uc_width=BIT_LENGTH_16):
        """Constructor of the SerialStub class.

        Expected get_device_info and load_param bytestream are initialized here.
        """
        self.delay_seconds = 0.2  # 200ms delay to make concurrency
        self.uc_width = uc_width
        self.data = bytearray()
        self.device_info = bytearray(b"\x55\x01\x01\x00\x57")
        self.load_param = bytearray(b"\x55\x03\x01\x11\x01\x00\x6b")

        # Mock memory for RAM operations
        # Default value for hardwareUiEnabled at address 0x1000
        self.mock_memory = {0x1000: 0}


    def lnet_serial_start(self):
        """Mocker for the start interface function.

        As we are dealing with no real device, we just return.
        """
        return

    def _get_ram(self):
        """Handle a get_ram request."""
        time.sleep(self.delay_seconds)  # Simulate operation delay
        frame_builder = FrameBuilder(0x09, self.uc_width, None)
        frame_builder.received = self.data
        addr, size = frame_builder.deserialize()# 16-bit or 32-bit address

        # Get the value from mock memory or return 0 if not found
        value = self.mock_memory.get(addr, 0)

        # Convert to bytes based on size
        value_bytes = value.to_bytes(size, 'little')

        # Create response frame with the value
        frame_builder = FrameBuilder(0x09, self.uc_width, value_bytes)
        return frame_builder.serialize()

    def _put_ram(self):
        """Handle a put_ram request."""
        time.sleep(self.delay_seconds)  # Simulate operation delay
        frame_builder = FrameBuilder(0x0A, self.uc_width, None)
        frame_builder.received = self.data
        addr, value = frame_builder.deserialize()

        # Store the value in mock memory
        self.mock_memory[addr] = value

        # Return success response (just the service ID and success status)
        return frame_builder.serialize()

    def lnet_serial_write(self, buffer: bytearray):
        """Assert the received byte stream with implemented LNET functions."""
        self.data = buffer

    def _get_lnet_service_id(self):
        if len(self.data) >= 5:  # Minimum frame size
            return self.data[3] if len(self.data) > 3 else 0
        return 0

    def lnet_serial_read(self) -> bytearray:
        """Return the respective expected byte stream according to the previous received command."""
        service_id = self._get_lnet_service_id()
        service = {
            0x00: self._get_device_info,
            0x11: self._get_load_param,
            0x09: self._get_ram,
            0x0A: self._put_ram
        }
        return service.get(service_id, self._get_device_info)()

    def _get_device_info(self):
        if self.data != self.device_info:
            raise ValueError("Wrong Device Info package format!")
        if self.uc_width == BIT_LENGTH_16:
            return bytearray(
                b"\x55.\x01\x00\x00\x05\x00\x01\x00\xff\x10\x82Nov2320231500\x00\x00\x00\x00"
                b"\x00\x00\xccJ\x14K\xc0\xff\xff\x01\x00\x00\x00\x00\x00\x00\xf4R\x00\x00\xba"
            )
        elif self.uc_width == BIT_LENGTH_32:
            return bytearray(
                b"\x55.\x01\x00\x00\x05\x00\x01\x00\xff \x82Mar 320191220Mar 320191220\x01"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00 T"
            )
        else:
            raise ValueError("Mocker fake_serial: wrong uC width! should be either 16 or 32 bits")

    def _get_load_param(self) -> bytearray:
        if self.data != self.load_param:
            raise ValueError("Wrong Load Parameter package format!")
        if self.uc_width == BIT_LENGTH_16:
            return bytearray(
                b"\x55\x1f\x01\x11\x00\x00\x04\x00\x00\x98:\x00\x004\x10\x00\x00\xe0\x05\x00"
                b"\x00\x00\x00\x00\x00\x98:\x00\x00\x98:\x00\x00\x82\xab"
            )
        elif self.uc_width == BIT_LENGTH_32:
            return bytearray(
                b"\x55\x1f\x01\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa8\x00\x00 \x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00 \x00\x00\x82\x10"
            )
        else:
            raise ValueError("Mocker fake_serial: wrong uC width! should be either 16 or 32 bits")

def fake_serial(mocker, uc_width=BIT_LENGTH_16):
    """Fakes a serial port for 16/32 bit devices.

    The methods being faked by this function are start, read and write.

    Args:
        mocker: Mocker inheritance
        uc_width: bit size of the device to be mocked
    Return:
        None
    """
    serial_stub = SerialStub(uc_width=uc_width)
    mocker.patch.object(LNetSerial, "start", serial_stub.lnet_serial_start)
    mocker.patch.object(LNetSerial, "write", serial_stub.lnet_serial_write)
    mocker.patch.object(LNetSerial, "read", serial_stub.lnet_serial_read)
