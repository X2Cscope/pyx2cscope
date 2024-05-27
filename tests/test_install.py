"""Integration test to check if after install, PyX2CScope outputs the expected behavior."""
import os

from mchplnet.services.frame_device_info import DeviceInfo
from mchplnet.services.frame_load_parameter import LoadScopeData
from pyx2cscope.xc2scope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial

elf_file_16 = os.path.join(os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")
elf_file_32 = os.path.join(os.path.dirname(data.__file__), "qspin_foc_same54.elf")

PROCESSOR_16_BIT_LENGTH = 2
PROCESSOR_32_BIT_LENGTH = 4

def test_x2cscope_install_serial_16(mocker):
    """Using a fake serial interface with a 16 bit device, check the device_info and scope_data frames."""
    fake_serial(mocker, 16)
    pyx2cscope = X2CScope(elf_file=elf_file_16, port="COM11")
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    assert device_info.uc_width == PROCESSOR_16_BIT_LENGTH, "wrong processor bit length"
    assert device_info.processor_id == "__GENERIC_MICROCHIP_DSPIC__", "unknown processor"
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data
    assert scope_data.scope_state == 0, "wrong scope state value"
    assert scope_data.data_array_size == 15000, "wrong scope data size" # noqa: PLR2004


def test_x2cscope_install_serial_32(mocker):
    """Using a fake serial interface with a 32 bit device, check the device_info and scope_data frames."""
    fake_serial(mocker, 32)
    pyx2cscope = X2CScope(elf_file=elf_file_32, port="COM11")
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    assert device_info.uc_width == PROCESSOR_32_BIT_LENGTH, "wrong processor bit length"
    assert device_info.processor_id == "__GENERIC_MICROCHIP_PIC32__", "unknown processor"
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data
    assert scope_data.scope_state == 0, "wrong scope state value"
    assert scope_data.data_array_size == 8192, "wrong scope array size" # noqa: PLR2004
