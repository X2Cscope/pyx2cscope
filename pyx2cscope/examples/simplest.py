"""The simplest usage of the pyX2Cscope library.

The script initializes the X2CScope class with a specified serial port and ELF file,
retrieves specific variables, reads their values, and writes new values to them.
"""

from pyx2cscope.x2cscope import X2CScope

# initialize the X2CScope class with serial port, by default baud rate is 115200
x2c_scope = X2CScope(port="COM8")
# instead of loading directly the elf file, we can import it after instantiating the X2CScope class
x2c_scope.import_variables(r"..\..\tests\data\qspin_foc_same54.elf")

# Collect some variables.
speed_reference = x2c_scope.get_variable("motor.apiData.velocityReference")
speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())
# Write a new value to the "motor.apiData.velocityReference" variable on the target
speed_reference.set_value(1000)
