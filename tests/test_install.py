import os

import data
import pytest

from pyx2cscope.xc2scope import X2CScope

elf_file = os.path.join(
    os.path.abspath(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
)


def test_x2cscope_install():
    # this test should implement a MOCK of serial port to simulate
    # a working serial communication
    with pytest.raises(RuntimeError, match=r"Failed to retrieve device information"):
        pyx2cscope = X2CScope(elf_file=elf_file, port="COM11")
