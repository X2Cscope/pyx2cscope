"""This module provides functionalities for parsing ELF files compatible with 32-bit architectures.

It focuses on extracting structure members and variable information from DWARF debugging information.
"""

import logging

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

from pyx2cscope.parser.elf_parser import ElfParser, VariableInfo


class Elf32Parser(ElfParser):
    """Class for parsing ELF files compatible with 32-bit architectures."""

    def __init__(self, elf_path):
        """Initialize the Elf32Parser with the given ELF file path."""
        self.elf_path = elf_path
        self.variable_map = {}
        self.symbol_table = {}  # Ensure this initialization is included
        self.address = None
        self.var_name = None
        self.die_variable = None
        self.elf_file = None
        self.dwarf_info = None
        self._load_elf_file()
        self._load_symbol_table()  # Load symbol table entries into a dictionary

    def _load_elf_file(self):
        try:
            self.stream = open(self.elf_path, "rb")
            self.elf_file = ELFFile(self.stream)
            self.dwarf_info = self.elf_file.get_dwarf_info()
        except IOError:
            raise Exception(f"Error loading ELF file: {self.elf_path}")

    def close_elf_file(self):
        """Closes the ELF file stream."""
        if self.stream:
            self.stream.close()

    def _map_variables(self) -> dict[str, VariableInfo]:
        self.variable_map.clear()
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            tag_variables = filter(lambda die: die.tag == "DW_TAG_variable", root_die)

            for die_variable in tag_variables:
                self._process_variable_die(die_variable)

        return self.variable_map

    def _process_variable_die(self, die_variable):
        """Process an individual variable DIE."""
        if "DW_AT_specification" in die_variable.attributes:
            spec_ref_addr = (
                die_variable.attributes["DW_AT_specification"].value
                + die_variable.cu.cu_offset
            )
            spec_die = self.dwarf_info.get_DIE_from_refaddr(spec_ref_addr)

            if spec_die.tag == "DW_TAG_variable":
                self.die_variable = spec_die
                self.var_name = self.die_variable.attributes.get(
                    "DW_AT_name"
                ).value.decode("utf-8")
                self._extract_address(die_variable)
            else:
                return

        elif (
            die_variable.attributes.get("DW_AT_location")
            and die_variable.attributes.get("DW_AT_name") is not None
        ):
            self.var_name = die_variable.attributes.get("DW_AT_name").value.decode(
                "utf-8"
            )
            self.die_variable = die_variable
            self._extract_address(die_variable)
        elif (
            die_variable.attributes.get("DW_AT_external")
            and die_variable.attributes.get("DW_AT_name") is not None
        ):
            self.var_name = die_variable.attributes.get("DW_AT_name").value.decode(
                "utf-8"
            )
            self.die_variable = die_variable
            self._extract_address(die_variable)
        else:
            return

        type_attr = self.die_variable.attributes.get("DW_AT_type")
        if type_attr is None:
            return

        ref_addr = type_attr.value + self.die_variable.cu.cu_offset
        type_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        if type_die.tag != "DW_TAG_volatile_type":
            end_die = self._get_end_die(type_die)
            if end_die is None:
                logging.warning(
                    f"Skipping variable {self.var_name} due to missing end DIE"
                )
                return
            self._processing_end_die(end_die)

        elif type_die.tag == "DW_TAG_volatile_type":
            end_die = self._get_end_die(type_die)
            if end_die is None:
                logging.warning(
                    f"Skipping volatile type variable {self.var_name} due to missing end DIE"
                )
                return
            self._processing_end_die(end_die)

    def _get_end_die(self, current_die):
        """Find the end DIE of a type."""
        valid_words = {
            "DW_TAG_base_type",
            "DW_TAG_pointer_type",
            "DW_TAG_structure_type",
            "DW_TAG_array_type",
        }
        while current_die.tag not in valid_words:
            if "DW_AT_type" not in current_die.attributes:
                logging.warning(
                    f"Skipping DIE at offset {current_die.offset} with no 'DW_AT_type' attribute"
                )
                return None
            ref_addr = (
                current_die.attributes["DW_AT_type"].value + current_die.cu.cu_offset
            )
            current_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        return current_die

    def _processing_end_die(self, end_die):
        """Processes the end DIE of a tag to extract variable information."""
        self._extract_address(self.die_variable)
        if self.address is None and not self.die_variable.attributes.get(
            "DW_AT_external"
        ):
            return

        if end_die.tag == "DW_TAG_pointer_type":
            self._process_pointer_type(end_die)
        elif end_die.tag == "DW_TAG_structure_type":
            self._process_structure_type(end_die)
        elif end_die.tag == "DW_TAG_array_type":
            self._process_array_type(end_die)
        else:
            self._process_base_type(end_die)

    def _extract_address(self, die_variable):
        """Extracts the address of the current variable or fetches it from the symbol table if not found."""
        try:
            if "DW_AT_location" in die_variable.attributes:
                data = list(die_variable.attributes["DW_AT_location"].value)[1:]
                self.address = int.from_bytes(bytes(data), byteorder="little")
            else:
                self.address = self._fetch_address_from_symtab(
                    die_variable.attributes.get("DW_AT_name").value.decode("utf-8")
                )
        except Exception as e:
            logging.error(e)
            self.address = None

    def _load_symbol_table(self):
        """Loads symbol table entries into a dictionary for fast access."""
        for section in self.elf_file.iter_sections():
            if isinstance(section, SymbolTableSection):
                for symbol in section.iter_symbols():
                    if symbol["st_info"].type == "STT_OBJECT":
                        self.symbol_table[symbol.name] = symbol["st_value"]

    def _fetch_address_from_symtab(self, variable_name):
        """Fetches the address of a variable from the preloaded symbol table."""
        return self.symbol_table.get(variable_name, None)

    def _find_actual_declaration(self, die_variable):
        """Find the actual declaration of an extern variable."""
        while "DW_AT_specification" in die_variable.attributes:
            spec_ref_addr = (
                die_variable.attributes["DW_AT_specification"].value
                + die_variable.cu.cu_offset
            )
            die_variable = self.dwarf_info.get_DIE_from_refaddr(spec_ref_addr)
        return die_variable

    def _process_pointer_type(self, end_die):
        """Process a pointer type variable."""
        type_name = "pointer"
        self.variable_map[self.var_name] = VariableInfo(
            name=self.var_name,
            byte_size=end_die.attributes["DW_AT_byte_size"].value,
            type=type_name,
            address=self.address,
        )

    def _process_structure_type(self, end_die):
        """Process a structure type variable."""
        members = self._get_structure_members(end_die, self.var_name)
        for member_name, member_data in members.items():
            self.variable_map[member_name] = VariableInfo(
                name=member_name,
                byte_size=member_data["byte_size"],
                type=member_data["type"],
                address=(
                    self.address + member_data["address_offset"]
                    if self.address
                    else None
                ),
                array_size=member_data["array_size"],
            )

    def _process_array_type(self, end_die):
        """Process an array type variable."""
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

    def _process_base_type(self, end_die):
        """Process a base type variable."""
        type_name_attr = end_die.attributes.get("DW_AT_name")
        type_name = (
            type_name_attr.value.decode("utf-8") if type_name_attr else "unknown"
        )
        self.variable_map[self.var_name] = VariableInfo(
            name=self.var_name,
            byte_size=end_die.attributes["DW_AT_byte_size"].value,
            type=type_name,
            address=self.address,
        )

    def _get_structure_members_recursive(
        self, die, parent_name: str, prev_address_offset=0
    ):
        """Recursively gets structure members from a DWARF DIE."""
        members = {}
        for child_die in die.iter_children():
            if child_die.tag in {
                "DW_TAG_member",
                "DW_TAG_pointer_type",
                "DW_TAG_array_type",
            }:
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
                        offset_value = child_die.attributes.get(
                            "DW_AT_data_member_location"
                        )
                        offset_value = int(offset_value.value[1]) if offset_value else 0
                        nested_die = self._get_end_die(child_die)
                        if nested_die.tag == "DW_TAG_structure_type":
                            nested_members, _ = self._get_structure_members_recursive(
                                nested_die,
                                member_name,
                                prev_address_offset + offset_value,
                            )
                            if nested_members:
                                members.update(nested_members)
                        elif nested_die.tag == "DW_TAG_array_type":
                            array_size = self._get_array_length(nested_die)
                            base_type_attr = nested_die.attributes.get("DW_AT_type")
                            if base_type_attr:
                                base_type_offset = (
                                    base_type_attr.value + nested_die.cu.cu_offset
                                )
                                base_type_die = self.dwarf_info.get_DIE_from_refaddr(
                                    base_type_offset
                                )
                                base_type_die = self._get_end_die(base_type_die)
                                if base_type_die:
                                    type_name = base_type_die.attributes.get(
                                        "DW_AT_name"
                                    )
                                    type_name = (
                                        type_name.value.decode("utf-8")
                                        if type_name
                                        else "unknown"
                                    )
                                    byte_size_attr = base_type_die.attributes.get(
                                        "DW_AT_byte_size"
                                    )
                                    byte_size = (
                                        byte_size_attr.value if byte_size_attr else 0
                                    )
                                    member["type"] = type_name
                                    member["byte_size"] = byte_size
                                    member["address_offset"] = (
                                        prev_address_offset + offset_value
                                    )
                                    member["array_size"] = array_size
                                    members[member_name] = member
                        else:
                            member["type"] = member_type["name"]
                            member["byte_size"] = member_type["byte_size"]
                            member["address_offset"] = (
                                prev_address_offset + offset_value
                            )
                            member["array_size"] = self._get_array_length(child_die)
                            members[member_name] = member
                    except Exception as e:
                        logging.error("exception", exc_info=e)
                        continue

        return members, prev_address_offset

    def _get_structure_members(self, structure_die, var_name):
        """Retrieves structure members from a DWARF DIE."""
        return self._get_structure_members_recursive(structure_die, var_name)[0]

    def _get_array_length(self, type_die):
        """Gets the length of an array type."""
        for child in type_die.iter_children():
            if child.tag == "DW_TAG_subrange_type":
                array_length_attr = child.attributes.get("DW_AT_upper_bound")
                if array_length_attr:
                    array_length = array_length_attr.value + 1
                    return array_length
        return 0

    def _get_member_type(self, type_offset):
        """Retrieve the type information from DWARF given a type offset."""
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

    def _get_dwarf_die_by_offset(self, offset):
        """Retrieve a DWARF DIE given its offset."""
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            for die in root_die:
                if die.offset == offset:
                    return die
        return None


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    # elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\elfparser_Decoding\LAB4_FOC\LAB4_FOC.X\dist\default\debug\LAB4_FOC.X.debug.elf"
    # elf_file = r"C:\Users\m67250\Downloads\pmsm (1)\mclv-48v-300w-an1292-dspic33ak512mc510_v1.0.0\pmsm.X\dist\default\production\pmsm.X.production.elf"
    elf_file = r"C:\Users\m67250\Downloads\pmsm_foc_zsmt_hybrid_sam_e54\pmsm_foc_zsmt_hybrid_sam_e54\firmware\qspin_zsmt_hybrid.X\dist\default\production\qspin_zsmt_hybrid.X.production.elf"
    # elf_file = r"C:\Users\m67250\Microchip Technology Inc\Mark Wendler - M18034 - Masters_2024_MC3\MastersDemo_ZSMT_dsPIC33CK_MCLV_48_300.X\dist\default\production\MastersDemo_ZSMT_dsPIC33CK_MCLV_48_300.X.production.elf"
    elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\ZSMT_dsPIC33CK_MCLV_48_300.X\dist\default\production\ZSMT_dsPIC33CK_MCLV_48_300.X.production.elf"  # 16bit-ELF
    elf_reader = Elf32Parser(elf_file)
    variable_map = elf_reader._map_variables()
    print(variable_map)

    print("'''''''''''''''''''''''''''''''''''''''' ")
    counter = 0
    for var_name, var_info in variable_map.items():

        # if var_info.address ==None and var_info.array_size !=0:
        # if var_info.array_size!=0:
        #    print(var_name)
        # print(f"Variable Name: {var_name}, Info: {var_info}")

        # if var_info.address ==None:
        #     print(f"Variable Name: {var_name}, Info: {var_info}")
        #     counter+=1
        if var_info.array_size != 0:
            print(f"Variable Name: {var_name}, Info: {var_info}")
