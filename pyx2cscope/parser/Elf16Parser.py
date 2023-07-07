import logging
import subprocess
import re
from typing import List

from pyx2cscope.parser.Elf_Parser import ElfParser
from pyx2cscope.parser.Elf_Parser import VariableInfo
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set the desired logging level and stream

xc16_readelf_path = 'C:/Program Files/Microchip/xc16/v2.00/bin/xc16-readelf.exe' # TODO set the util for self set the exe https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script
class Elf16Parser(ElfParser):


    def __init__(self, elf_path):
        """
        Initialize the Elf16Parser.

        Args:
            xc16_readelf_path (str): Path to the xc16-readelf executable.
            elf_path (str): Path to the input ELF file.
        """
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
            "Pointer Size": int(next(self.tree_string).split(":")[1].strip())
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
                # Remove the indirect string part and leading whitespace

                value = re.sub(r'\(indirect string, offset: 0x[0-9a-fA-F]+\):', '', value).strip()
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
            offset = int(self.next_line.split('@')[1].strip()[:-1], 16)
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
        command = [self.xc16_readelf_path, '-w', self.input_elf_file]

        # Execute the command and capture the output
        try:
            output = subprocess.check_output(command, universal_newlines=True)
            self._parse_tree(output)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing xc16-readelf.exe: {e}")
            return

    @staticmethod
    def _get_structure_member_offset(location: str):
        hex_offset = location.split(":")[2][0:-1].strip()
        return int(hex_offset, 16)

    def _get_structure_members(self, structure_die):
        members = {}
        cu_sibling = None
        for cu_offset, cu in self.dwarf_info.items():
            if not (cu_offset < structure_die["offset"] < (cu_offset + cu["length"])):
                continue
            cu_sibling = int(cu["elements"][structure_die["offset"]]["DW_AT_sibling"][1:-1], 16)
            break
        for cu_offset, cu_structure_member in cu["elements"].items():
            if cu_offset <= structure_die["offset"]:
                continue
            if cu_offset == cu_sibling:
                break
            end_die = self.get_end_die(cu_structure_member)
            try:
                address = self._get_structure_member_offset(cu_structure_member["DW_AT_data_member_location"])
                member = {
                    cu_structure_member["DW_AT_name"]: {
                        "address_offset": address,
                        "type": end_die["DW_AT_name"],
                        "byte_size": end_die["DW_AT_byte_size"]
                    }
                }
            except Exception as e:
                # there are some missing values
                # this will be addressed on future versions
                # print(structure_die)
                continue
            members.update(member)
        return members

    def get_var_list(self) -> List[str]:
        my_list = []
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                if "DW_TAG_variable" in die["tag"] and 'DW_AT_location' in die and self._get_address_check(die["DW_AT_location"]) > 2 :
                    end_die = self.get_end_die(die)
                    if end_die["tag"] == "DW_TAG_structure_type" and 'DW_AT_location' in die:
                        members = self._get_structure_members(end_die)
                        for member in members.keys():
                            my_list.append(die["DW_AT_name"]+"."+member)

                    # elif end_die["tag"] == "DW_TAG_pointer_type":
                    #     my_list.append(die["DW_AT_name"])
                    else:
                        my_list.append(die["DW_AT_name"])
        my_list.insert(0,"")

        return sorted(my_list)

    @staticmethod
    def _get_address_check(location: str) -> int:
        address_start = location.find(':') + 1  # Find the start position of the address
        address_end = location.find('(')  # Find the end position of the address
        address = location[address_start:address_end].strip()  # Extract the address

        address = address[1:]
        bytes_list = re.findall(r'[0-9a-fA-F]+', address)
        bytes_list.reverse()

        # Add leading zero for single-digit bytes
        bytes_list = [byte.zfill(2) for byte in bytes_list]
        return len(bytes_list)



    @staticmethod
    def _get_address_location(location: str) -> int:
        address_start = location.find(':') + 1  # Find the start position of the address
        address_end = location.find('(')  # Find the end position of the address
        address = location[address_start:address_end].strip()  # Extract the address
        address = address[1:]
        bytes_list = re.findall(r'[0-9a-fA-F]+', address)
        bytes_list.reverse()

        # Add leading zero for single-digit bytes
        bytes_list = [byte.zfill(2) for byte in bytes_list]

        hex_string = ''.join(bytes_list)
        return int(hex_string, 16)

    def get_var_info(self, var_name) -> VariableInfo:
        """
        Get the information of a variable by name.

        Args:
            var_name (str): The name of the variable.

        Returns:
            VariableInfo: An object containing the variable information.
        """
        variable_name, member_name = var_name.split('.') if "." in var_name else (var_name, None)
        die_var = None
        ref_address = None
        variable_die = None
        for cu_offset, cu in self.dwarf_info.items():
            for die_offset, die in cu["elements"].items():
                if "DW_TAG_variable" in die["tag"]:
                    if die["DW_AT_name"] == variable_name:
                        die_var = die
                        ref_address = die["DW_AT_type"]
        assert die_var is not None, "Variable not found!"
        for cu_offset, cu in self.dwarf_info.items():
            if cu_offset < ref_address < (cu_offset + cu["length"]):
                variable_die = cu["elements"][ref_address]
        end_die = self.get_end_die(variable_die)
        address = self._get_address_location(die_var['DW_AT_location'])

        # If the address already includes the "0x" prefix, you can skip the above code and directly use:
        # address = location[address_start:address_end].strip()
        #if not "DW_AT_name" in end_die or end_die["DW_AT_name"] == "_SCCP3_TMR_OBJ_STRUCT" or end_die["DW_AT_name"] == "_SCCP1_TMR_OBJ_STRUCT": # TODO setup this part
       # NO need to check for the avaibility of DW_AT_name
        if end_die["tag"] == "DW_TAG_pointer_type":
            variabledata = VariableInfo(
                name=die_var['DW_AT_name'],
                byte_size=end_die["DW_AT_byte_size"],
                type='pointer',
                address=address
            )
        elif end_die["tag"] == "DW_TAG_structure_type":
            members = self._get_structure_members(end_die)
            member = members[member_name]
            variabledata = VariableInfo(
                name=die_var['DW_AT_name'] + "." + member_name,
                byte_size=member["byte_size"],
                type=member["type"],
                address=address+(member["address_offset"])
            )
        else:
            variabledata = VariableInfo(
                name=die_var["DW_AT_name"],
                byte_size=end_die["DW_AT_byte_size"],
                type=end_die["DW_AT_name"],
                address=address
            )
        return variabledata

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
        if start_die["tag"] in ["DW_TAG_base_type", "DW_TAG_pointer_type", "DW_TAG_structure_type"]:
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


if __name__ == '__main__':


    input_elf_file =   'C:\_DESKTOP\_Projects\AN1160_dsPIC33CK256MP508_MCLV2_MCHV\\bldc_MCLV2.X\dist\MCLV2\production/bldc_MCLV2.X.production.elf'
    elf_reader = Elf16Parser(input_elf_file)

    variable_name = 'sccp3_timer_obj.secondaryTimer16Elapsed'
    #variable_name = 'V_pot'
    #variable_name = 'DesiredSpeed'
    variable_list = elf_reader.get_var_list()
    variable_data = elf_reader.get_var_info(variable_name)
    print(variable_data.name)
    print(variable_data.byte_size)
    print(variable_data.type)
    print(variable_data.address)
    #print(variabledata.members)
    #print(variabledata.members.items())

