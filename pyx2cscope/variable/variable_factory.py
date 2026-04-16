"""Variable Factory returns the respective variable type according to the variable type found at the elf file."""

import logging
import os
import pickle
import warnings
from dataclasses import asdict
from enum import Enum
from typing import Optional

import yaml

from mchplnet.lnet import LNet
from pyx2cscope.parser.elf_parser import DummyParser
from pyx2cscope.parser.generic_parser import GenericParser
from pyx2cscope.variable.variable import (
    Variable,
    VariableEnum,
    VariableFloat,
    VariableInfo,
    VariableInt8,
    VariableInt16,
    VariableInt32,
    VariableInt64,
    VariableUint8,
    VariableUint16,
    VariableUint32,
    VariableUint64,
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

    _NAME_SFR_PAIR_LEN = 2
    _DEVICE_FAMILY_KEYWORDS = {
        "arm": ("ARM",),
        "pic32": ("PIC32",),
        "dspic": ("DSPIC", "PIC24"),
    }
    _DEVICE_SIGNATURE_KEYWORDS = {
        "dspic33a": ("DSPIC33A", "33AK"),
        "arm": ("ARM",),
        "pic32": ("PIC32",),
        "dspic": ("DSPIC", "PIC24"),
    }

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
        self._warn_if_incompatible(elf_path)

    def set_lnet_interface(self, lnet: LNet):
        """Set the LNet interface to be used for data communication.

        Args:
            lnet (LNet): the LNet interface
        """
        self.l_net = lnet
        self.device_info = self.l_net.get_device_info()

    def _get_device_family(self) -> Optional[str]:
        processor_id = str(getattr(self.device_info, "processor_id", "") or "")
        for family, keywords in self._DEVICE_FAMILY_KEYWORDS.items():
            if any(keyword in processor_id for keyword in keywords):
                return family
        return None

    def _get_device_signature(self) -> Optional[str]:
        processor_id = str(getattr(self.device_info, "processor_id", "") or "")
        for signature, keywords in self._DEVICE_SIGNATURE_KEYWORDS.items():
            if any(keyword in processor_id for keyword in keywords):
                return signature
        return None

    def check_device_compatibility(self) -> dict:
        """Check whether the loaded ELF appears compatible with the connected target."""
        file_family = self.parser.get_target_family() if hasattr(self.parser, "get_target_family") else None
        file_signature = self.parser.get_target_signature() if hasattr(self.parser, "get_target_signature") else file_family
        device_family = self._get_device_family()
        device_signature = self._get_device_signature() or device_family
        checked = bool(file_signature and device_signature)
        compatible = (file_signature == device_signature) if checked else None
        if compatible is False:
            reason = "ELF file and connected target appear to describe different MCU targets."
        elif checked:
            reason = "ELF file appears compatible with the connected target."
        else:
            reason = "Compatibility could not be determined."
        return {
            "checked": checked,
            "compatible": compatible,
            "device_family": device_family,
            "file_family": file_family,
            "device_signature": device_signature,
            "file_signature": file_signature,
            "processor_id": str(getattr(self.device_info, "processor_id", "") or ""),
            "elf_file": getattr(self.parser, "elf_path", ""),
            "reason": reason,
        }

    def _warn_if_incompatible(self, elf_path: str):
        """Warn when the loaded ELF appears incompatible with the connected target."""
        compatibility = self.check_device_compatibility()
        if compatibility["compatible"] is False:
            warnings.warn(
                (
                    f"Loaded ELF '{elf_path}' appears incompatible with the connected target "
                    f"({compatibility['processor_id']})."
                ),
                stacklevel=2,
            )

    def _build_export_file_name(self, filename: Optional[str] = None, ext: FileType= FileType.YAML):
        if filename is None:
            if self.parser.elf_path is not None:
                # get the elf_file name without extension
                filename = os.path.splitext(os.path.basename(self.parser.elf_path))[0]
            else:
                filename = "variables_list"

        return os.path.splitext(filename)[0] + ext.value

    def _resolve_export_item(self, item):
        """Resolve an export item to VariableInfo and its target map kind."""
        variable_info = None
        is_register = False

        if isinstance(item, tuple) and len(item) == self._NAME_SFR_PAIR_LEN:
            name, sfr = item
            is_register = bool(sfr)
            if isinstance(name, str):
                variable_info = self.parser.get_var_info(name, sfr=is_register)
        elif isinstance(item, Variable):
            item = item.info.name

        if isinstance(item, VariableInfo):
            if self.parser.register_map.get(item.name) == item:
                variable_info = item
                is_register = True
            elif self.parser.variable_map.get(item.name) == item:
                variable_info = item
            else:
                variable_info = item
                is_register = item.name in self.parser.register_map
        elif isinstance(item, str):
            if item in self.parser.variable_map:
                variable_info = self.parser.variable_map.get(item)
            elif item in self.parser.register_map:
                variable_info = self.parser.register_map.get(item)
                is_register = True

        return variable_info, is_register

    def export_variables(self, filename: Optional[str] = None, ext: FileType = FileType.YAML, items=None):
        """Store the variables registered on the elf file to a pickle file.

        Args:
            filename (str): The path and name of the file to store data to. Defaults to 'elf_file_name.yml'.
            ext (FileType): The file extension type to be used (yml or pkl, elf is not supported for export).
            items (List): A list of variable names or variables to export. Export all variables if empty.
        """
        if ext is FileType.ELF:
            raise ValueError("Elf file is not yet supported as export format...")
        filename = self._build_export_file_name(filename, ext)

        export_dict = {"variables": {}, "registers": {}}
        if items:
            for item in items:
                variable_info, is_register = self._resolve_export_item(item)
                if variable_info is None:
                    continue
                target_key = "registers" if is_register else "variables"
                export_dict[target_key][variable_info.name] = variable_info
        else:
            export_dict["variables"] = dict(self.parser.variable_map)
            export_dict["registers"] = dict(self.parser.register_map)

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
        self.parser.register_map.clear()
        imported_data = None

        if ext is FileType.ELF:
            self.parser = GenericParser(filename)
            self._warn_if_incompatible(filename)
        if ext is FileType.PICKLE:
            with open(filename, 'rb') as file:
                imported_data = pickle.loads(file.read())
        if ext is FileType.YAML:
            with open(filename, 'r') as file:
                imported_data = yaml.load(file.read(), Loader=yaml.FullLoader)

        if ext is not FileType.ELF:
            if isinstance(imported_data, dict) and "variables" in imported_data:
                self.parser.variable_map = imported_data.get("variables", {}) or {}
                self.parser.register_map = imported_data.get("registers", {}) or {}
            else:
                self.parser.variable_map = imported_data or {}

        logging.debug(f"Variables loaded from {filename}")

    def get_var_list(self) -> list[str]:
        """Get a list of variable names available in the ELF file.

        Returns:
            list[str]: A list of variable names.
        """
        return self.parser.get_var_list()

    def get_sfr_list(self) -> list[str]:
        """Get a list of SFR (Special Function Register) names available in the ELF file.

        Returns:
            list[str]: A list of SFR names.
        """
        return self.parser.get_register_list()

    def get_variable(self, name: str, sfr: bool = False) -> Variable | None:
        """Retrieve a Variable object based on its name.

        Args:
            name (str): Name of the variable to retrieve.
            sfr (bool): Whether to retrieve a peripheral register (SFR) or a firmware variable.

        Returns:
            Variable: The Variable object, if found. None otherwise.
        """
        try:
            variable_info = self.parser.get_var_info(name, sfr=sfr)
            if variable_info is None:
                logging.error(f"Variable '{name}' not found!")
                return None
            if variable_info is None:
                logging.error(f"Variable '{name}' not found!")
                return None
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
            var_type = "enum" if "enum" in var_type else var_type
            return type_factory[var_type](self.l_net, var_info)
        except IndexError:
            raise ValueError(
                f"Type {var_info.type} not found. Cannot select the right variable representation."
            )
