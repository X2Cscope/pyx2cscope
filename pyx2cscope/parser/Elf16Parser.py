import logging
import re
import subprocess
from typing import List

from pyx2cscope.parser.Elf_Parser import ElfParser, VariableInfo

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set the desired logging level and stream

xc16_readelf_path = "C:/Program Files/Microchip/xc16/v2.00/bin/xc16-readelf.exe"
# TODO set the util for self set the exe
#  https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script


class Elf16Parser(ElfParser):
    def __init__(self, elf_path):
        """
        Initialize the Elf16Parser.

        Args:
            self.xc16_readelf_path (str): Path to the xc16-readelf executable.
            elf_path (str): Path to the input ELF file.
        """
        self.variable_mapping = {}
        self.xc16_readelf_path = xc16_readelf_path
        self.input_elf_file = elf_path
        self.dwarf_info = {}
        self.tree_string = ""
        self.next_line = ""
        self.read_elf_file()

    def _parse_cu_attributes(self):
        """
        Parse the attributes of a compilation unit.

        Returns:
            dict: Dictionary containing the parsed attributes.
        """
        return {
            "length": int(next(self.tree_string).split(":")[1].strip()),
            "version": next(self.tree_string).split(":")[1].strip(),
            "Abbrev Offset": int(next(self.tree_string).split(":")[1].strip()),
            "Pointer Size": int(next(self.tree_string).split(":")[1].strip()),
        }

    def _parse_cu_header(self):
        """
        Parse the header of a compilation unit.

        Returns:
            dict: Dictionary containing the parsed header information.
        """
        items = self.next_line.split(":")
        offset = int(items[0].split("<")[2][:-1], 16)
        tag = items[-1].split("(")[1].strip()[:-1]
        return {"offset": offset, "tag": tag}

    def _parse_cu_members(self):
        """
        Parse the members of a compilation unit.

        Returns:
            dict: Dictionary containing the parsed members.
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
        """
        Parse the elements of a compilation unit.

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
        """
        Parse a compilation unit.
        """
        while "compilation unit" in self.next_line.lower():
            offset = int(self.next_line.split("@")[1].strip()[:-1], 16)
            attributes = self._parse_cu_attributes()
            elements = self._parse_cu_elements()
            cu = {offset: {**attributes, "elements": elements}}
            self.dwarf_info.update(cu)

    def _parse_tree(self, tree_string):
        """
        Parse the tree string.

        Args:
            tree_string (str): The tree string to parse.
        """
        self.tree_string = iter(tree_string.split("\n"))
        for self.next_line in self.tree_string:
            self._parse_cu()

    def read_elf_file(self):
        """
        Read the ELF file and parse the DWARF information.
        """
        # Construct the command
        command = [self.xc16_readelf_path, "-w", self.input_elf_file]

        # Execute the command and capture the output
        try:
            output = subprocess.check_output(command, universal_newlines=True)
            self._parse_tree(output)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing xc16-readelf.exe: {e.output}")
            return

    @staticmethod
    def _get_structure_member_offset(location: str):
        # Split the location string by '(' to isolate the part containing the offset
        offset_part = location.split("(")[-1].strip()

        # Extract digits from the offset part using regular expression
        offset_digits = re.findall(r"\d+", offset_part)

        # Join the extracted digits to form the offset as a string
        offset_value = "".join(offset_digits)

        return int(offset_value)

    def _locate_cu_in_dwarf(self, structure_die):
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
            }
        }
        return member

    def _get_structure_members(self, structure_die, parent_address=0):
        members = {}
        cu_sibling = None
        # Locate the structure DIE inside the DWARFInfo regarding its offset
        # We define here the correct CU, it's offset on the DWARF and the next sibling to be used as the stop condition.
        cu, cu_sibling = self._locate_cu_in_dwarf(structure_die)
        # List all the members of the CU, if the member is structure type, calling this function recursively.
        for cu_offset, cu_structure_member in cu["elements"].items():
            if cu_offset <= structure_die["offset"]:
                continue
            if cu_offset == cu_sibling:
                break

            end_die = self.get_end_die(cu_structure_member)
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
                        }
                    }
                    members.update(member)
            except Exception:
                # there are some missing values
                # this will be addressed in future versions
                continue
        return members

    def get_var_list(self) -> List[str]:
        return sorted(self.variable_mapping.keys(), key=lambda x: x.lower())

    @staticmethod
    def _get_address_check(location: str) -> int:
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
        if (
            "DW_TAG_variable" in die["tag"]
            and "DW_AT_location" in die
            and 2 < self._get_address_check(die["DW_AT_location"]) < 6
        ):
            return self.get_end_die(die)
        return None

    def _check_for_pointer_tag(self, die, end_die, address):
        if end_die["tag"] != "DW_TAG_pointer_type":
            return False
        _variabledata = VariableInfo(
            name=die["DW_AT_name"],
            byte_size=end_die["DW_AT_byte_size"],
            type="pointer",
            address=address,
        )
        self.variable_mapping[die["DW_AT_name"]] = _variabledata
        return True

    def _check_for_structure_tag(self, die, end_die, address):
        if end_die["tag"] == "DW_TAG_structure_type" and "DW_AT_location" in die:
            members = self._get_structure_members(end_die)
            if members is None:
                # Return the entire structure as a single variable
                variable_data = VariableInfo(
                    name=die["DW_AT_name"],
                    byte_size=end_die["DW_AT_byte_size"],
                    type=end_die["DW_AT_name"],
                    address=address,
                )
                self.variable_mapping[die["DW_AT_name"]] = variable_data
            if members:
                for member, member_info in members.items():
                    member_name = die["DW_AT_name"] + "." + member
                    variable_data = VariableInfo(
                        name=member_name,
                        byte_size=member_info.get("byte_size"),
                        type=member_info.get("type"),
                        address=address + (member_info.get("address_offset")),
                    )
                    self.variable_mapping[member_name] = variable_data
            return True
        return False

    def get_var_info(self) -> dict:
        """
        Get the information of a variable by name.

        Args:
            var_name (str): The name of the variable.

        Returns:
            VariableInfo: An object containing the variable information.
        """

        self.variable_mapping.clear()
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                end_die = self._locate_tag_variable_end_die(die)
                if end_die is None:
                    continue

                address = self._get_address_location(die.get("DW_AT_location"))
                if not self._check_for_pointer_tag(
                    die, end_die, address
                ) and not self._check_for_structure_tag(
                    die, end_die, address
                ):
                    variable_data = VariableInfo(
                        name=die["DW_AT_name"],
                        byte_size=end_die["DW_AT_byte_size"],
                        type=end_die["DW_AT_name"],
                        address=address,
                    )
                    self.variable_mapping[die["DW_AT_name"]] = variable_data
        return self.variable_mapping

    def get_end_die(self, start_die):
        """
        Get the end die of a given die.

        Args:
            start_die (dict): The starting die.

        Returns:
            dict: The end die.
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
            type_die = self.get_dwarf_die_by_offset(type_offset)
            return self.get_end_die(type_die)
        return None

    def get_dwarf_die_by_offset(self, offset):
        """
        Get a DWARF die by offset.

        Args:
            offset: The offset of the die.

        Returns:
            dict: The DWARF die.
        """
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                if die_offset == offset:
                    return die
        return None

    def map_all_variables_data(self) -> dict:
        return self.get_var_info()


if __name__ == "__main__":
    input_elf_file = (
        "C:\\_DESKTOP\\_Projects\\AN1160_dsPIC33CK256MP508_MCLV2_MCHV\\bldc_MCLV2.X\\dist\\MCLV2"
        "\\production\\bldc_MCLV2.X.production.elf"
    )
    # input_elf_file = "C:\\_DESKTOP\\_Projects\\Ceiling fan project\\AN1299_dsPIC33CK64MC102_LVCFRD
    # \\pmsm.X\\dist\\default\\production\\pmsm.X.production.elf"
    input_elf_file = (
        r"C:\_DESKTOP\_Projects\Motorbench_Projects\AN1292-42BLF02-mb-33ck256mp508.X\dist"
        r"\default\production\AN1292-42BLF02-mb-33ck256mp508.X.production.elf"
    )
    elf_reader = Elf16Parser(input_elf_file)

    # variable = "sccp3_timer_obj.secondaryTimer16Elapsed"
    variable = "adcDataBuffer"
    # variable_name = 'V_pot'
    # variable_name = 'DesiredSpeed'

    variable_info_map = elf_reader.map_all_variables_data()
    print(elf_reader.get_var_list())
    # print(variable_info_map)
    # print(variable_info_map.get("motor.potInput"))
    # print(variable_info_map.get("motor.estimator.pll.sincos.sin"))
    # variableList = elf_reader.get_var_list()
    # print(variable_info_map)
    # print(variableList)
