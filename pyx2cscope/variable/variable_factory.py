"""Variable Factory returns the respective variable type according to the variable type found at the elf file."""

import logging

from mchplnet.lnet import LNet
from mchplnet.services.frame_device_info import DeviceInfo
from pyx2cscope.parser.elf16_parser import Elf16Parser
from pyx2cscope.parser.elf32_parser import Elf32Parser
from pyx2cscope.variable.variable import (
    Variable,
    VariableFloat,
    VariableInt8,
    VariableInt16,
    VariableInt32,
    VariableInt64,
    VariableUint8,
    VariableUint16,
    VariableUint32,
    VariableUint64,
)


class VariableFactory:
    """A factory class for creating variable objects based on ELF file parsing.

    This class uses either `Elf16Parser` or `Elf32Parser` depending on the microcontroller's architecture
    to parse the ELF file and create variable objects that can interact with the microcontroller's memory.

    Attributes:
        l_net (LNet): An instance of the LNet class for communication with the microcontroller.
        device_info: Information about the connected device.
        parser (ElfParser): An instance of the appropriate ELF parser based on the device's architecture.

    Methods:
        get_var_list: Retrieves a list of variable names from the ELF file.
        get_variable: Gets a Variable object based on the variable name.
        _get_variable_instance: Creates a Variable instance from provided information.
    """

    def __init__(self, l_net: LNet, elf_path=None):
        """Initialize the VariableFactory with LNet instance and path to the ELF file.

        Args:
            l_net (LNet): Instance of LNet for communication with the microcontroller.
            elf_path (str, optional): Path to the ELF file.
        """
        self.l_net = l_net
        self.device_info = self.l_net.get_device_info()
        parser = (
            Elf16Parser
            if self.device_info.uc_width == DeviceInfo.MACHINE_16
            else Elf32Parser
        )
        self.parser = parser(elf_path)

    def get_var_list(self) -> list[str]:
        """Get a list of variable names available in the ELF file.

        Returns:
            list[str]: A list of variable names.
        """
        return self.parser.get_var_list()

    def get_variable(self, name: str) -> Variable | None:
        """Retrieve a Variable object based on its name.

        Args:
            name (str): Name of the variable to retrieve.

        Returns:
            Variable: The Variable object, if found. None otherwise.
        """
        try:
            variable_info = self.parser.get_var_info(name)
            return self._get_variable_instance(
                variable_info.address,
                variable_info.type,
                variable_info.array_size,
                variable_info.name,
            )
        except Exception as e:
            logging.error(f"Error while getting variable '{name}' : {str(e)}")

    def _get_variable_instance(
        self,
        address: int,
        var_type: str,
        array_size: int,
        name: str,
    ) -> Variable:
        """Create a variable object based on the provided address, type, and name.

        Args:
            address (int): Address of the variable in the MCU memory.
            var_type (VarTypes): Type of the variable.
            array_size (int): the size of the array, in case of an array, 0 otherwise.
            name (str): Name of the variable.

        returns:
            Variable: Variable object based on the provided information.

        raises:
            Exception: If the variable type is not found.
        """
        type_factory = {
            "bool": VariableUint8,
            "char": VariableInt8,
            "double": VariableFloat,
            "float": VariableFloat,
            "int": VariableInt16,
            "long": VariableInt32,
            "long double": VariableFloat,
            "long int": VariableInt32,
            "long long": VariableInt64,
            "long long unsigned int": VariableUint64,
            "long unsigned int": VariableUint32,
            "pointer": VariableUint16
            if self.device_info.uc_width == self.device_info.MACHINE_16
            else VariableUint32,  # TODO v 0.2.0
            "short": VariableInt16,
            "short int": VariableInt16,
            "short unsigned int": VariableUint16,
            "signed char": VariableInt8,
            "signed int": VariableInt32,
            "signed long": VariableInt32,
            "signed long long": VariableInt64,
            "unsigned char": VariableUint8,
            "unsigned int": VariableUint16,
            "unsigned long": VariableUint32,
            "unsigned long long": VariableUint64,
        }

        try:
            var_type = var_type.lower().replace("_", "")
            return type_factory[var_type](self.l_net, address, array_size, name)
        except IndexError:
            raise Exception(
                f"Type {var_type} not found. Cannot select the right variable representation."
            )
