"""Unified parser solution for ELF files."""

from __future__ import print_function

import os

from elftools.elf.elffile import ELFFile


def process_file(filename):
    """Process the ELF file and print symbols' information."""
    print("Processing file:", filename)

    if not os.path.isfile(filename):
        print(f"File {filename} does not exist.")
        return

    with open(filename, "rb") as f:
        elffile = ELFFile(f)

        # Retrieve symbol table
        symbols = elffile.get_section_by_name(".symtab")
        if symbols is None:
            print("No symbol table found in the ELF file.")
            return

        print("\nSymbols and their information:")
        for sym in symbols.iter_symbols():

            if sym.entry.st_info.type in {"STT_OBJECT", "STT_FUNC"}:
                print(f"\nSymbol: {sym.name}")
                print(f"  Address: {hex(sym.entry.st_value)}")
                print(f"  Size: {sym.entry.st_size} bytes")
                print(f"  Binding: {sym.entry.st_info.bind}")
                print(f"  Type: {sym.entry.st_info.type} (Object)")


if __name__ == "__main__":

    elf_file = r"C:\Users\m67250\Microchip Technology Inc\Mark Wendler - M18034 - Masters_2024_MC3\elfparser project\elfparser_Unified.X\dist\default\production\elfparser_Unified.X.production.elf"  # 16bit-ELF
    # elf_file = r"C:\Users\m67250\Downloads\pmsm_foc_zsmt_hybrid_sam_e54\pmsm_foc_zsmt_hybrid_sam_e54\firmware\qspin_zsmt_hybrid.X\dist\default\production\qspin_zsmt_hybrid.X.production.elf"

    process_file(elf_file)
