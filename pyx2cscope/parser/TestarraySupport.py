from Elf_Parser import VariableInfo  # Assuming this defines VariableInfo class
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
                        type_attr = DIE.attributes.get("DW_AT_type")
                        if not type_attr:
                            print(f"Variable '{array_name}' has no type information.")
                            continue

                        type_offset = type_attr.value + CU.cu_offset
                        type_DIE = offset_to_die.get(type_offset)

                        # Check for different array representations
                        if type_DIE:
                            if type_DIE.tag == "DW_TAG_array_type":
                                # Look for upper bound in subrange type child
                                for child in type_DIE.iter_children():
                                    if child.tag == "DW_TAG_subrange_type":
                                        array_length_attr = child.attributes.get("DW_AT_upper_bound")
                                        if array_length_attr:
                                            array_length = array_length_attr.value + 1
                                            print(f"Array length of '{array_name}': {array_length}")
                                            return VariableInfo(
                                                name=DIE.attributes.get("DW_AT_name").value,
                                                byte_size=DIE.size,
                                                type="int32",  # Adjust type based on actual type
                                                address=DIE.attributes.get("DW_AT_location").value,
                                                is_array=True,
                                                array_size=array_length,
                                            )
                            # Handle other array representations (pointers, etc.) here
                            # You might need to analyze the type DIE further
                            else:
                                print(f"Variable '{array_name}' is an array but with unknown representation.")

                        else:
                            print(f"Failed to find type information for '{array_name}'.")

                        break  # Stop searching after finding the named variable


values = get_named_array_length(
    r"C:\Users\m67250\Downloads\dsPIC33A_compiled_example\xc-dsc_dsPIC33AK128MC106_examples.X\dist\default\production\xc-dsc_dsPIC33AK128MC106_examples.X.production.elf",
    "my_bool",
)
print(values)
