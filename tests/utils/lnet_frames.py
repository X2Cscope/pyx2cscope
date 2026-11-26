"""Build valid LNet v5 response frames for tests.

Frames follow LNet v5 (LCM) and the X2Cscope LNet profile
(X2Cscope_library_make: doc/lnet/x2cscope_lnet_profile.md): SYN 0x55, SIZE, NODE, data, checksum,
with a 0x00 fill byte after every 0x55/0x02 in SIZE, NODE and data.
"""

RESERVED = (0x55, 0x02)


def lnet_response(service_id: int, data: bytes = b"", error_id: int = 0x00, node: int = 0x01) -> bytearray:
    """Return a raw response frame: SYN, SIZE, NODE, Service ID, Error ID, data, checksum."""
    payload = bytes([0x55, len(data) + 2, node, service_id, error_id]) + bytes(data)
    raw = bytearray([0x55])
    for byte in payload[1:]:
        raw.append(byte)
        if byte in RESERVED:
            raw.append(0x00)
    checksum = sum(payload) & 0xFF
    if checksum in RESERVED:
        checksum = (~checksum) & 0xFF
    raw.append(checksum)
    return raw


def device_info_response(processor_id: int = 0x8210, max_frame_size: int = 255) -> bytearray:
    """Return a Get Device Info (0x00) response (profile section 5.1)."""
    data = (
        (5).to_bytes(2, "little")  # monitor version (LNet v5)
        + (1).to_bytes(2, "little")  # application version
        + bytes([max_frame_size])
        + processor_id.to_bytes(2, "little")
        + b"Jan012024" + b"1200"  # monitor date (MmmDDYYYY) and time (HHMM)
        + b"Jan012024" + b"1200"  # application date and time
        + bytes([0x01])  # DSP state: application running
        + (0).to_bytes(2, "little")  # event type
        + (0).to_bytes(4, "little")  # event ID
        + (0).to_bytes(4, "little")  # TableStruct address
    )
    return lnet_response(0x00, data)


def load_parameter_response(state: int = 0, channels: int = 0, array_size: int = 5000,
                            scope_version: int = 2) -> bytearray:
    """Return a Load Parameter (0x11) response for the scope block (profile section 6.1)."""
    data = (
        bytes([state, channels])
        + (0).to_bytes(2, "little")  # sample time prescaler
        + (0).to_bytes(4, "little")  # offline pointer
        + (0).to_bytes(4, "little")  # scope buffer address
        + (0).to_bytes(4, "little")  # trigger delay
        + (0).to_bytes(4, "little")  # trigger event position
        + array_size.to_bytes(4, "little")  # used length
        + array_size.to_bytes(4, "little")  # scope buffer size
        + bytes([0x80 + scope_version])
    )
    return lnet_response(0x11, data)
