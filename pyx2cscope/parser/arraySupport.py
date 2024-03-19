from elftools.elf.elffile import ELFFile


def get_named_array_length(elf_file_path, array_name):
    with open(elf_file_path, "rb") as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print("No DWARF information in this ELF file.")
            return

        dwarf_info = elffile.get_dwarf_info()

        for CU in dwarf_info.iter_CUs():
            offset_to_die = {die.offset: die for die in CU.iter_DIEs()}
            for DIE in CU.iter_DIEs():
                # Check if the DIE is a variable and has the name we're looking for
                if DIE.tag == "DW_TAG_variable" and "DW_AT_name" in DIE.attributes:
                    if DIE.attributes["DW_AT_name"].value.decode("utf-8") == array_name:
                        # Get the type of the variable
                        type_attr = DIE.attributes["DW_AT_type"]
                        type_offset = type_attr.value + CU.cu_offset
                        type_DIE = offset_to_die.get(type_offset)

                        # Now, look for the array length in the type DIE
                        if type_DIE.tag == "DW_TAG_array_type":
                            for child in type_DIE.iter_children():
                                if child.tag == "DW_TAG_subrange_type":
                                    array_length_attr = child.attributes.get(
                                        "DW_AT_upper_bound"
                                    )
                                    if array_length_attr:
                                        array_length = (
                                            array_length_attr.value + 1
                                        )  # upper_bound is 0-indexed
                                        print(
                                            f"Array length of '{array_name}': {array_length}"
                                        )
                                        return array_length
                        break


# get_named_array_length(
#     r"C:\Users\m67250\Downloads\E54_github_packsupdated\mclv2_sam_e54_pim.X\dist\mclv2_sam_e54_pim\production\mclv2_sam_e54_pim.X.production.elf",
#     "ScopeArray",
# )
