from typing import List

from elftools.elf.elffile import ELFFile

from pyx2cscope.parser.Elf_Parser import ElfParser, VariableInfo


class Elf32Parser(ElfParser):
    def __init__(self, elf_path):
        """
        Initialize the DwarfParser with the path to the ELF file.

        Args:
            elf_path (str): Path to the ELF file.
        """
        self.elf_path = elf_path
        self.dwarf_info = None
        self.elf_file = None
        self.load_elf_file()
        # self.variables = self.get_variable_list()

    def _get_structure_members(self, structure_die):
        members = {}
        prev_address_offset = 0
        for child_die in structure_die.iter_children():
            if child_die.tag == "DW_TAG_member":
                member = {}
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name = name_attr.value.decode("utf-8")
                type_attr = child_die.attributes.get("DW_AT_type")
                if type_attr:
                    type_offset = type_attr.value + child_die.cu.cu_offset
                    try:
                        member_type = self._get_member_type(type_offset)
                    except Exception:
                        # there are some missing fields
                        # it will be handled on future versions
                        continue
                    if member_type:
                        member["type"] = member_type["name"]
                        member["byte_size"] = member_type["byte_size"]
                        member["address_offset"] = prev_address_offset
                        prev_address_offset += int(member_type["byte_size"])
                members[member_name] = member
        return members

    def get_var_list(self) -> List[str]:
        my_list = []
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            tag_variables = list(
                filter(
                    lambda die: die.tag == "DW_TAG_variable"
                    and "DW_AT_location" in die.attributes
                    and isinstance(die.attributes["DW_AT_location"].value, List)
                    and len(die.attributes["DW_AT_location"].value) > 2,
                    root_die,
                )
            )
            die_variables = list(
                filter(
                    lambda die: die.attributes.get("DW_AT_name") is not None,
                    tag_variables,
                )
            )
            for die_variable in die_variables:
                end_die = self.get_end_die(die_variable)
                if end_die.tag == "DW_TAG_structure_type":
                    members = self._get_structure_members(end_die)
                    for member in members.keys():
                        my_list.append(
                            die_variable.attributes["DW_AT_name"].value.decode("utf-8")
                            + "."
                            + member
                        )
                else:
                    my_list.append(
                        die_variable.attributes["DW_AT_name"].value.decode("utf-8")
                    )
        #my_list.insert(0, "")
        return sorted(my_list)

    def get_var_info(self, var_name) -> VariableInfo:
        """
        Parse the DWARF information for a specific variable.s

        Args:
            var_name (str): Name of the variable.

        Returns:
            VariableInfo or None: Variable information if found, None otherwise.
        """
        variable_name, member_name = (
            var_name.split(".") if "." in var_name else (var_name, None)
        )
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            tag_variables = filter(lambda die: die.tag == "DW_TAG_variable", root_die)
            die_variables = list(
                filter(
                    lambda die: die.attributes.get("DW_AT_name") is not None
                    and die.attributes.get("DW_AT_name").value.decode("utf-8")
                    == variable_name,
                    tag_variables,
                )
            )
            if die_variables:
                assert len(die_variables) == 1, "Multiple variables found"
                die_variable = die_variables[0]
                ref_addr = (
                    die_variable.attributes.get("DW_AT_type").value
                    + die_variable.cu.cu_offset
                )
                type_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
                end_die = self.get_end_die(type_die)
                try:
                    data = list(die_variable.attributes["DW_AT_location"].value)[1:]
                    address = int.from_bytes(bytes(data), byteorder="little")
                except Exception as e:
                    print(e)

                if end_die.tag == "DW_TAG_pointer_type":
                    type_name = "pointer"
                    return VariableInfo(
                        name=die_variable.attributes["DW_AT_name"].value.decode(
                            "utf-8"
                        ),
                        byte_size=end_die.attributes["DW_AT_byte_size"].value,
                        type=type_name,
                        address=address,
                    )
                elif end_die.tag == "DW_TAG_structure_type":
                    members = self._get_structure_members(end_die)
                    member = members[member_name]
                    return VariableInfo(
                        name=die_variable.attributes["DW_AT_name"].value.decode("utf-8")
                        + "."
                        + member_name,
                        byte_size=member["byte_size"],
                        type=member["type"],
                        address=address + member["address_offset"],
                    )

                return VariableInfo(
                    name=die_variable.attributes["DW_AT_name"].value.decode("utf-8"),
                    byte_size=end_die.attributes["DW_AT_byte_size"].value,
                    type=end_die.attributes["DW_AT_name"].value.decode("utf-8"),
                    address=address,
                )
        return None

    # def get_variable_list(self) -> List[VariableInfo]:
    #     variable_names = []
    #     for compilation_unit in self.dwarf_info.iter_CUs():
    #         root_die = compilation_unit.iter_DIEs()
    #         tag_variables = filter(lambda die: die.tag == 'DW_TAG_variable', root_die)
    #         variable_names = [
    #             VariableInfo(name=die.attributes.get('DW_AT_name').value.decode('utf-8'))
    #             for die in tag_variables
    #             if die.attributes.get('DW_AT_name') is not None
    #         ]
    #         for var in variable_names:
    #             print(var.name)
    #     return variable_names

    def load_elf_file(self):
        """
        Load the ELF file and extract the DWARF information.
        """
        try:
            with open(self.elf_path, "rb") as stream:
                self.elf_file = ELFFile(stream)
                self.dwarf_info = self.elf_file.get_dwarf_info()
        except IOError:
            raise Exception("Error loading ELF file: {}".format(self.elf_path))

    def get_dwarf_die_by_offset(self, offset):
        """
        Retrieve the DWARF DIE given an offset.

        Args:
            offset (int): Offset of the DIE.

        Returns:
            elftools.dwarf.die.DIE or None: The DWARF DIE if found, or None if not found.
        """
        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            for die in root_die:
                if die.offset == offset:
                    return die
        return None

    def get_end_die(self, current_die):
        """
        Find the end DIE of a type.

        Args:
            current_die (elftools.dwarf.die.DIE): The starting DIE.

        Returns:
            elftools.dwarf.die.DIE: The end DIE of the type.
        """
        valid_words = [
            "DW_TAG_base_type",
            "DW_TAG_pointer_type",
            "DW_TAG_structure_type",
        ]
        while not any(current_die.tag == word for word in valid_words):
            ref_addr = (
                current_die.attributes["DW_AT_type"].value + current_die.cu.cu_offset
            )
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
            type_die = self.get_end_die(type_die)
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
        #     else:
        #         byte_size_attr = type_die.attributes.get('DW_AT_byte_size')
        #         byte_size = byte_size_attr.value if byte_size_attr else None
        #
        #         return {
        #             'name': type_die.get_full_path(),
        #             'byte_size': byte_size
        #         }
        #
        # return None

    def map_all_variables_data(self) -> dict:
        variable_info_map = {}
        variable_list = self.get_var_list()
        for variable_name in variable_list:
            variable_info = self.get_var_info(variable_name)
            variable_info_map[variable_name] = variable_info
        return variable_info_map

if __name__ == "__main__":
    elf_file = (
        "C:\\Users\\m67250\\Downloads\\mc_apps_pic32mk-3.1.0\\mc_apps_pic32mk-3.1.0\\apps\\"
        "pmsm_foc_pll_estimator_pic32_mk\\firmware\\mclv2_pic32_mk_mcf_pim.X\\dist\\mclv2_pic32_mk_mcf_pim\\"
        "production\\mclv2_pic32_mk_mcf_pim.X.production.elf"
    )
    parser = Elf32Parser(elf_file)
    variable = "gMCRPOS_Parameters.rs"
    #variable_info = parser.get_var_info(variable)
    variable_map = parser.map_all_variables_data()
    variable_info = variable_map.get(variable)
    var_list = parser.get_var_list()
    print(var_list)
    #
    if variable_info:
        print(f"Variable Name: {variable_info.name}")
        print(f"Variable Type: {variable_info.type}")
        print(f"Variable Byte Size: {variable_info.byte_size}")
        print(f"Variable address: {variable_info.address}")
