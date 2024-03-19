import os

import data
import pytest

from pyx2cscope.xc2scope import X2CScope


class TestPyX2CScope:
    elf_file = os.path.join(
        os.path.abspath(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    )

    def test_missing_elf_file(self):
        with pytest.raises(TypeError, match=r"elf_file"):
            pyx2cscope = X2CScope()

    def test_missing_com_port(self):
        with pytest.raises(ValueError, match=r"SERIAL: port"):
            pyx2cscope = X2CScope(elf_file=self.elf_file)

    def test_wrong_com_port(self):
        with pytest.raises(
            RuntimeError, match=r"Failed to retrieve device information"
        ):
            pyx2cscope = X2CScope(elf_file=self.elf_file, port="COM0")
