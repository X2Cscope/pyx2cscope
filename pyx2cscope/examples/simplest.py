"""This script demonstrates the simplest usage of the pyX2Cscope library to interact with variables in an ELF file via a serial connection.

The script initializes the X2CScope with a specified serial port and ELF file, retrieves specific variables,
reads their values, and writes new values to them.
"""
from pyx2cscope.xc2scope import X2CScope

# initialize the x2cscope with serial port, by default baud rate is 115200,
x2c_scope = X2CScope(port="COM8", baud_rate=115200, elf_file="Path_To_Elf_File")

# Retrieve specific variables.
speed_reference = x2c_scope.get_variable("motor.apiData.velocityReference")
speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())
# Write a new value to the "motor.apiData.velocityReference" variable on the target
speed_reference.set_value(1000)
