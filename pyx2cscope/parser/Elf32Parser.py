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
        self.variable_mapping = {}
        # self.variables = self.get_variable_list()

    def _get_structure_members_recursive(
        self,
        die,
        parent_name: str,
        prev_address_offset=0,
    ):
        members = {}

        for child_die in die.iter_children():
            if child_die.tag == "DW_TAG_member" or child_die.tag == "DW_TAG_pointer_type":
                member = {}
                name_attr = child_die.attributes.get("DW_AT_name")
                if name_attr:
                    member_name = parent_name + "." + name_attr.value.decode("utf-8")
                type_attr = child_die.attributes.get("DW_AT_type")
                if type_attr:
                    type_offset = type_attr.value + child_die.cu.cu_offset
                    try:
                        member_type = self._get_member_type(type_offset)
                        offset_value_from_member_address = int(child_die.attributes.get("DW_AT_data_member_location").value[1])
                        nested_die = self.get_end_die(child_die)
                        print(nested_die)
                        if nested_die.tag == "DW_TAG_structure_type":
                            nested_members, nested_offset = self._get_structure_members_recursive(
                                nested_die, member_name, prev_address_offset + offset_value_from_member_address
                            )
                            if nested_members:
                                members.update(nested_members)
                            prev_address_offset = nested_offset
                        else:
                            member["type"] = member_type["name"]
                            member["byte_size"] = member_type["byte_size"]
                            member["address_offset"] = prev_address_offset + offset_value_from_member_address
                            members[member_name] = member
                    except Exception as e:
                        print(e)
                        # Handle missing fields
                        # This will be handled in future versions
                        continue

                    # If the member type is a structure or class, recurse into it
        return members , prev_address_offset

    def _get_structure_members(self, structure_die, var_name):
        prev_address_offset = 0
        return self._get_structure_members_recursive(
            structure_die, var_name, prev_address_offset
        )

    def get_var_list(self) -> List[str]:
        # my_list.insert(0, "")
        return sorted(self.variable_mapping.keys())

    def get_var_info(self) -> dict:
        """
        Parse the DWARF information for all variables.

        Returns:
            dict: A dictionary containing information for each variable.
        """

        for compilation_unit in self.dwarf_info.iter_CUs():
            root_die = compilation_unit.iter_DIEs()
            tag_variables = filter(lambda die: die.tag == "DW_TAG_variable" and die.attributes.get("DW_AT_location") is not None, root_die)

            for die_variable in tag_variables:
                if die_variable:
                    if die_variable.attributes.get("DW_AT_name") is not None:
                        var_name = die_variable.attributes.get(
                            "DW_AT_name"
                        ).value.decode("utf-8")
                    type_attr = die_variable.attributes.get("DW_AT_type")
                    if type_attr is None:
                        continue  # Skip to the next iteration if DW_AT_type is missing
                    ref_addr = type_attr.value + die_variable.cu.cu_offset

                    #
                    type_die = self.dwarf_info.get_DIE_from_refaddr(ref_addr)
                    print("typeDIE", type_die)
                    if type_die.tag != "DW_TAG_volatile_type":
                        end_die = self.get_end_die(type_die)
                        print(end_die)
                    try:
                        data = list(die_variable.attributes["DW_AT_location"].value)[1:]
                        address = int.from_bytes(bytes(data), byteorder="little")
                    except Exception as e:
                        print(e)
                        continue  # if there's an error, skip this variable and move to the next

                if end_die.tag == "DW_TAG_pointer_type":
                    type_name = "pointer"
                    self.variable_mapping[var_name] = VariableInfo(
                        name=var_name,
                        byte_size=end_die.attributes["DW_AT_byte_size"].value,
                        type=type_name,
                        address=address,
                    )
                elif end_die.tag == "DW_TAG_structure_type":
                    members = self._get_structure_members(end_die, var_name)[0]
                    print(members)
                    for member_name, member_data in members.items():
                        print(member_name, member_data)

                        self.variable_mapping[member_name] = VariableInfo(
                            name=member_name,
                            byte_size=member_data["byte_size"],
                            type=member_data["type"],
                            address=address + member_data["address_offset"],
                        )
                else:
                    self.variable_mapping[var_name] = VariableInfo(
                        name=var_name,
                        byte_size=end_die.attributes["DW_AT_byte_size"].value,
                        type=end_die.attributes["DW_AT_name"].value.decode("utf-8"),
                        address=address,
                    )

        return self.variable_mapping

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

        variable_info = self.get_var_info()
        # print(variable_info)
        variableList = self.get_var_list()
        print(variableList)
        return variable_info


if __name__ == "__main__":
    #elf_file = (
        # "C:\\Users\\m67250\\Downloads\\mc_apps_pic32mk-3.1.0\\mc_apps_pic32mk-3.1.0\\apps\\"
        # "pmsm_foc_pll_estimator_pic32_mk\\firmware\\mclv2_pic32_mk_mcf_pim.X\\dist\\mclv2_pic32_mk_mcf_pim\\"
        # "debug\\mclv2_pic32_mk_mcf_pim.X.debug.elf"
    # )
    #elf_file = r"C:\Users\m67250\Downloads\structure_Test.X.debug_PIC32MK_Level3_FixedAddress.elf"
    #elf_file = r"C:\Users\m67250\Downloads\mc_apps_sam_d5x_e5x-master\apps\pmsm_foc_pll_estimator_sam_e54\firmware\mclv2_sam_e54_pim.X\dist\mclv2_sam_e54_pim\production\mclv2_sam_e54_pim.X.production.elf"
    elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\elf32_struct.X\dist\default\production\elf32_struct.X.production.elf"
    parser = Elf32Parser(elf_file)
    # variable_info = parser.get_var_info(variable)
    variable_map = parser.map_all_variables_data()
    for variable in variable_map:
        print(variable_map.get(variable))
        print(hex(variable_map.get(variable).address))

    #
    # if variable_info:
    #     print(f"Variable Name: {variable_info.name}")
    #     print(f"Variable Type: {variable_info.type}")
    #     print(f"Variable Byte Size: {variable_info.byte_size}")
    #     print(f"Variable address: {variable_info.address}")
