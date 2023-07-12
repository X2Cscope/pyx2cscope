import logging

from mchplnet.lnet import LNet
from pyx2cscope.parser.Elf16Parser import Elf16Parser
from pyx2cscope.parser.Elf32Parser import Elf32Parser
from pyx2cscope.variable.variable import *
from pyx2cscope.variable.vartypes import VarTypes


class VariableFactory:
    def __init__(self, l_net: LNet, Elf_path=None):
        self.l_net = l_net
        self.elfFile = Elf_path  # Initialize the ELF file as None
        self.parser = None  # Initialize the parser as None
        self.device_info = self.l_net.interface_handshake()

        self.parser_obj = Elf16Parser if self.device_info.width == 2 else Elf32Parser
        self.parser = self.parser_obj(self.elfFile)

    def get_var_list_elf(self) -> list[str]:
        """
        Get the list of variables available from the ELF file.

        Returns:
            list[Variable]: List of variables.
        """
        return self.parser.get_var_list()

    def get_variable_elf(self, name: str) -> Variable:
        """
        Get the value of the variable directly from the ELF file parser and perform further processing.

        Args:
            name (str): Variable name from the user.

        Returns:
            Variable: Variable object with the retrieved value like address, type, and size.
        """
        if self.elfFile is None:
            raise Exception("ELF file is not set. Use set_elf_file()")

        try:
            # ELF parsing
            var_result = self.parser.get_var_info(name)
            if var_result:
                variable = self.get_variable_raw(
                    var_result.address, var_result.type, var_result.name
                )
            return variable
        except Exception as e:
            logging.error(
                f"Error while getting variable '{name}' from ELF file: {str(e)}"
            )
            raise

    def get_variable_raw(
        self, address: int, var_type: VarTypes, name: str = "unknown"
    ) -> Variable:
        """
        get a variable object based on the provided address, type, and name.

        Args:
            address (int): Address of the variable in the MCU memory.
            var_type (VarTypes): Type of the variable.
            name (str, optional): Name of the variable.
            defaults to "unknown".

        returns:
            Variable: Variable object based on the provided information.
        """
        # TODO check address range

        try:
            variable = self._create_variable(address, var_type, name)
            return variable
        except Exception as e:
            logging.error(f"Error while creating variable '{name}': {str(e)}")
            raise

    def _create_variable(self, address: int, var_type: str, name: str) -> Variable:
        """
        create a variable object based on the provided address, type, and name.

        Args:
            address (int): Address of the variable in the MCU memory.
            var_type (VarTypes): Type of the variable.
            name (str): Name of the variable.

        returns:
            Variable: Variable object based on the provided information.

        Raises:
            Exception: If the variable type is not found.
        """
        type_factory = {
            "bool": Variable_uint8,
            "char": Variable_int8,
            "double": Variable_float,
            "float": Variable_float,
            "int": Variable_int32,
            "long": Variable_int32,
            "long int": Variable_int32,
            "long long": Variable_int64,
            "long long unsigned int": Variable_uint64,
            "long unsigned int": Variable_uint32,
            "pointer": Variable_uint16
            if self.device_info == 2
            else Variable_uint32,  # TODO v 0.2.0
            "short": Variable_int16,
            "short unsigned int": Variable_uint16,
            "signed char": Variable_int8,
            "signed int": Variable_int32,
            "signed long": Variable_int32,
            "signed long long": Variable_int64,
            "unsigned char": Variable_uint8,
            "unsigned int": Variable_uint16,
            "unsigned long": Variable_uint32,
            "unsigned long long": Variable_uint64,
        }

        try:
            var_type = var_type.lower().replace("_", "")
            return type_factory[var_type](self.l_net, address, name)
        except IndexError:
            raise Exception(
                f"Type {var_type} not found. Cannot select the right variable representation."
            )
