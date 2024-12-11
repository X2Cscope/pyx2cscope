"""Execute unit tests related to the parser class for 16 and 32 bits."""

import os

from pyx2cscope.x2cscope import X2CScope
from pyx2cscope.variable.variable_factory import FileType
from tests import data
from tests.utils.serial_stub import fake_serial


class TestParser:
    """Parser related unit tests."""

    elf_file_16 = os.path.join(
        os.path.dirname(data.__file__), "MCAF_ZSMT_dsPIC33CK.elf"
    )
    elf_file_32 = os.path.join(
        os.path.dirname(data.__file__), "qspin_foc_same54.elf"
    )

    elf_file_dspic33ak = os.path.join(
        os.path.dirname(data.__file__), "dsPIC33ak128mc106_foc.elf"
    )

    def test_variable_16_does_not_exist(self, mocker):
        """Given a valid 16 bit elf file, check if an invalid variable outputs the expected behavior."""
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("wrong_variable_name")
        assert variable is None

    def test_variable_32_does_not_exist(self, mocker):
        """Given a valid 32 bit elf file, check if an invalid variable outputs the expected behavior."""
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_32)
        variable = x2c_scope.get_variable("wrong_variable_name")
        assert variable is None

    def test_array_variable_16(self, mocker, array_size_test=4):
        """Given a valid 16 bit elf file, check if an array variable is read correctly."""
        fake_serial(mocker, 16)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_16)
        variable = x2c_scope.get_variable("motor.estimator.zsmt.iqHistory")
        assert variable is not None, "variable name not found"
        assert variable.is_array() is True, "variable should be an array"
        assert len(variable) == array_size_test, "array has wrong length"  # noqa: PLR2004

    def test_array_variable_32(self, mocker, array_size_test=255):
        """Given a valid 32 bit elf file, check if an array variable is read correctly."""
        fake_serial(mocker, 32)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_32)
        variable = x2c_scope.get_variable("bufferLNet")
        assert variable is not None, "variable name not found"
        assert variable.is_array() == True, "variable should be an array"
        assert len(variable) == array_size_test, "array has wrong length"

    def test_variable_dspic33ak(self, mocker, array_size_test=4900):
        """Given a valid dspic33ak elf file, check if an array variable is read correctly."""
        fake_serial(mocker, 32)
        x2c_scope = X2CScope(port="COM14")
        x2c_scope.import_variables(self.elf_file_dspic33ak)
        variable = x2c_scope.get_variable("measureInputs.current.Ia")
        assert variable is not None, "variable name not found"
        assert variable.is_array() == False, "variable should be an array"
        # test array
        variable_array = x2c_scope.get_variable("X2C_BUFFER")
        assert variable_array is not None, "variable name not found"
        assert variable_array.is_array() == True, "variable should be an array"
        assert len(variable_array) == array_size_test, "array has wrong length"

    def test_nested_array_variable_32(self, mocker, array_size_test=3):
        """Given a valid 32 bit elf file, check if an array variable is read correctly."""
        fake_serial(mocker, 32)
        x2c_scope = X2CScope(port="COM14", elf_file=self.elf_file_32)
        variable = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.duty")
        assert variable is not None, "variable name not found"
        assert variable.is_array() == True, "variable should be an array"
        assert len(variable) == array_size_test, "array has wrong length"

    def test_variable_export_import(self, mocker):
        """Given a valid 32 bit elf file, check if export and import functions for variables are working."""
        fake_serial(mocker, 32)
        x2c_scope = X2CScope(port="COM14")
        # try to import elf file instead of loading directly from the constructor
        x2c_scope.import_variables(self.elf_file_32)
        variable = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")
        # store all variables with custom name and default yaml file format
        x2c_scope.export_variables(filename="my_variables")
        assert os.path.exists("my_variables.yml") == True, "custom export yaml file name not found"
        # store all variables with default name and default file format
        x2c_scope.export_variables()
        assert os.path.exists("qspin_foc_same54.yml") == True, "default export yaml file name not found"
        # store a pickle file with only one variable
        x2c_scope.export_variables("my_single_variable", ext=FileType.PICKLE, items=[variable])
        assert os.path.exists("my_single_variable.pkl") == True, "default export pickle file name not found"
        x2c_scope.disconnect()

        # load generated yaml file and try
        x2c_reloaded = X2CScope(port="COM14")
        x2c_reloaded.import_variables(filename="my_variables.yml")
        variable_reloaded = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")
        assert variable.name == variable_reloaded.name, "variables don't have the same name"
        assert variable.address == variable_reloaded.address, "variables don't have the same address"
        assert variable.array_size == variable_reloaded.array_size, "variables don't have the same array size"

        # load generated pickle file with single variable
        x2c_reloaded = X2CScope(port="COM14")
        x2c_reloaded.import_variables(filename="my_single_variable.pkl")
        variable_reloaded = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")
        assert len(x2c_reloaded.variable_factory.parser.variable_map) == 1, "import loaded more than 1 variable"
        assert variable.name == variable_reloaded.name, "variables don't have the same name"
        assert variable.address == variable_reloaded.address, "variables don't have the same address"
        assert variable.array_size == variable_reloaded.array_size, "variables don't have the same array size"

        # house keeping -> delete generated files
        os.remove("my_variables.yml")
        os.remove("qspin_foc_same54.yml")
        os.remove("my_single_variable.pkl")
