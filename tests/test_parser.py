import os

import data
import pytest

from pyx2cscope.xc2scope import X2CScope


class TestParser:
    elf_file_16 = os.path.join(
        os.path.abspath(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf"
    )
    elf_file_32 = os.path.join(
        os.path.abspath(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    )

    def test_array_variable_16(self):
        x2cScope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2cScope.get_variable("motor.estimator.zsmt.iqHistory")
        assert variable.is_array() == True
        assert variable.get_length() == 4

    def test_array_variable_32(self):
        x2cScope = X2CScope(port="COM14", elf_file=self.elf_file_32)
        variable = x2cScope.get_variable("motor.estimator.zsmt.iqHistory")
        assert variable.is_array() == True
        assert variable.get_length() == 4
