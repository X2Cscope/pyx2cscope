from pyx2cscope.parser.Elf16Parser import Elf16Parser
from pyx2cscope.parser.Elf32Parser import Elf32Parser
from pyx2cscope.variable.variable import *  # pylint: disable=import-error

# disabled due to vriable strucuture contains many subclasses with inheritance


class VariableFactory:
    """
    A factory class for creating variable objects based on ELF file parsing.

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
        """
        Initialize the VariableFactory with LNet instance and path to the ELF file.

        Args:
            l_net (LNet): Instance of LNet for communication with the microcontroller.
            elf_path (str, optional): Path to the ELF file.
        """
        self.l_net = l_net
        self.device_info = self.l_net.get_device_info()
        parser = Elf16Parser if self.device_info.uc_width == 2 else Elf32Parser
        self.parser = parser(elf_path)

    def get_var_list(self) -> list[str]:
        """
        Get a list of variable names available in the ELF file.

        Returns:
            list[str]: A list of variable names.
        """
        return self.parser.get_var_list()

    def get_variable(self, name: str) -> Variable | None:
        """
        Retrieve a Variable object based on its name.

        Args:
            name (str): Name of the variable to retrieve.

        Returns:
            Variable: The Variable object, if found. None otherwise.
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
