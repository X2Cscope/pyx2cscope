"""This module provides abstract base classes and data structures for parsing ELF files.

Classes:
    VariableInfo: A data class representing information about a variable in an ELF file.
    ElfParser: An abstract base class for parsing ELF files and extracting variable information.

The module is designed to be extended by specific implementations for different ELF file formats.
"""
import logging
import os
import pickle
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
    array_size: int
    valid_values: Dict[str, int]


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
        self.symbol_table = {}

        self._load_elf_file()
        self._map_variables()
        self._load_symbol_table()
        self._close_elf_file()

    def get_var_info(self, name: str) -> Optional[VariableInfo]:
        """Return the VariableInfo associated with a given variable name, or None if not found.

        Args:
            name (str): The name of the variable.

        Returns:
            Optional[VariableInfo]: The information of the variable, if available.
        """
        return self.variable_map.get(name)

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
    def _close_elf_file(self):
        """Abstract method to close any open file connection after parsing is done."""


    def export_variable_list(self, path: str = None, filename: str = None):
        """Store the variables registered on the elf file to a pickle file.

        Args:
            path (str): The path where the file will be stored. Defaults to the current directory if empty.
            filename (str): The name of the file. Defaults to 'elf_file_name.pkl' if not provided.
        """
        if filename is None:
            if self.elf_path is not None:
                # get the elf_file name without path and replace .elf by .pkl
                filename = os.path.splitext(os.path.basename(self.elf_path))[0] + ".pkl"
            else:
                filename = "variables_list.pkl"
        else:
            filename += ".pkl"

        if path:
            filename = os.path.join(path, filename)

        with open(filename, 'wb') as file:
            pickle.dump(self.variable_map, file)

        logging.debug(f"Dictionary stored to {filename}")

    def import_variable_list(self, path: str = None, filename: str ='variables_list'):
        """Import and load variables registered on the pickle file.

        Args:
            path (str): The path where the file is stored. Defaults to the current directory if empty.
            filename (str): The name of the pickle file. Defaults to 'variables_list.pkl' if not provided.
        """
        if not filename.endswith('.pkl'):
            filename += '.pkl'

        if path:
            filepath = os.path.join(path, filename)
        else:
            filepath = filename

        if not os.path.exists(filepath):
            raise ValueError(f"Pickle file does not exist at given path: {filepath}")

        # clear any previous loaded variable
        self.variable_map.clear()

        with open(filepath, 'rb') as file:
            self.variable_map = pickle.load(file)
        logging.debug(f"Pickle file loaded from {filepath}")


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

    def _close_elf_file(self):
        pass

