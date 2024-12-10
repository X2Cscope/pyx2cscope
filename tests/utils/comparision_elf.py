"""Module for comparing ELF files parsed by 16-bit and 32-bit ELF parsers.

This script defines utility functions and classes to map and compare variables
from ELF files parsed by the two parsers. Differences and similarities between
the variable mappings are analyzed and displayed.
"""

from pyx2cscope.parser.generic_parser import GenericParser
from pyx2cscope.parser.elf16_parser import Elf16Parser

def compare_dicts_intelligently(dict1, dict2):
    """Compare two dictionaries of variables and analyze similarities and differences.

    Variables with pointer types are excluded from the comparison.
    Differences are categorized by address, type, and array size.

    :param dict1: First dictionary of variables
    :param dict2: Second dictionary of variables
    """
    dict1 = {key: value for key, value in dict1.items() if not value.type.startswith("pointer")}
    dict2 = {key: value for key, value in dict2.items() if not value.type.startswith("pointer")}

    common_keys = dict1.keys() & dict2.keys()
    unique_to_dict1 = dict1.keys() - dict2.keys()
    unique_to_dict2 = dict2.keys() - dict1.keys()

    same_values = []
    different_values = []

    def compare_variable_properties(var1, var2):
        """Compare the properties of two variables and identify differences.

        :param var1: Variable from dict1
        :param var2: Variable from dict2
        :return: A dictionary of differences
        """
        differences = {}
        if var1.address != var2.address:
            differences["address_diff"] = abs(var1.address - var2.address)
        if var1.type != var2.type:
            differences["type_diff"] = (var1.type, var2.type)
        if var1.array_size != var2.array_size:
            differences["array_size_diff"] = (var1.array_size, var2.array_size)
        return differences

    for key in common_keys:
        differences = compare_variable_properties(dict1[key], dict2[key])
        if differences:
            different_values.append({
                "key": key,
                "in_dict1": dict1[key],
                "in_dict2": dict2[key],
                "differences": differences,
            })
        else:
            same_values.append({"key": key, "in_dict1": dict1[key], "in_dict2": dict2[key]})

    print_summary(unique_to_dict1, dict1, unique_to_dict2, dict2, different_values, same_values, len(common_keys))


def print_summary(unique_to_dict1, dict1, unique_to_dict2, dict2, different_values, same_values, common_count):
    """Print a summary of the comparison results.

    :param unique_to_dict1: Keys unique to the first dictionary
    :param dict1: The first dictionary
    :param unique_to_dict2: Keys unique to the second dictionary
    :param dict2: The second dictionary
    :param different_values: List of keys with differing values
    :param same_values: List of keys with identical values
    :param common_count: Number of common keys
    """
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
        for k, v in diff["differences"].items():
            print(f"  {k.replace('_', ' ').capitalize()}: {v}")

    print(f"\nTotal variables in dict1: {len(dict1)}")
    print(f"Total variables in dict2: {len(dict2)}")
    print(f"Variables in both parsers: {common_count}")
    print(f"Different values: {len(different_values)}")
    print(f"Same values: {len(same_values)}")


def run_parsers_and_compare(elf_file_path):
    """Run both ELF parsers and compare the variable maps they produce.

    :param elf_file_path: Path to the ELF file to parse
    """
    elf32_parser = GenericParser(elf_file_path)
    elf16_parser = Elf16Parser(elf_file_path)

    variable_map_32 = elf32_parser._map_variables()
    variable_map_16 = elf16_parser._map_variables()

    compare_dicts_intelligently(variable_map_16, variable_map_32)


# Usage example
if __name__ == "__main__":
    elf_file = r"../data/MCAF_ZSMT_dsPIC33CK.elf"
    run_parsers_and_compare(elf_file)
