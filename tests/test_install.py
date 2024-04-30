import os

from mchplnet.services.frame_device_info import DeviceInfo
from mchplnet.services.frame_load_parameter import LoadScopeData
from tests import data
from tests.utils.SerialStub import fake_serial

from pyx2cscope.xc2scope import X2CScope


elf_file_16 = os.path.join(
    os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
)


elf_file_32 = os.path.join(
    os.path.dirname(data.__file__), "qspin_foc_same54.elf"
)


def test_x2cscope_install_serial_16(mocker):
    fake_serial(mocker, 16)
    pyx2cscope = X2CScope(elf_file=elf_file_16, port="COM11")
    # TODO: check if device_info and scope data are correct
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data

def test_x2cscope_install_serial_32(mocker):
    fake_serial(mocker, 32)
    pyx2cscope = X2CScope(elf_file=elf_file_32, port="COM11")
    # TODO: check if device_info and scope data are correct
    device_info: DeviceInfo = pyx2cscope.lnet.device_info
    scope_data: LoadScopeData = pyx2cscope.lnet.scope_data
