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

    def _get_die_variable(self, die_struct):
        """Process the die_struct to obtain the die containing the variable and its info.

        This method populates class members:
        - self.die_variable
        - self.var_name
        - self.address
        """
        self.die_variable = None
        self.var_name = None
        self.address = None

        # In DIE structure, a variable to be considered valid, has under
        # its attributes the attribute DW_AT_specification or DW_AT_location
        if "DW_AT_specification" in die_struct.attributes:
            spec_ref_addr = die_struct.attributes["DW_AT_specification"].value + die_struct.cu.cu_offset
            spec_die = self.dwarf_info.get_DIE_from_refaddr(spec_ref_addr)
            # if it is not a concrete variable, return
            if spec_die.tag != "DW_TAG_variable":
                return
            self.die_variable = spec_die
        elif die_struct.attributes.get("DW_AT_location") and die_struct.attributes.get("DW_AT_name") is not None:
            self.die_variable = die_struct
        # YA/EP We are not sure if we need to catch external variables.
        # probably they are already being detected anywhere else as static or global
        # variables, so this step may be avoided here.
        # We let the code here in case we want to process them anyway.
        # elif die_variable.attributes.get("DW_AT_external") and die_variable.attributes.get("DW_AT_name") is not None:
        #      self.var_name = die_variable.attributes.get("DW_AT_name").value.decode("utf-8")
        #      self.die_variable = die_variable
        #      self._extract_address(die_variable)
        else:
            return

        self.var_name = self.die_variable.attributes.get("DW_AT_name").value.decode("utf-8")
        self.address = self._extract_address(die_struct)

    def _process_die(self, die):
        """Process a DIE structure containing the variable and its."""
        self._get_die_variable(die)
        if self.address is None:
            return

        members = {}
        self._process_end_die(members, self.die_variable, self.var_name, 0)
        # Uncomment and use if base type processing is needed
        # base_type_die = self._get_base_type_die(self.die_variable)
        # self._process_end_die(members, base_type_die, self.var_name, 0)

        for member_name, member_data in members.items():
            self.variable_map[member_name] = VariableInfo(
                name = member_name,
                byte_size = member_data["byte_size"],
                bit_size = member_data["bit_size"],
                bit_offset = member_data["bit_offset"],
                type = member_data["type"],
                address = self.address + member_data["address_offset"],
                array_size=member_data["array_size"],
                valid_values=member_data["valid_values"],
            )

    def _get_base_type_die(self, current_die):
        """Find the base type die regarding the current selected die, i.e. array_type."""
        type_attr = current_die.attributes.get("DW_AT_type")
        if type_attr:
            ref_addr = type_attr.value + current_die.cu.cu_offset
            return self.dwarf_info.get_DIE_from_refaddr(ref_addr)

    def _get_end_die(self, current_die):
        """Find the end DIE of a type iteratively."""
        ref_addr = None
        end_die = current_die
        valid_tags = {
            "DW_TAG_base_type",
            "DW_TAG_pointer_type",
            "DW_TAG_structure_type",
            "DW_TAG_array_type",
            "DW_TAG_enumeration_type",
            "DW_TAG_union_type"
        }
        while end_die and end_die.tag not in valid_tags:
            type_attr = end_die.attributes.get("DW_AT_type")
            if not type_attr:
                logging.warning(f"Skipping DIE at offset {current_die.offset} with no 'DW_AT_type'")
                return None, None
            ref_addr = type_attr.value + end_die.cu.cu_offset
            end_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
        return end_die, ref_addr

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

    def _get_member_offset(self, die) -> [int, int, int]:
        """Extracts the offset for a structure member.

        Args:
            die: The DIE of the structure member.

        Returns:
            int, int, int: The offset value, the bit_size (union) and bit offset (union).
        """
        offset = None
        bit_size = 0
        bit_offset = 0
        if "DW_AT_data_member_location" in die.attributes:
            data_member_location = die.attributes.get("DW_AT_data_member_location")
            if "DW_AT_bit_size" in die.attributes:
                bit_size = die.attributes.get("DW_AT_bit_size").value
                bit_offset = die.attributes.get("DW_AT_bit_offset").value
            offset = data_member_location.value
            if isinstance(offset, int):
                return offset, bit_size, bit_offset
            if isinstance(offset, ListContainer):
                offset = self._extract_address_from_expression(offset, die.cu.structs)
                return offset, bit_size, bit_offset
            else:
                logging.warning(f"Unknown data_member_location value: {offset}")
        return offset, bit_size, bit_offset

    def _process_array_type(self, end_die, member_name, offset):
        """Process array type members recursively.

        The easiest implementation is the array of primitives, which contains only primitives,
        e.g.: char my_array[10]. In this case, function _process_end_die(...) will return the
        variable 'members' with only one element. Considering multidimensional arrays, arrays of
        structs, and arrays of unions, the variable 'members' will have multiple elements, that should
        be considered when calculating the size of the main array element. Afterward, each element need
        to be added as single indexed element in the array_members variable.
        """
        members = {}
        array_members = {}
        array_size = self._get_array_length(end_die)
        base_type_die = self._get_base_type_die(end_die)
        self._process_end_die(members, base_type_die, member_name, offset)
        if members:
            idx_size = sum(item["byte_size"] for item in members.values())
            # Generate array variable
            array_members[member_name] = {
                "type": members[next(iter(members))]["type"] if len(members) == 1 else "array",
                "byte_size": array_size * idx_size,
                "bit_size": 0,
                "bit_offset": 0,
                "address_offset": offset,
                "array_size": array_size,  # Individual elements aren't arrays
                "valid_values": {}
            }

            # Generate array members, e.g.: array[0], array[1], ..., array[i]
            for i in range(array_size):
                for name, values in members.items():
                    element_name = name.replace(member_name, f"{member_name}[{i}]")
                    array_members[element_name] = values.copy()
                    array_members[element_name]["address_offset"] += i * idx_size

        return array_members

    def _process_end_die(self, members, child_die, parent_name, offset):
        """Process the current die according to its tag.

        A variable can be a primitive or can have multiple children, e.g., a struct or and array of structs.
        After calling this method, members is populated with details of the variable and its children.
        """
        end_die, type_ref_addr = self._get_end_die(child_die)
        if end_die is None:
            return

        nested_member = {}
        if end_die.tag == "DW_TAG_pointer_type":
            pass
        elif end_die.tag == "DW_TAG_enumeration_type":
            nested_member = self._process_enum_type(end_die, parent_name, offset)
        elif end_die.tag == "DW_TAG_array_type":
            nested_member = self._process_array_type(end_die, parent_name, offset)
        elif end_die.tag == "DW_TAG_structure_type":
            nested_member = self._process_structure_type(end_die, parent_name, offset)
        elif end_die.tag == "DW_TAG_union_type":
            nested_member = self._process_union_type(end_die, parent_name, offset)
        else:
            nested_member = self._process_base_type(end_die, parent_name, offset)

        members.update(nested_member)
        return

    @staticmethod
    def _process_enum_type(end_die, parent_name, offset):
        """Process an enum type variable and map its members."""
        enum_name_attr = end_die.attributes.get("DW_AT_name")
        enum_name = (
            enum_name_attr.value.decode("utf-8") if enum_name_attr else "anonymous_enum"
        )

        # Dictionary to store enum member names and values
        enum_members = {}
        for child in end_die.iter_children():
            if child.tag == "DW_TAG_enumerator":
                name_attr = child.attributes.get("DW_AT_name")
                value_attr = child.attributes.get("DW_AT_const_value")
                if name_attr and value_attr:
                    member_name = name_attr.value.decode("utf-8")
                    member_value = value_attr.value
                    enum_members[member_name] = member_value

        return {
            parent_name: {
                "type": f"enum {enum_name}",
                "byte_size": end_die.attributes.get("DW_AT_byte_size", 0).value,
                "bit_size" : 0,
                "bit_offset" : 0,
                "address_offset": offset,
                "array_size": 0,
                "valid_values": enum_members
            }
        }

    def _process_union_type(self, die, parent_name: str, offset=0):
        """Recursively extracts union members from a DWARF DIE."""
        members = {}
        for child_die in die.iter_children():
            member = {}
            if child_die.tag == "DW_TAG_member":
                member_name = parent_name
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name += "." + name_attr.value.decode("utf-8")
                self._process_end_die(member, child_die, member_name, offset)
                members.update(member)
        return members

    def _process_structure_type(self, die, parent_name: str, offset=0):
        """Recursively extracts structure members from a DWARF DIE, including arrays."""
        members = {}
        for child_die in die.iter_children():
            member = {}
            if child_die.tag == "DW_TAG_member":
                member_offset, bit_size, bit_offset = self._get_member_offset(child_die)
                if member_offset is None:
                    continue
                member_name = parent_name
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name += "." + name_attr.value.decode("utf-8")
                self._process_end_die(member, child_die, member_name, offset + member_offset)
                # in case of a union, here is the location where the bit size and offset are registered.
                # on later versions of DWARF, it is available on the base type.
                if bit_size:
                    member[member_name]["bit_size"] = bit_size
                    member[member_name]["bit_offset"] = bit_offset
                members.update(member)
        return members

    @staticmethod
    def _get_array_length(type_die):
        """Gets the length of an array type."""
        array_length = 0
        for child in type_die.iter_children():
            if child.tag == "DW_TAG_subrange_type":
                array_length_attr = child.attributes.get("DW_AT_upper_bound")
                if array_length_attr:
                    array_length = array_length_attr.value + 1
                    break
        return array_length

    @staticmethod
    def _process_base_type(end_die, parent_name, offset):
        """Process a base type variable."""
        type_name_attr = end_die.attributes.get("DW_AT_name")
        type_name = type_name_attr.value.decode("utf-8") if type_name_attr else "base unknown"
        byte_size_attr = end_die.attributes.get("DW_AT_byte_size")
        byte_size = byte_size_attr.value if byte_size_attr else None
        return {
            parent_name: {
                "type": type_name,
                "byte_size": byte_size,
                "bit_size": 0,
                "bit_offset": 0,
                "address_offset": offset,
                "array_size": 0,
                "valid_values": {}
            }
        }

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
                self._process_die(die)

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