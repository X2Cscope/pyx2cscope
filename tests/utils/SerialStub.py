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

    def LNetSerial_read(self) -> bytearray:
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
