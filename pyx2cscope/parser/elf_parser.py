"""This module provides abstract base classes and data structures for parsing ELF files.

Classes:
    VariableInfo: A data class representing information about a variable in an ELF file.
    ElfParser: An abstract base class for parsing ELF files and extracting variable information.

The module is designed to be extended by specific implementations for different ELF file formats.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pyx2cscope.variable.variable import VariableInfo


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
        self.register_map = {}
        self.symbol_table = {}

        self._load_elf_file()
        self._map_variables()
        self._load_symbol_table()
        self._map_variables()
        self._map_registers()
        self._close_elf_file()

    def get_register_info(self, name: str) -> Optional[VariableInfo]:
        """Return the VariableInfo associated with a given register name, or None if not found.

        Args:
            name (str): The name of the register (e.g. "U1STA", "U1STAbits.URXDA").

        Returns:
            Optional[VariableInfo]: The information of the register, if available.
        """
        return self.register_map.get(name)

    def get_register_list(self) -> List[str]:
        """Return a sorted list of all MCU peripheral register names found in the ELF.

        Returns:
            List[str]: A sorted list of register names.
        """
        return sorted(self.register_map.keys())

    def get_var_info(self, name: str, sfr: bool = False) -> Optional[VariableInfo]:
        """Return the VariableInfo associated with a given variable name, or None if not found.

        Args:
            name (str): The name of the variable.
            sfr (bool): Whether to retrieve a peripheral register (SFR) or a firmware variable.

        Returns:
            Optional[VariableInfo]: The information of the variable, if available.
        """
        return self.register_map.get(name) if sfr else self.variable_map.get(name)

    def get_var_list(self) -> List[str]:
        """Return a list of all variable names available in the ELF file.

        Returns:
            List[str]: A sorted list of variable names.
        """
        return sorted(self.variable_map.keys(), key=lambda x: x.lower())

    @abstractmethod
    def _load_elf_file(self):
        """Load the ELF file according to the specific hardware architecture.

        This method should be implemented by subclasses to handle different ELF file formats.
        """

    @abstractmethod
    def _load_symbol_table(self):
        """Load symbol table according to the specific hardware architecture.

        This method should be implemented by subclasses to handle different ELF file formats.
        """

    @abstractmethod
    def _map_variables(self) -> Dict[str, VariableInfo]:
        """Abstract method to map variables from the parsed DWARF information.

        Subclasses should implement this method to extract variable information specific to their ELF format.

        Returns:
            Dict[str, VariableInfo]: A dictionary of variable names to VariableInfo objects.
        """

    @abstractmethod
    def _map_registers(self) -> Dict[str, VariableInfo]:
        """Abstract method to map MCU peripheral registers from DWARF / symbol table.

        Implementations should populate ``self.register_map`` with entries for every
        peripheral register (SFR) found, including their bitfield sub-entries where
        available. The same ``VariableInfo`` dataclass is reused: ``bit_size`` and
        ``bit_offset`` are non-zero for individual bit/bitfield members.

        Returns:
            Dict[str, VariableInfo]: A dictionary of register names to VariableInfo objects.
        """

    @abstractmethod
    def _close_elf_file(self):
        """Abstract method to close any open file connection after parsing is done."""


class DummyParser(ElfParser):
    """Dummy implementation of ElfParser class.

    This class provides basic functionality of a parser in case an elf_file is
    not supplied. It is a pure implementation of class ElfParser.
    """


    def __init__(self, elf_path = ""):
        """DummyParser constructor takes no argument."""
        super().__init__(elf_path = elf_path)

    def _load_elf_file(self):
        pass

    def _load_symbol_table(self):
        pass

    def _map_variables(self) -> Dict[str, VariableInfo]:
        return {}

    def _map_registers(self) -> Dict[str, VariableInfo]:
        return {}

    def _close_elf_file(self):
        pass

