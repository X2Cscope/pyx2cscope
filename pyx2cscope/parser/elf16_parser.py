"""(Deprecated) ELF16 Parser for Microchip's XC16 Compiler.

This module is deprecated and will be removed in future versions.

This module defines the `Elf16Parser` class for parsing ELF files generated by Microchip's XC16 compiler.
The parser extracts useful information about variables defined in the compiled program.

Usage:
    elf_reader = Elf16Parser(elf_file)
    variable_map = elf_reader.map_variables()
    print(variable_map)
"""
import logging
import os.path
import re
import subprocess
import warnings
from shutil import which

from pyx2cscope.parser.elf_parser import ElfParser
from pyx2cscope.variable.variable import VariableInfo

# Constants for magic values
ADDRESS_CHECK_LOWER_LIMIT = 2
ADDRESS_CHECK_UPPER_LIMIT = 6


#@warnings.deprecated
class Elf16Parser(ElfParser):
    """Class for parsing ELF files generated by Microchip's XC16 compiler.

    This class extends the basic ElfParser to specifically handle ELF files produced by the XC16 compiler,
    extracting useful information about variables defined in the compiled program.
    Deprecation warning: This class will not be continued.
    Use the new generic Class Generic_Parser instead.

    Attributes:
        xc16_read_elf_path (str): Path to the XC16 `readelf` executable.
    """


    def __init__(self, elf_path):
        """Initialize the Elf16Parser instance.

        Args:
        elf_path (str): Path to the input ELF file.

        Raises:
        ValueError: If the XC16 compiler is not found in the local directory or on the system path.
        """
        # Check if the xc16-readelf executable exists in the current directory
        warnings.warn("Do not use this class for new development, it will be discontinued")
        local_readelf = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "xc16-readelf"
        )

        logging.warning("Do not use this class for new development, it will be discontinued.")

        # Checking if the xc16-readelf executable exists in the same directory as the script or executable
        if os.path.exists(local_readelf):
            self.xc16_read_elf_path = local_readelf
        else:
            # Fallback to checking if xc16-readelf is on the system path
            self.xc16_read_elf_path = which("xc16-readelf")
            if self.xc16_read_elf_path is None or not os.path.exists(
                    self.xc16_read_elf_path
            ):
                raise ValueError(
                    "XC16 compiler not found. Ensure xc16-readelf is in the same folder or listed on PATH."
                )

        super().__init__(elf_path)
        self.tree_string = None
        self.next_line = None

    def _load_symbol_table(self):
        """Load symbol tables.

        This method exists at this class only for compatibility.
        This class is deprecated and not maintained on current version.
        """
        pass

    def _close_elf_file(self):
        pass

    def _parse_cu_attributes(self):
        """Parse the attributes of a compilation unit from the ELF file.

        Returns:
            dict: A dictionary containing parsed attributes of the compilation unit.
        """
        return {
            "length": int(next(self.tree_string).split(":")[1].strip()),
            "version": next(self.tree_string).split(":")[1].strip(),
            "Abbrev Offset": int(next(self.tree_string).split(":")[1].strip()),
            "Pointer Size": int(next(self.tree_string).split(":")[1].strip()),
        }

    def _parse_cu_header(self):
        """Parse the header of a compilation unit.

        Returns:
            dict: A dictionary containing parsed header information.
        """
        items = self.next_line.split(":")
        offset = int(items[0].split("<")[2][:-1], 16)
        tag = items[-1].split("(")[1].strip()[:-1]
        return {"offset": offset, "tag": tag}

    def _parse_cu_members(self):
        """Parse the members of a compilation unit.

        Returns:
            dict: A dictionary containing parsed members of the compilation unit.
        """
        members = {}
        self.next_line = next(self.tree_string)
        while "DW_AT" in self.next_line:
            values = self.next_line.split(":")

            key = values[0].strip()
            value = ":".join(values[1:]).strip()
            if key == "DW_AT_name":
                # Remove the indirect string part and leading space
                value = re.sub(
                    r"\(indirect string, offset: 0x[0-9a-fA-F]+\):", "", value
                ).strip()
            value = int(value[1:-1], 16) if key == "DW_AT_type" else value

            members.update({key: value})
            self.next_line = next(self.tree_string)
        return members

    def _parse_cu_elements(self):
        """Parse the elements of a compilation unit.

        Returns:
            dict: Dictionary containing the parsed elements.
        """
        cu_elements = {}
        self.next_line = next(self.tree_string)
        while "abbrev number" in self.next_line.lower():
            header = self._parse_cu_header()
            members = self._parse_cu_members()
            members.update(header)
            cu_elements.update({header["offset"]: members})
        return cu_elements

    def _parse_cu(self):
        """Parse a compilation unit."""
        while "compilation unit" in self.next_line.lower():
            offset = int(self.next_line.split("@")[1].strip()[:-1], 16)
            attributes = self._parse_cu_attributes()
            elements = self._parse_cu_elements()
            cu = {offset: {**attributes, "elements": elements}}
            self.dwarf_info.update(cu)

    def _parse_tree(self, tree_string):
        """Parse the entire tree string of the ELF file.

        Args:
            tree_string (str): The tree string to parse.
        """
        self.tree_string = iter(tree_string.split("\n"))
        for self.next_line in self.tree_string:
            self._parse_cu()

    def _load_elf_file(self):
        """Load the ELF file and parse its contents."""
        # Construct the command
        command = [self.xc16_read_elf_path, "-w", self.elf_path]

        # Execute the command and capture the output
        try:
            output = subprocess.check_output(command, universal_newlines=True)
            self._parse_tree(output)
        except subprocess.CalledProcessError:
            raise Exception("Error loading ELF file: {}".format(self.elf_path))

    @staticmethod
    def _get_structure_member_offset(location: str):
        """Extract the offset of a structure member from its location string.

        Args:
            location (str): Location string of the member.

        Returns:
            int: Offset of the member.
        """
        # Split the location string by '(' to isolate the part containing the offset
        offset_part = location.split("(")[-1].strip()

        # Extract digits from the offset part using regular expression
        offset_digits = re.findall(r"\d+", offset_part)

        # Join the extracted digits to form the offset as a string
        offset_value = "".join(offset_digits)

        return int(offset_value)

    def _locate_cu_in_dwarf(self, structure_die):
        """Locate the corresponding compilation unit in the DWARF information.

        Args:
            structure_die (dict): Dictionary representing a DWARF DIE for a structure.

        Returns:
            tuple: A tuple containing the compilation unit and its sibling
        """
        cu = None
        cu_sibling = None
        for cu_offset, cu in self.dwarf_info.items():
            if not (cu_offset < structure_die["offset"] < (cu_offset + cu["length"])):
                continue
            cu_sibling = int(
                cu["elements"][structure_die["offset"]]["DW_AT_sibling"][1:-1], 16
            )
            break
        return cu, cu_sibling

    def _get_member_from_nested_members(
            self, parent_address, nested_member, cu_structure
    ):
        """Extract information about a structure member from nested members.

        Args:
            parent_address (int): Address of the parent structure.
            nested_member (tuple): Nested structure member information.
            cu_structure (dict): DWARF DIE representing a structure.

        Returns:
            dict: Dictionary containing information about the structure member.
        """
        member_info = nested_member[1]
        member_address = cu_structure["DW_AT_data_member_location"]
        member_address_offset = (
                parent_address
                + self._get_structure_member_offset(member_address)
                + member_info["address_offset"]
        )
        member = {
            cu_structure["DW_AT_name"]
            + "."
            + nested_member[0]: {
                "address_offset": member_address_offset,
                "type": member_info["type"],
                "byte_size": member_info["byte_size"],
                "array_size": member_info["array_size"],
            }
        }
        return member

    def _get_structure_members(self, structure_die, parent_address=0):
        """Recursively get all members of a structure.

        Args:
            structure_die (dict): DWARF DIE representing the structure.
            parent_address (int): Address of the parent structure.

        Returns:
            dict: Dictionary containing all structure members.
        """
        members = {}
        # Locate the structure DIE inside the DWARFInfo regarding its offset
        # We define here the correct CU.
        # It's offset on the DWARF and the next sibling to be used as the stop condition.
        cu, cu_sibling = self._locate_cu_in_dwarf(structure_die)
        # List all the members of the CU, if the member is a structure type, calling this function recursively.
        for cu_offset, cu_structure_member in cu["elements"].items():
            if cu_offset <= structure_die["offset"]:
                continue
            if cu_offset == cu_sibling:
                break

            end_die = self._get_end_die(cu_structure_member)
            try:
                if end_die["tag"] == "DW_TAG_structure_type":
                    # Handle nested structures recursively
                    nested_members = self._get_structure_members(
                        end_die, parent_address
                    )
                    for nested_member in nested_members.items():
                        members.update(
                            self._get_member_from_nested_members(
                                parent_address, nested_member, cu_structure_member
                            )
                        )
                else:
                    address = parent_address + self._get_structure_member_offset(
                        cu_structure_member["DW_AT_data_member_location"]
                    )
                    member = {
                        cu_structure_member["DW_AT_name"]: {
                            "address_offset": address,
                            "type": end_die["DW_AT_name"],
                            "byte_size": end_die["DW_AT_byte_size"],
                            "array_size": self.calculate_array_size(
                                array_die=cu_structure_member
                            ),
                        }
                    }
                    members.update(member)
            except Exception:
                # there are some missing values
                # this will be addressed in future versions
                continue
        return members

    @staticmethod
    def _get_address_check(location: str) -> int:
        """Get address check value from a location string.

        Args:
            location (str): Location string.

        Returns:
            int: Address check value.
        """
        address_start = location.find(":") + 1  # Find the start position of the address
        address_end = location.find("(")  # Find the end position of the address
        address = location[address_start:address_end].strip()  # Extract the address

        address = address[1:]
        bytes_list = re.findall(r"[0-9a-fA-F]+", address)
        bytes_list.reverse()

        # Add leading zero for single-digit bytes
        bytes_list = [byte.zfill(2) for byte in bytes_list]
        return len(bytes_list)

    @staticmethod
    def _get_address_location(location: str) -> int:
        """Extract address location from a location string.

        Args:
            location (str): Location string.

        Returns:
            int: Address location.
        """
        address_start = location.find(":") + 1  # Find the start position of the address
        address_end = location.find("(")  # Find the end position of the address
        address = location[address_start:address_end].strip()  # Extract the address
        address = address[1:]
        bytes_list = re.findall(r"[0-9a-fA-F]+", address)
        bytes_list.reverse()

        # Add leading zero for single-digit bytes
        bytes_list = [byte.zfill(2) for byte in bytes_list]

        hex_string = "".join(bytes_list)
        return int(hex_string, 16)

    def _locate_tag_variable_end_die(self, die):
        """Locate the end DIE of a variable tag.

        Args:
            die (dict): Dictionary representing a DWARF DIE.

        Returns:
            dict: Dictionary representing the end DIE.
        """
        if (
                "DW_TAG_variable" in die["tag"]
                and "DW_AT_location" in die
                and ADDRESS_CHECK_LOWER_LIMIT
                < self._get_address_check(die["DW_AT_location"])
                < ADDRESS_CHECK_UPPER_LIMIT
        ):
            return self._get_end_die(die)
        return None

    def _check_for_pointer_tag(self, die, end_die, address):
        """Check if a DIE represents a pointer tag.

        Args:
            die (dict): Dictionary representing a DWARF DIE.
            end_die (dict): Dictionary representing the end DIE.
            address (int): Address of the DIE.

        Returns:
            bool: True if it's a pointer tag, False otherwise.
        """
        if end_die["tag"] != "DW_TAG_pointer_type":
            return False
        variable_data = VariableInfo(
            name=die["DW_AT_name"],
            type="pointer",
            byte_size=end_die["DW_AT_byte_size"],
            address=address,
            array_size=0,
            valid_values = {}
        )
        self.variable_map[die["DW_AT_name"]] = variable_data
        return True

    def _check_for_structure_tag(self, die, end_die, address):
        """Check if a DIE represents a structure tag.

        Args:
            die (dict): Dictionary representing a DWARF DIE.
            end_die (dict): Dictionary representing the end DIE.
            address (int): Address of the DIE.

        Returns:
            bool: True if it's a structure tag, False otherwise.
        """
        # the DW_AT_location confirms its global Structure and not a local one
        if end_die["tag"] == "DW_TAG_structure_type" and "DW_AT_location" in die:
            members = self._get_structure_members(end_die)
            if members is None:
                # Return the entire structure as a single variable
                variable_data = VariableInfo(
                    name=die["DW_AT_name"],
                    type=end_die["DW_AT_name"],
                    byte_size=end_die["DW_AT_byte_size"],
                    address=address,
                    array_size=0,
                    valid_values={}
                )
                self.variable_map[die["DW_AT_name"]] = variable_data
            if members:
                for member, member_info in members.items():
                    member_name = die["DW_AT_name"] + "." + member
                    variable_data = VariableInfo(
                        name=member_name,
                        byte_size=member_info.get("byte_size"),
                        type=member_info.get("type"),
                        address=address + (member_info.get("address_offset")),
                        array_size=member_info.get("array_size"),
                        valid_values={}
                    )
                    self.variable_map[member_name] = variable_data
                    # Reset array attributes for each variable
                    self.array_size = 0
            return True
        return False

    def _get_end_die(self, start_die):
        """Get the end die of a given die.

        Args:
            start_die (dict): The starting die.

        Returns:
            dict: The end dies.
        """
        if start_die is None:
            return None
        if start_die["tag"] in [
            "DW_TAG_base_type",
            "DW_TAG_pointer_type",
            "DW_TAG_structure_type",
        ]:
            return start_die
        if "DW_AT_type" in start_die:
            type_offset = start_die["DW_AT_type"]
            type_die = self._get_dwarf_die_by_offset(type_offset)
            #     if type_die["tag"] == "DW_TAG_array_type":
            #         print(start_die)
            #         self.array_size = self.calculate_array_size(type_die)
            return self._get_end_die(type_die)
        return None

    def _get_next_die_by_offset(self, offset):
        take_next = False
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                if take_next:
                    return die
                if die_offset == offset:
                    take_next = True

    def calculate_array_size(self, array_die):
        """Calculate the size of an array.

        This method retrieves the array type DIE and calculates the size based on its upper bound.

        Args:
            array_die (dict): The DWARF DIE representing the array.

        Returns:
            int: The size of the array.
        """
        type_offset = array_die["DW_AT_type"]
        type_die = self._get_dwarf_die_by_offset(type_offset)
        if type_die["tag"] == "DW_TAG_array_type":
            # Retrieve the array type DIE
            die = self._get_next_die_by_offset(type_die["offset"])
            try:
                upper_bound = int(die.get("DW_AT_upper_bound"))

                return upper_bound + 1  # Assuming 0-based indexing
            except Exception:
                print(array_die)
        else:
            return 0

    def _get_dwarf_die_by_offset(self, offset):
        """Get a DWARF die by offset.

        Args:
            offset: The offset of the die.

        Returns:
            dict: The DWARF dies.
        """
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                if die_offset == offset:
                    return die
        return None

    def _map_variables(self) -> dict[str, VariableInfo]:
        """Map variables from the DWARF information.

        Returns:
            dict: A dictionary mapping variable names to their information.
        """
        self.variable_map.clear()
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                end_die = self._locate_tag_variable_end_die(die)
                if end_die is None:
                    continue
                address = None
                if "DW_AT_location" in die:
                    address = self._get_address_location(die.get("DW_AT_location"))
                # else:
                #     # Check symbol table if DW_AT_location is not present
                #     address = self.symbol_table.get(die["DW_AT_name"], None)

                if address is None:
                    continue  # Skip variables without an address

                if not self._check_for_pointer_tag(
                        die, end_die, address
                ) and not self._check_for_structure_tag(die, end_die, address):
                    variable_data = VariableInfo(
                        name=die["DW_AT_name"],
                        byte_size=end_die["DW_AT_byte_size"],
                        type=end_die["DW_AT_name"],
                        address=address,
                        array_size=self.calculate_array_size(die),
                        valid_values={}
                    )
                    self.variable_map[die["DW_AT_name"]] = variable_data
        return self.variable_map


if __name__ == "__main__":
    elf_file = r"..\..\tests\data\MCAF_ZSMT_dsPIC33CK.elf"
    # elf_file = r"..\..\tests\data\mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    # logging.basicConfig(level=logging.DEBUG)  # Set the desired logging level and stream
    elf_reader = Elf16Parser(elf_file)
    variable_map = elf_reader.map_variables()
    print(variable_map)
    vars_to_remove = [var_name for var_name, var_info in variable_map.items() if var_info.address is None]

    # Remove the variables with no address from the map
    for var_name in vars_to_remove:
        variable_map.pop(var_name)

    print(variable_map)

    # Remove the variables with no address from the map
    for var_name in vars_to_remove:
        variable_map.pop(var_name)

    print(variable_map)