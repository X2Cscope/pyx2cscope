from pyx2cscope.parser.Elf16Parser import Elf16Parser
from pyx2cscope.parser.Elf32Parser import Elf32Parser
from pyx2cscope.variable.variable import *


class VariableFactory:
    def __init__(self, l_net: LNet, elf_path=None):
        self.l_net = l_net
        self.device_info = self.l_net.get_device_info()
        parser = Elf16Parser if self.device_info.uc_width == 2 else Elf32Parser
        self.parser = parser(elf_path)

    def get_var_list(self) -> list[str]:
        """
        Get the list of variables available.

        Returns:
            list[str]: List of variables.
        """
        return self.parser.get_var_list()

    def get_variable(self, name: str) -> Variable | None:
        """
        Get the Variable object from the parser or None.

        Args:
            name (str): Variable name.

        Returns:
            Variable: Variable object or None.
        """
        try:
            variable_info = self.parser.get_var_info(name)
            return self._get_variable_instance(
                variable_info.address, variable_info.type, variable_info.name
            )
        except Exception as e:
            logging.error(f"Error while getting variable '{name}' : {str(e)}")

    def _get_variable_instance(
        self, address: int, var_type: str, name: str
    ) -> Variable:
        """
        create a variable object based on the provided address, type, and name.

        args:
            address (int): Address of the variable in the MCU memory.
            var_type (VarTypes): Type of the variable.
            name (str): Name of the variable.

        returns:
            Variable: Variable object based on the provided information.

        raises:
            Exception: If the variable type is not found.
        """
        type_factory = {
            "bool": Variable_uint8,
            "char": Variable_int8,
            "double": Variable_float,
            "float": Variable_float,
            "int": Variable_int16,
            "long": Variable_int32,
            "long double": Variable_float,
            "long int": Variable_int32,
            "long long": Variable_int64,
            "long long unsigned int": Variable_uint64,
            "long unsigned int": Variable_uint32,
            "pointer": Variable_uint16
            if self.device_info.uc_width == 2
            else Variable_uint32,  # TODO v 0.2.0
            "short": Variable_int16,
            "short int": Variable_int16,
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
