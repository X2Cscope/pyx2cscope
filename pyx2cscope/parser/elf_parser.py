"""This module provides abstract base classes and data structures for parsing ELF files.

Classes:
    VariableInfo: A data class representing information about a variable in an ELF file.
    ElfParser: An abstract base class for parsing ELF files and extracting variable information.

The module is designed to be extended by specific implementations for different ELF file formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VariableInfo:
    """A data class representing information about a variable in an ELF file.

    Attributes:
        name (str): The name of the variable.
        type (str): The data type of the variable.
        byte_size (int): The size of the variable in bytes.
        address (int): The memory address of the variable.
        array_size (int): The size of the array if the variable is an array, default is 0.
    """

    name: str
    type: str
    byte_size: int
    address: int
    array_size: int = 0


class ElfParser(ABC):
    """Abstract base class for parsing ELF files.

    This class provides a general interface for parsing ELF files and extracting
    information about variables contained within. Subclasses should provide specific
    implementations for different types of ELF files based on the architecture.

    Attributes:
        elf_path (str): Path to the ELF file.
        dwarf_info (dict): A dictionary to store DWARF information from the ELF file.
        elf_file: An object representing the ELF file, specific to the implementation.
        variable_map (dict): A map of variable names to their corresponding information.
        var_name (str): The name of the current variable being processed.

    Methods:
        get_var_info: Return information about a specified variable.
        get_var_list: Return a list of variable names from the ELF file.
        map_variables: Map variables from the parsed DWARF information.
    """

    def __init__(self, elf_path: str):
        """Initialize the ElfParser with the path to the ELF file.

        Args:
            elf_path (str): Path to the ELF file.
        """
        self.elf_path = elf_path
        self.dwarf_info = {}
        self.elf_file = None
        self.variable_map = {}
        self.var_name = None
        self.array_size = 0
        self._load_elf_file()

    def get_var_info(self, name: str) -> Optional[VariableInfo]:
        """Return the VariableInfo associated with a given variable name, or None if not found.

        Args:
            name (str): The name of the variable.

        Returns:
            Optional[VariableInfo]: The information of the variable, if available.
        """
        if not self.variable_map:
            self.map_variables()
        return self.variable_map.get(name)

    def get_var_list(self) -> List[str]:
        """Return a list of all variable names available in the ELF file.

        Returns:
            List[str]: A sorted list of variable names.
        """
        if not self.variable_map:
            self._map_variables()
        return sorted(self.variable_map.keys(), key=lambda x: x.lower())

    def map_variables(self) -> Dict[str, VariableInfo]:
        """Map variables from the parsed DWARF information and return them.

        Returns:
            Dict[str, VariableInfo]: A dictionary of variable names to VariableInfo objects.
        """
        if not self.variable_map:
            self._map_variables()
        return self.variable_map

    @abstractmethod
    def _load_elf_file(self):
        """Load the ELF file according to the specific hardware architecture.

        This method should be implemented by subclasses to handle different ELF file formats.
        """

    @abstractmethod
    def _map_variables(self) -> Dict[str, VariableInfo]:
        """Abstract method to map variables from the parsed DWARF information.

        Subclasses should implement this method to extract variable information specific to their ELF format.

        Returns:
            Dict[str, VariableInfo]: A dictionary of variable names to VariableInfo objects.
        """
