"""Execute unit tests related to the parser class for 16 and 32 bits."""
import os

from pyx2cscope.xc2scope import X2CScope
from tests import data
from tests.utils.serial_stub import fake_serial


class TestParser:
    """Parser related unit tests."""
    elf_file_16 = os.path.join(os.path.dirname(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf")
    elf_file_32 = os.path.join(os.path.dirname(data.__file__), "qspin_foc_same54.elf")

    def test_variable_does_not_exist(self, mocker):
        """Given a valid 16 bit elf file, check if an invalid variable outputs the expected behavior."""
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("wrong_variable_name")
        assert variable is None

    def test_array_variable_16(self, mocker):
        """Given a valid 16 bit elf file, check if an array variable is read correctly."""
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("motor.estimator.zsmt.iqHistory")
        assert variable is not None, "variable name not found"
        assert variable.is_array() is True, "variable should be an array"
        assert len(variable) == 4, "array has wrong length" # noqa: PLR2004

    # def test_array_variable_32(self, mocker):
    #     """Given a valid 16 bit elf file, check if an array variable is read correctly."""
    #     fake_serial(mocker, 32)
    #     x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_32)
    #     variable = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.duty")
    #     assert variable is not None, "variable name not found"
    #     assert variable.is_array() == True, "variable should be an array"
    #     assert len(variable) == 3, "array has wrong length"
