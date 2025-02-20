"""This module provides functionalities for parsing ELF files compatible with 32-bit architectures.

It focuses on extracting structure members and variable information from DWARF debugging information.
"""

import logging

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

from pyx2cscope.parser.elf_parser import ElfParser, VariableInfo
from elftools.construct.lib import ListContainer
from elftools.dwarf.dwarf_expr import DWARFExprParser


class GenericParser(ElfParser):
    """Class for parsing ELF files compatible with 32-bit architectures."""

    def __init__(self, elf_path):
        """Initialize the GenericParser with the given ELF file path."""
        super().__init__(elf_path)

        # These variables are used as local holders during the file parsing
        self.die_variable = None
        self.var_name = None
        self.address = None
        self.type_attr = None

    def _load_elf_file(self):
        try:
            self.stream = open(self.elf_path, "rb")
            self.elf_file = ELFFile(self.stream)
            self.dwarf_info = self.elf_file.get_dwarf_info()
        except IOError:
            raise Exception(f"Error loading ELF file: {self.elf_path}")

    def _close_elf_file(self):
        """Closes the ELF file stream."""
        if self.stream:
            self.stream.close()

    def _get_die_variable_details(self, die_variable):
        """Process the die_variable to obtain detailed info.

        The purpose of this method is to populate:
        - self.die_variable
        - self.var_name
        - self.address
        - self.type_attr
        """
        self.die_variable = None
        self.var_name = None
        self.address = None
        self.type_attr = None

        # In DIE structure, a variable to be considered valid, has under
        # its attributes the attribute DW_AT_specification or DW_AT_location
        if "DW_AT_specification" in die_variable.attributes:
            spec_ref_addr = (
                    die_variable.attributes["DW_AT_specification"].value
                    + die_variable.cu.cu_offset
            )
            spec_die = self.dwarf_info.get_DIE_from_refaddr(spec_ref_addr)
            # if it is not a concrete variable, return
            if spec_die.tag != "DW_TAG_variable":
                return
            self.die_variable = spec_die
        elif (
                die_variable.attributes.get("DW_AT_location")
                and die_variable.attributes.get("DW_AT_name") is not None
        ):
            self.die_variable = die_variable
        # YA/EP We are not sure if we need to catch external variables.
        # probably they are already being detected anywhere else as static or global
        # variables, so this step may be avoided here.
        # We let the code here in case we want to process them anyway.
        # elif (
        #      die_variable.attributes.get("DW_AT_external")
        #      and die_variable.attributes.get("DW_AT_name") is not None
        #  ):
        #      self.var_name = die_variable.attributes.get("DW_AT_name").value.decode(
        #          "utf-8"
        #      )
        #      self.die_variable = die_variable
        #      self._extract_address(die_variable)
        else:
            return

        self.var_name = self.die_variable.attributes.get("DW_AT_name").value.decode("utf-8")
        self.address = self._extract_address(die_variable)
        self.type_attr = self.die_variable.attributes.get("DW_AT_type")

    def _process_variable_die(self, die_variable):
        """Process an individual variable DIE."""
        self._get_die_variable_details(die_variable)
        if self.type_attr is None:
            return []

        ref_addr = self.type_attr.value + self.die_variable.cu.cu_offset
        type_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        end_die = self._get_end_die(die_variable)

        # try to get variable data on end_die
        if end_die is not None and end_die.tag is not None:
            return self._process_end_die(end_die)

        # try to get variable data on type_die
        end_die = self._get_end_die(type_die)
        if end_die:
            return self._process_end_die(end_die)

        # no data found
        logging.warning(
            f"Skipping variable {self.var_name} due to missing end DIE"
        )
        return []

    def _process_enum_type(self, enum_die):
        """Process an enum type variable and map its members."""
        enum_name_attr = enum_die.attributes.get("DW_AT_name")
        enum_name = (
            enum_name_attr.value.decode("utf-8") if enum_name_attr else "anonymous_enum"
        )

        # Dictionary to store enum member names and values
        enum_members = {}
        for child in enum_die.iter_children():
            if child.tag == "DW_TAG_enumerator":
                name_attr = child.attributes.get("DW_AT_name")
                value_attr = child.attributes.get("DW_AT_const_value")
                if name_attr and value_attr:
                    member_name = name_attr.value.decode("utf-8")
                    member_value = value_attr.value
                    enum_members[member_name] = member_value

        # Check if VariableInfo can accept 'members' or create a compatible entry
        self.variable_map[self.var_name] = VariableInfo(
            name=self.var_name,
            byte_size=enum_die.attributes.get("DW_AT_byte_size", 0).value,
            type=f"enum {enum_name}",
            address=self.address,
            array_size=0,
            valid_values = enum_members
        )

    def _get_end_die(self, current_die):
        """Find the end DIE of a type iteratively."""
        valid_tags = {"DW_TAG_base_type", "DW_TAG_pointer_type", "DW_TAG_structure_type", "DW_TAG_array_type", "DW_TAG_enumeration_type"}
        while current_die and current_die.tag not in valid_tags:
            type_attr = current_die.attributes.get("DW_AT_type")
            if not type_attr:
                logging.warning(f"Skipping DIE at offset {current_die.offset} with no 'DW_AT_type'")
                return None
            ref_addr = type_attr.value + current_die.cu.cu_offset
            current_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        return current_die

    def _process_end_die(self, end_die):
        """Processes the end DIE of a tag to extract variable information.

        This method NEEDS to add a variable to the variable_map.
        In case the end_die does not contain a valid variable, it should return.
        """
        # Handle Types
        if end_die.tag == "DW_TAG_pointer_type":
            pass
        elif end_die.tag == "DW_TAG_enumeration_type":
            self._process_enum_type(end_die)
        elif end_die.tag == "DW_TAG_structure_type":
            self._process_structure_type(end_die)
        elif end_die.tag == "DW_TAG_array_type":
            self._process_array_type(end_die)
        else:
            self._process_base_type(end_die)

    def _extract_address_from_expression(self, expr_value, structs):
        """Extracts an address from DWARF expression.

        Args:
            expr_value: The raw DWARF expression bytes.
            structs: The DWARF structs used for parsing expressions.

        Returns:
            int or None: The extracted address, or None if it couldn't be determined.
        """
        try:
            expression = DWARFExprParser(structs).parse_expr(expr_value)
            for op in expression:
                if op.op_name in {"DW_OP_plus_uconst", "DW_OP_plus_const", "DW_OP_addr"}:
                    return op.args[0]
        except TypeError as e:
            logging.warning(f"Error parsing DWARF expression: {e}")
        return None

    def _extract_address(self, die_variable):
        """Extracts the address of the current variable or fetches it from the symbol table if not found."""
        try:
            if "DW_AT_location" in die_variable.attributes:
                expr_value = die_variable.attributes["DW_AT_location"].value
                return self._extract_address_from_expression(
                    expr_value, die_variable.cu.structs
                )
            else:
                return self._fetch_address_from_symtab(
                    die_variable.attributes.get("DW_AT_name").value.decode("utf-8")
                )
        except Exception as e:
            logging.error(e)
            return None

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
                valid_values={}
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
                type_name = type_name.value.decode("utf-8") if type_name else "array"
                byte_size_attr = base_type_die.attributes.get("DW_AT_byte_size")
                byte_size = byte_size_attr.value if byte_size_attr else 0
                self.variable_map[self.var_name] = VariableInfo(
                    name=self.var_name,
                    byte_size=byte_size,
                    type=type_name,
                    address=self.address,
                    array_size=array_size,
                    valid_values={}
                )

    def _process_base_type(self, end_die):
        """Process a base type variable."""
        type_name_attr = end_die.attributes.get("DW_AT_name")
        type_name = (
            type_name_attr.value.decode("utf-8") if type_name_attr else "base unknown"
        )
        self.variable_map[self.var_name] = VariableInfo(
            name=self.var_name,
            byte_size=end_die.attributes["DW_AT_byte_size"].value,
            type=type_name,
            address=self.address,
            array_size=0,
            valid_values={}
        )

    def _get_member_offset(self, die) -> int | None:
        """Extracts the offset for a structure member.

        Args:
            die: The DIE of the structure member.

        Returns:
            int or None: The offset value, or None if it couldn't be determined.
        """
        assert die.tag == "DW_TAG_member"
        data_member_location = die.attributes.get("DW_AT_data_member_location")
        if data_member_location is None:
            return None
        value = data_member_location.value
        if isinstance(value, int):
            return value
        if isinstance(value, ListContainer):
            return self._extract_address_from_expression(value, die.cu.structs)
        logging.warning(f"Unknown data_member_location value: {value}")
        return None

    def _process_member_array_type(self, member_type_die, member_name, prev_offset, offset):
        """Process array type structure members recursively."""
        members = {}
        end_die = self._get_end_die(member_type_die)
        array_size = self._get_array_length(end_die)
        base_type_attr = end_die.attributes.get("DW_AT_type")
        if base_type_attr:
            base_type_offset = base_type_attr.value + end_die.cu.cu_offset
            base_type_die = self.dwarf_info.get_DIE_from_refaddr(base_type_offset)
            if base_type_die:
                base_type_die = self._get_end_die(base_type_die)
                type_name_attr = base_type_die.attributes.get("DW_AT_name")
                type_name = (
                    type_name_attr.value.decode("utf-8")
                    if type_name_attr
                    else "Array Element"
                )
                byte_size_attr = base_type_die.attributes.get("DW_AT_byte_size")
                element_byte_size = byte_size_attr.value if byte_size_attr else 1

                # add the array itself as a variable
                members[member_name] = {
                    "type": type_name,
                    "byte_size": array_size * element_byte_size,
                    "address_offset": prev_offset + offset,
                    "array_size": array_size,  # Individual elements aren't arrays
                }

                # Generate array members
                for i in range(array_size):
                    element_name = f"{member_name}[{i}]"
                    members[element_name] = {
                        "type": type_name,
                        "byte_size": element_byte_size,
                        "address_offset": prev_offset + offset + i * element_byte_size,
                        "array_size": 0,  # Individual elements aren't arrays
                    }
        return members

    def _process_structure_member(self, members, child_die, prev_offset, offset, parent_name):
        """Process individual structure member, including handling nested types and arrays."""
        member = {}
        type_attr = child_die.attributes.get("DW_AT_type")
        if type_attr:
            type_offset = type_attr.value + child_die.cu.cu_offset
            try:
                member_type_die = self.dwarf_info.get_DIE_from_refaddr(type_offset)
                if not member_type_die:
                    return

                if member_type_die.tag == "DW_TAG_array_type":
                    nested_array_members = self._process_member_array_type(
                        member_type_die, parent_name, prev_offset, offset
                    )
                    members.update(nested_array_members)
                    return  # Array processing is handled

                member_type = self._get_member_type(type_offset)
                if member_type:
                    member["type"] = member_type["name"]
                    member["byte_size"] = member_type["byte_size"]
                    member["address_offset"] = prev_offset + offset
                    member["array_size"] = self._get_array_length(member_type_die)
                    members[parent_name] = member

                # Handle nested structures
                nested_die = self._get_end_die(child_die)
                if nested_die.tag == "DW_TAG_structure_type":
                    nested_members, _ = self._get_structure_members_recursive(
                        nested_die, parent_name, prev_offset + offset
                    )
                    if nested_members:
                        members.update(nested_members)

            except Exception as e:
                logging.error(f"Exception processing member '{parent_name}': {e}", exc_info=True)

    def _get_structure_members_recursive(self, die, parent_name: str, prev_offset=0):
        """Recursively extracts structure members from a DWARF DIE, including arrays."""
        members = {}
        for child_die in die.iter_children():
            member = {}
            if child_die.tag == "DW_TAG_member":
                offset = self._get_member_offset(child_die)
                if offset is None:
                    continue
                member_name = parent_name
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name += "." + name_attr.value.decode("utf-8")
                self._process_structure_member(member, child_die, prev_offset, offset, member_name)
                members.update(member) # member should be varinfo?
        return members, prev_offset

    def _get_structure_members(self, structure_die, var_name):
        """Retrieves structure members from a DWARF DIE."""
        return self._get_structure_members_recursive(structure_die, var_name)[0]

    @staticmethod
    def _get_array_length(type_die):
        """Gets the length of an array type."""
        for child in type_die.iter_children():
            if child.tag == "DW_TAG_subrange_type":
                array_length_attr = child.attributes.get("DW_AT_upper_bound")
                if array_length_attr:
                    array_length = array_length_attr.value + 1
                    return array_length
        return 0

    def _get_member_type(self, type_ref_addr):
        """Retrieve the type information from DWARF given a type offset."""
        try:
            type_die = self.dwarf_info.get_DIE_from_refaddr(type_ref_addr)
        except KeyError:
            return
        type_die = self._get_end_die(type_die)
        if type_die is None:
            return
        if type_die.tag == "DW_TAG_base_type":
            type_name = type_die.attributes["DW_AT_name"].value.decode("utf-8")
            byte_size_attr = type_die.attributes.get("DW_AT_byte_size")
            byte_size = byte_size_attr.value if byte_size_attr else None
            return {
                "name": type_name,
                "byte_size": byte_size,
            }
        # if we have a different tag than "DW_TAG_base_type", keep on searching
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

    def _map_variables(self) -> dict[str, VariableInfo]:
        """Maps all variables in the ELF file."""
        self.variable_map.clear()
        for cu in self.dwarf_info.iter_CUs():
            for die in filter(lambda d: d.tag == "DW_TAG_variable", cu.iter_DIEs()):
                self.expression_parser = DWARFExprParser(die.cu.structs)
                self._process_variable_die(die)

        # Remove variables with invalid addresses
        self.variable_map = {
            name: info
            for name, info in self.variable_map.items()
            if info.address is not None and info.address != 0
        }

        # #Update type _Bool to bool
        # for var_info in self.variable_map.values():
        #     if var_info.type == "_Bool":
        #         var_info.type = "bool"

        return self.variable_map


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    #elf_file = r"C:\Users\m67250\Downloads\pmsm (1)\mclv-48v-300w-an1292-dspic33ak512mc510_v1.0.0\pmsm.X\dist\default\production\pmsm.X.production.elf"
    # elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\Training_Domel\motorbench_demo_domel.X\dist\default\production\motorbench_demo_domel.X.production.elf"
    #elf_file = r"C:\Users\m67250\Downloads\mcapp_pmsm_zsmtlf(1)\mcapp_pmsm_zsmtlf\project\mcapp_pmsm.X\dist\default\production\mcapp_pmsm.X.production.elf"
    elf_file = r"..\..\tests\data\qspin_foc_same54.elf"
    elf_reader = GenericParser(elf_file)
    variable_map = elf_reader._map_variables()

    print(variable_map)
    print(len(variable_map))
    print("'''''''''''''''''''''''''''''''''''''''' ")
    counter = 0

    for var_info in variable_map.values():
        if var_info.array_size > 0:
            print(var_info)