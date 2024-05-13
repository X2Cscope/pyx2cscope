import os

import pytest

from pyx2cscope.xc2scope import X2CScope
from tests import data
from tests.utils.SerialStub import fake_serial


class TestPyX2CScope:
    elf_file = os.path.join(os.path.abspath(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")

    def test_missing_elf_file_16(self, mocker):
        # with pytest.raises(ValueError, match=r"elf_file"):
        fake_serial(mocker, 16)
        with pytest.raises(Exception, match=r"Error loading ELF file"):
            X2CScope(elf_file="wrong_elf_file.elf", port="COM0")

    def test_missing_elf_file_32(self, mocker):
        # with pytest.raises(ValueError, match=r"elf_file"):
        fake_serial(mocker, 32)
        with pytest.raises(Exception, match=r"Error loading ELF file"):
            X2CScope(elf_file="wrong_elf_file.elf", port="COM0")

    def test_missing_com_port(self):
        with pytest.raises(ValueError, match=r"SERIAL: port"):
            X2CScope(elf_file=self.elf_file)

    def test_wrong_com_port(self):
        with pytest.raises(RuntimeError, match=r"Failed to retrieve device information"):
            X2CScope(elf_file=self.elf_file, port="COM0")
