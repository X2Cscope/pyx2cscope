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
    members: dict = None

    # def __init__(self, *args, **kwargs):
    #     if "name" in kwargs:
    #         self.name = kwargs["name"]
    #
    # def __getattr__(self, attr):
    #
    #     if self.name == attr:
    #         return attr


class ElfParser(ABC):
    @abstractmethod
    def get_var_info(self, var_name: str) -> VariableInfo:
        pass

    @abstractmethod
    def get_var_list(self) -> List[str]:
        """Return all variables described at elf file as a list of variable names."""
        pass
