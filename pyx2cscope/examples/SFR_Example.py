"""Example to read LATD and TMR1 registers using Special Function Register (SFR) access."""

import logging
import time

from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Configuration for serial port communication
port = get_com_port()  # Select COM port
elf_file = get_elf_file_path()

# Initialize the X2CScope with the specified serial port and baud rate
x2cscope = X2CScope(port=port, elf_file=elf_file)

# Get the LATD register using the sfr parameter
latd_register = x2cscope.get_variable("LATD", sfr=True)

# Get the TMR1 register using the sfr parameter
tmr1_register = x2cscope.get_variable("TMR1", sfr=True)

print("Reading LATD and TMR1 registers...")
print("Press Ctrl+C to stop\n")


# Read the current value of LATD register
latd_value = latd_register.get_value()

# Read the current value of TMR1 register
tmr1_value = tmr1_register.get_value()

# Print the register values
print(f"LATD: 0x{latd_value:04X} ({latd_value})")
print(f"TMR1: 0x{tmr1_value:04X} ({tmr1_value})")
print("-" * 40)



