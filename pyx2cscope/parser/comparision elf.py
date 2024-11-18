from pyx2cscope.parser.unified_parser import Parser
from pyx2cscope.parser.elf16_parser import Elf16Parser


class VariableInfo:
    def __init__(self, name, type, byte_size, address, array_size):
        self.name = name
        self.type = type
        self.byte_size = byte_size
        self.address = address
        self.array_size = array_size

    def __repr__(self):
        return f"VariableInfo(name={self.name}, type={self.type}, byte_size={self.byte_size}, address={self.address}, array_size={self.array_size})"


def compare_dicts_intelligently(dict1, dict2):
    common_keys = set(dict1.keys()).intersection(set(dict2.keys()))
    unique_to_dict1 = set(dict1.keys()) - set(dict2.keys())
    unique_to_dict2 = set(dict2.keys()) - set(dict1.keys())

    same_values = []
    different_values = []

    for key in common_keys:
        var1 = dict1[key]
        var2 = dict2[key]

        address_match = var1.address == var2.address
        type_match = var1.type == var2.type
        array_size_match = var1.array_size == var2.array_size

        if address_match and type_match and array_size_match:
            same_values.append(
                {"key": key, "in_dict1": var1, "in_dict2": var2}
            )
        else:
            differences = {}
            if not address_match:
                differences["address_diff"] = abs(var1.address - var2.address)
            if not type_match:
                differences["type_diff"] = (var1.type, var2.type)
            if not array_size_match:
                differences["array_size_diff"] = (var1.array_size, var2.array_size)

            different_values.append(
                {
                    "key": key,
                    "in_dict1": var1,
                    "in_dict2": var2,
                    "differences": differences,
                }
            )

    print("Keys only in dict1:")
    for key in unique_to_dict1:
        print(f"{key}: {dict1[key]}")

    print("\nKeys only in dict2:")
    for key in unique_to_dict2:
        print(f"{key}: {dict2[key]}")

    print("\nCommon keys with different values:")
    for diff in different_values:
        print(f"{diff['key']}:")
        print(f"  in dict1: {diff['in_dict1']}")
        print(f"  in dict2: {diff['in_dict2']}")
        if "address_diff" in diff["differences"]:
            print(f"  Address difference: {diff['differences']['address_diff']}")
        if "type_diff" in diff["differences"]:
            print(f"  Type difference: {diff['differences']['type_diff']}")
        if "byte_size_diff" in diff["differences"]:
            print(f"  Byte size difference: {diff['differences']['byte_size_diff']}")
        if "array_size_diff" in diff["differences"]:
            print(f"  Array size difference: {diff['differences']['array_size_diff']}")

    # print("\nCommon keys with same values:")
    # for same in same_values:
    #      print(f"{same['key']}")

    print(f"\nTotal variables in dict1: {len(dict1)}")
    print(f"Total variables in dict2: {len(dict2)}")
    print(f"Variables in both parsers: {len(common_keys)}")
    print(f"Different values: {len(different_values)}")
    print(f"Same values: {len(same_values)}")


def run_parsers_and_compare(elf_file_path):
    # Parse the ELF file with both 32-bit and 16-bit parsers
    elf32_parser = Parser(elf_file_path)
    elf16_parser = Elf16Parser(elf_file_path)

    # Generate variable maps for each parser
    variable_map_32 = elf32_parser._map_variables()
    variable_map_16 = elf16_parser._map_variables()

    # print("variable_map_16", variable_map_16)
    # print("variable_map_32", variable_map_32)
    # Compare the two dictionaries
    compare_dicts_intelligently(variable_map_16, variable_map_32)


# Usage example
elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\elfparser_Decoding\Unified.X\dist\default\production\Unified.X.production.elf"
#elf_file = r"C:\Users\m67250\Downloads\mcapp_pmsm_zsmtlf(1)\mcapp_pmsm_zsmtlf\project\mcapp_pmsm.X\dist\default\production\mcapp_pmsm.X.production.elf"
elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\Training_Domel\motorbench_demo_domel.X\dist\default\production\motorbench_demo_domel.X.production.elf"
run_parsers_and_compare(elf_file)
