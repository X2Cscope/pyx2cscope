from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class VariableInfo:
    name: str
    type: str
    byte_size: int
    address: int

    # Optional members for structure types
    # members: dict = None

    # def __init__(self, *args, **kwargs):
    #     if "name" in kwargs:
    #         self.name = kwargs["name"]
    #
    # def __getattr__(self, attr):
    #
    #     if self.name == attr:
    #         return attr


class ElfParser(ABC):

    def __init__(self, elf_path):
        """
        Initialize the DwarfParser with the path to the ELF file.

        Args:
            elf_path (str): Path to the ELF file.
        """
        self.elf_path = elf_path
        self.dwarf_info = {}
        self.elf_file = None
        self.variable_map = {}
        self.var_name = None
        self._load_elf_file()

    def get_var_info(self, name: str) -> VariableInfo | None:
        """Return the VariableInfo associated to the variable name or None"""
        if not self.variable_map:
            self.map_variables()
        if name in self.variable_map:
            return self.variable_map[name]
        return None

    def get_var_list(self) -> List[str]:
        """Return all variable name available the elf file."""
        if not self.variable_map:
            self._map_variables()
        return sorted(self.variable_map.keys(), key=lambda x: x.lower())

    def map_variables(self) -> dict[str, VariableInfo]:
        """Return a dictionary of {variable names: VariableInfo}"""
        if not self.variable_map:
            self._map_variables()
        return self.variable_map

    @abstractmethod
    def _load_elf_file(self):
        """
        Load the elf file according to the hardware architecture of the subclass
        """

    @abstractmethod
    def _map_variables(self) -> dict[str, VariableInfo]:
        """Return a dictionary of variable name: VariableInfo"""
