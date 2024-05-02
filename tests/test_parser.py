import os

from tests import data

from pyx2cscope.xc2scope import X2CScope
from tests.utils.SerialStub import fake_serial



class TestParser:

    elf_file_16 = os.path.join(
        os.path.dirname(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf"
    )
    elf_file_32 = os.path.join(
        os.path.dirname(data.__file__), "qspin_foc_same54.elf"
    )

    def test_variable_does_not_exist(self, mocker):
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("wrong_variable_name")
        assert variable is None

    def test_array_variable_16(self, mocker):
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("motor.estimator.zsmt.iqHistory")
        assert variable is not None, "variable name not found"
        assert variable.is_array() == True, "variable should be an array"
        assert len(variable) == 4, "array has wrong length"

    def test_array_variable_32(self, mocker):
        fake_serial(mocker, 32)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_32)
        variable = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.duty")
        assert variable is not None, "variable name not found"
        assert variable.is_array() == True, "variable should be an array"
        assert len(variable) == 3, "array has wrong length"