"""This module provides functionalities for parsing ELF files compatible with 32-bit architectures.

It focuses on extracting structure members and variable information from DWARF debugging information.
"""

import logging

from elftools.common.utils import elf_assert
from elftools.elf.elffile import ELFFile

from pyx2cscope.parser.elf_parser import ElfParser, VariableInfo


class Elf32Parser(ElfParser):
    """
    Class for parsing ELF files compatible with 32-bit architectures.
    """

    def _get_structure_members_recursive(
        self,
        die,
        parent_name: str,
        prev_address_offset=0,
    ):
        """
        Recursively gets structure members from a DWARF DIE.

        Args:
            die: The DIE representing the structure.
            parent_name (str): Name of the parent structure.
            prev_address_offset (int): Address offset from the parent.

        Returns:
            Tuple[dict, int]: Dictionary of members and their offset.
        """
        members = {}
        for child_die in die.iter_children():
            if child_die.tag in {"DW_TAG_member", "DW_TAG_pointer_type", "DW_TAG_array_type"}:
                member = {}
                member_name = parent_name
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name += "." + name_attr.value.decode("utf-8")
                type_attr = child_die.attributes.get("DW_AT_type")
                if type_attr:
                    type_offset = type_attr.value + child_die.cu.cu_offset
                    try:
                        member_type = self._get_member_type(type_offset)
                        offset_value = child_die.attributes.get("DW_AT_data_member_location")
                        offset_value = int(offset_value.value[1]) if offset_value else 0
                        nested_die = self._get_end_die(child_die)
                        if nested_die.tag == "DW_TAG_structure_type":
                            nested_members, _ = self._get_structure_members_recursive(
                                nested_die, member_name, prev_address_offset + offset_value
                            )
                            if nested_members:
                                members.update(nested_members)
                        elif nested_die.tag == "DW_TAG_array_type":
                            array_size = self._get_array_length(nested_die)
                            base_type_attr = nested_die.attributes.get("DW_AT_type")
                            if base_type_attr:
                                base_type_offset = base_type_attr.value + nested_die.cu.cu_offset
                                base_type_die = self.dwarf_info.get_DIE_from_refaddr(base_type_offset)
                                base_type_die = self._get_end_die(base_type_die)
                                if base_type_die:
                                    type_name = base_type_die.attributes.get("DW_AT_name")
                                    type_name = type_name.value.decode("utf-8") if type_name else "unknown"
                                    byte_size_attr = base_type_die.attributes.get("DW_AT_byte_size")
                                    byte_size = byte_size_attr.value if byte_size_attr else 0
                                    member["type"] = type_name
                                    member["byte_size"] = byte_size
                                    member["address_offset"] = prev_address_offset + offset_value
                                    member["array_size"] = array_size
                                    members[member_name] = member
                        else:
                            member["type"] = member_type["name"]
                            member["byte_size"] = member_type["byte_size"]
                            member["address_offset"] = prev_address_offset + offset_value
                            member["array_size"] = self._get_array_length(child_die)
                            members[member_name] = member
                    except Exception as e:
                        logging.error("exception", exc_info=e)
                        continue

        return members, prev_address_offset

    def _get_structure_members(self, structure_die, var_name):
        """
        Retrieves structure members from a DWARF DIE.

        Args:
            structure_die: The DIE representing the structure.
            var_name (str): Name of the variable.

        Returns:
            dict: Dictionary of structure members.
        """
        return self._get_structure_members_recursive(structure_die, var_name)[0]

    def _processing_end_die(self, type_die, end_die):
        """
        Processes the end DIE of a tag to extract variable information.

        Args:
            end_die: The end DIE of the tag.
        """
        try:
            if self.die_variable.attributes.get("DW_AT_location"):
                data = list(self.die_variable.attributes["DW_AT_location"].value)[1:]
                self.address = int.from_bytes(bytes(data), byteorder="little")
            else:
                self.address = None
        except Exception as e:
            logging.error(e)
            self.address = None
        if self.address is None:
            logging.warning(f"Skipping variable {self.var_name} with no valid address")
            return
        if self.var_name.startswith("_") or self.var_name.startswith("__"):
            logging.warning(f"Skipping variable {self.var_name} with underscored name")
            return

        if end_die.tag == "DW_TAG_pointer_type":
            type_name = "pointer"
            self.variable_map[self.var_name] = VariableInfo(
                name=self.var_name,
                byte_size=end_die.attributes["DW_AT_byte_size"].value,
                type=type_name,
                address=self.address,
            )
        elif end_die.tag == "DW_TAG_structure_type":
            members = self._get_structure_members(end_die, self.var_name)
            for member_name, member_data in members.items():
                self.variable_map[member_name] = VariableInfo(
                    name=member_name,
                    byte_size=member_data["byte_size"],
                    type=member_data["type"],
                    address=self.address + member_data["address_offset"],
                    array_size=member_data["array_size"],
                )
        elif end_die.tag == "DW_TAG_array_type":
            array_size = self._get_array_length(end_die)
            base_type_attr = end_die.attributes.get("DW_AT_type")
            if base_type_attr:
                base_type_offset = base_type_attr.value + end_die.cu.cu_offset
                base_type_die = self.dwarf_info.get_DIE_from_refaddr(base_type_offset)
                if base_type_die:
                    base_type_die = self._get_end_die(base_type_die)
                    type_name = base_type_die.attributes.get("DW_AT_name")
                    type_name = type_name.value.decode("utf-8") if type_name else "unknown"
                    byte_size_attr = base_type_die.attributes.get("DW_AT_byte_size")
                    byte_size = byte_size_attr.value if byte_size_attr else 0
                    self.variable_map[self.var_name] = VariableInfo(
                        name=self.var_name,
                        byte_size=byte_size,
                        type=type_name,
                        address=self.address,
                        array_size=array_size,
                    )
        else:
            type_name_attr = end_die.attributes.get("DW_AT_name")
            type_name = type_name_attr.value.decode("utf-8") if type_name_attr else "unknown"
            self.variable_map[self.var_name] = VariableInfo(
                name=self.var_name,
                byte_size=end_die.attributes["DW_AT_byte_size"].value,
                type=type_name,
                address=self.address,
            )

    def _get_array_length(self, type_die):
        """
        Gets the length of an array type.

        Args:
            type_die: The DIE representing the array type.

        Returns:
            int: Length of the array.
        """
        for child in type_die.iter_children():
            if child.tag == "DW_TAG_subrange_type":
                array_length_attr = child.attributes.get("DW_AT_upper_bound")
                if array_length_attr:
                    array_length = array_length_attr.value + 1
                    return array_length
        return 0

    def _load_elf_file(self):
        try:
            with open(self.elf_path, "rb") as stream:
                self.elf_file = ELFFile(stream)
                self.dwarf_info = self.elf_file.get_dwarf_info()
        except IOError:
            raise Exception("Error loading ELF file: {}".format(self.elf_path))

    def _get_dwarf_die_by_offset(self, offset):
        """
        Retrieve a DWARF DIE given its offset.

        Args:
            offset (int): Offset of the DIE.

        Returns:
            DIE: The DWARF DIE corresponding to the offset.
        """
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            for die in root_die:
                if die.offset == offset:
                    return die
        return None

    def _get_end_die(self, current_die):
        """
        Find the end DIE of a type.

        Args:
            current_die (elftools.dwarf.die.DIE): The starting DIE.

        Returns:
            elftools.dwarf.die.DIE: The end DIE of the type.
        """
        valid_words = {
            "DW_TAG_base_type",
            "DW_TAG_pointer_type",
            "DW_TAG_structure_type",
            "DW_TAG_array_type",
        }
        while current_die.tag not in valid_words:
            if "DW_AT_type" not in current_die.attributes:
                logging.warning(f"Skipping DIE at offset {current_die.offset} with no 'DW_AT_type' attribute")
                return None
            ref_addr = current_die.attributes["DW_AT_type"].value + current_die.cu.cu_offset
            current_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        return current_die

    def _get_member_type(self, type_offset):
        """
        Retrieve the type information from DWARF given a type offset.

        Args:
            type_offset (int): Offset of the type DIE.

        Returns:
            dict or None: Dictionary containing the name and byte size of the type, or None if not found.
        """
        type_die = self.dwarf_info.get_DIE_from_refaddr(type_offset)
        if type_die:
            type_die = self._get_end_die(type_die)
            if type_die.tag == "DW_TAG_base_type":
                type_name = type_die.attributes["DW_AT_name"].value.decode("utf-8")
                byte_size_attr = type_die.attributes.get("DW_AT_byte_size")
                byte_size = byte_size_attr.value if byte_size_attr else None

                return {
                    "name": type_name,
                    "byte_size": byte_size,
                }
            elif type_die.tag != "DW_TAG_base_type":
                base_type_attr = type_die.attributes.get("DW_AT_type")
                if base_type_attr:
                    base_type_offset = base_type_attr.value
                    return self._get_member_type(base_type_offset)

    def _map_variables(self) -> dict[str, VariableInfo]:
        self.variable_map.clear()
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            tag_variables = filter(lambda die: die.tag == "DW_TAG_variable", root_die)

            for self.die_variable in tag_variables:
                if "DW_AT_specification" in self.die_variable.attributes:
                    spec_ref_addr = (
                            self.die_variable.attributes["DW_AT_specification"].value
                            + self.die_variable.cu.cu_offset
                    )
                    spec_die = self.dwarf_info.get_DIE_from_refaddr(spec_ref_addr)

                    if self.die_variable.attributes.get("DW_AT_location"):
                        address_set = list(
                            self.die_variable.attributes["DW_AT_location"].value
                        )[1:]
                        self.address = int.from_bytes(
                            bytes(address_set), byteorder="little"
                        )

                    if spec_die.tag == "DW_TAG_variable" and self.address is not None:
                        self.die_variable = spec_die
                        self.var_name = self.die_variable.attributes.get(
                            "DW_AT_name"
                        ).value.decode("utf-8")
                    else:
                        continue

                elif (
                        self.die_variable.attributes.get("DW_AT_location")
                        and self.die_variable.attributes.get("DW_AT_name") is not None
                ):
                    self.var_name = self.die_variable.attributes.get(
                        "DW_AT_name"
                    ).value.decode("utf-8")
                else:
                    continue

                type_attr = self.die_variable.attributes.get("DW_AT_type")
                if type_attr is None:
                    continue

                ref_addr = type_attr.value + self.die_variable.cu.cu_offset

                type_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
                if type_die.tag != "DW_TAG_volatile_type":
                    end_die = self._get_end_die(type_die)
                    if end_die is None:
                        logging.warning(f"Skipping variable {self.var_name} due to missing end DIE")
                        continue
                    self._processing_end_die(type_die, end_die)

                elif type_die.tag == "DW_TAG_volatile_type":
                    end_die = self._get_end_die(type_die)
                    if end_die is None:
                        logging.warning(f"Skipping volatile type variable {self.var_name} due to missing end DIE")
                        continue
                    self._processing_end_die(type_die, end_die)
                    continue

        return self.variable_map


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    elf_file = r""
    elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\elfparser_Decoding\LAB4_FOC\LAB4_FOC.X\dist\default\production\LAB4_FOC.X.production.elf"
    elf_reader = Elf32Parser(elf_file)
    variable_map = elf_reader._map_variables()
    print(variable_map)

    print("'''''''''''''''''''''''''''''''''''''''' ")
    for var_name, var_info in variable_map.items():
        if var_info.array_size != 0:
            print(f"Variable Name: {var_name}, Info: {var_info}")
