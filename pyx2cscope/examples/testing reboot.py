from xc2scope import X2CScope

# x2c_scope = X2CScope(port="COM12", elf_file= r"C:\Users\m67250\OneDrive - Microchip Technology
# Inc\Desktop\elfparser_Decoding\dsPIC33A_RAM 1\dsPIC33A_instrRAM\dsPIC33A_RAM.X\dist\default\production\dsPIC33A_RAM
# .X.production.elf")

x2c_scope = X2CScope(port="COM12",
                     elf_file=r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\WWMCFG Call "
                              r"Training\Demo_ACT42blf02_X2Cscope_motorbench_FOC.X\dist\default\production"
                              r"\Demo_ACT42blf02_X2Cscope_motorbench_FOC.X.production.elf")

byte_array = x2c_scope.reboot_device()
# Convert each byte to its decimal value
decimal_values = [byte for byte in byte_array]
print(decimal_values)
hexvalue = hex(decimal_values[5])
print(hexvalue)
