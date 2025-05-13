"""Variable Factory returns the respective variable type according to the variable type found at the elf file."""

import logging
import os
import pickle

import yaml
from enum import Enum
from dataclasses import asdict

from mchplnet.lnet import LNet
from pyx2cscope.parser.elf_parser import DummyParser
from pyx2cscope.parser.generic_parser import GenericParser
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
    VariableEnum,
    VariableInfo,
)

class FileType(Enum):
    """Enumeration of supported file types for import/export operations."""
    YAML = ".yml"
    PICKLE = ".pkl"
    ELF = ".elf"

def variable_info_repr(dumper, data):
    """Helper function to yaml file deserializer. Do not call this function."""
    return dumper.represent_mapping('!VariableInfo', asdict(data))

# Custom constructor for VariableInfo
def variable_info_constructor(loader, node):
    """Helper function to yaml file deserializer. Do not call this function."""
    values = loader.construct_mapping(node)
    return VariableInfo(**values)

# adding constructor and representation of VariableInfo to yaml module.
yaml.add_representer(VariableInfo, variable_info_repr)
yaml.add_constructor('!VariableInfo', variable_info_constructor)

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

        # we should be able to initialize without using and elf file.
        if elf_path is None:
            self.parser = DummyParser()
        else:
            self.set_elf_file(elf_path)

    def set_elf_file(self, elf_path: str):
        """Set an elf file to be used as source for variables and addresses.

        Args:
            elf_path (str): Path to the elf file.

        Returns:
            None
        """
        parser = GenericParser
        self.parser = parser(elf_path)

    def set_lnet_interface(self, lnet: LNet):
        """Set the LNet interface to be used for data communication.

        Args:
            lnet (LNet): the LNet interface
        """
        self.l_net = lnet

    def _build_export_file_name(self, filename: str = None, ext: FileType= FileType.YAML):
        if filename is None:
            if self.parser.elf_path is not None:
                # get the elf_file name without extension
                filename = os.path.splitext(os.path.basename(self.parser.elf_path))[0]
            else:
                filename = "variables_list"

        return os.path.splitext(filename)[0] + ext.value

    def export_variables(self, filename: str = None, ext: FileType = FileType.YAML, items=None):
        """Store the variables registered on the elf file to a pickle file.

        Args:
            filename (str): The path and name of the file to store data to. Defaults to 'elf_file_name.yml'.
            ext (FileType): The file extension type to be used (yml or pkl, elf is not supported for export).
            items (List): A list of variable names or variables to export. Export all variables if empty.
        """
        if ext is FileType.ELF:
            raise ValueError("Elf file is not yet supported as export format...")
        filename = self._build_export_file_name(filename, ext)

        export_dict = {}
        if items:
            for item in items:
                variable_name = item.name if isinstance(item, Variable) else item
                export_dict[variable_name] = self.parser.variable_map.get(variable_name)
        else:
            export_dict = self.parser.variable_map

        if ext is FileType.PICKLE:
            with open(filename, 'wb') as file:
                pickle.dump(export_dict, file)
        if ext is FileType.YAML:
            with open(filename, 'w') as file:
                yaml.dump(export_dict, file)

        logging.debug(f"Dictionary stored to {filename}")

    def import_variables(self, filename: str):
        """Import and load variables registered on the file.

        Currently supported files are Elf (.elf), Pickle (.pkl), and Yaml (.yml).
        The flush parameter defaults to true and clears all previous loaded variables. This flag is
        intended to be used when adding single variables to the parser.

        Args:
            filename (str): The name of the file and its path.
        """
        if not os.path.exists(filename):
            raise ValueError(f"File does not exist at given path: {filename}")
        try:
            ext = FileType(os.path.splitext(filename)[1])
        except ValueError:
            raise ValueError(f"File extension not supported. Supported ones are: {[f.value for f in FileType]}")

        # clear any previous loaded variable
        self.parser.variable_map.clear()

        if ext is FileType.ELF:
            self.parser = GenericParser(filename)
        if ext is FileType.PICKLE:
            with open(filename, 'rb') as file:
                self.parser.variable_map = pickle.load(file)
        if ext is FileType.YAML:
            with open(filename, 'r') as file:
                self.parser.variable_map = yaml.load(file, Loader=yaml.FullLoader)

        logging.debug(f"Variables loaded from {filename}")

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
            return self.get_variable_raw(variable_info)
        except Exception as e:
            logging.error(f"Error while getting variable '{name}' : {str(e)}")

    def get_variable_raw(self, var_info: VariableInfo) -> Variable:
        """Create a variable object based on the provided address, type, and name, defined by DataClass VariableInfo.

        Args:
            var_info (VariableInfo): details about the variable as name, address, type, array_size, etc.

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
            "pointer": (
                VariableUint16
                if self.device_info.uc_width == self.device_info.MACHINE_16
                else VariableUint32
            ),
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
            "enum": VariableEnum,
        }

        try:

            var_type: str = var_info.type.lower().replace("_", "")
            params = [self.l_net, var_info.address, var_info.array_size, var_info.name]
            if "enum" in var_type:
                var_type = "enum"
                params.append(var_info.valid_values)

            return type_factory[var_type](*params)
        except IndexError:
            raise ValueError(
                f"Type {var_type} not found. Cannot select the right variable representation."
            )
