import os

from mchplnet.interfaces.uart import LNetSerial

from pyx2cscope.xc2scope import X2CScope
from tests import data
from tests.utils.SerialStub import SerialStub

elf_file = os.path.join(
    os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
)


def test_x2cscope_install_serial(mocker):
    serial_stub = SerialStub()
    mocker.patch.object(LNetSerial, "start", serial_stub.LNetSerial_start)
    mocker.patch.object(LNetSerial, "write", serial_stub.LNetSerial_write)
    mocker.patch.object(LNetSerial, "read", serial_stub.LNetSerial_read)
    pyx2cscope = X2CScope(elf_file=elf_file, port="COM11")
    # TODO: check if device_info and scope data are correct
    device_info = pyx2cscope.lnet.device_info

    scope_data = pyx2cscope.lnet.scope_data
