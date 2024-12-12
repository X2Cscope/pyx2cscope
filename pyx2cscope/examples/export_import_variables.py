"""Example of importing and exporting variable.

The script initializes the X2CScope class with a specified serial port,
retrieves specific variables, reads their values, export them to a yaml file
and also export all the variables available as a pickle binary file.

We define a new instance of X2Cscope, and we reload the variables over the exported
files instead of the elf file.
"""
import os

from pyx2cscope.x2cscope import X2CScope
from pyx2cscope.variable.variable_factory import FileType

# initialize the X2CScope class with serial port, by default baud rate is 115200
com_port = "COM32"
x2c_scope = X2CScope(port=com_port)
# instead of loading directly the elf file, we can import it after instantiating the X2CScope class
x2c_scope.import_variables(r"..\..\tests\data\qspin_foc_same54.elf")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_reference = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_measured = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())

# you can export only these two variables as yaml file (plain text)
x2c_scope.export_variables(filename="my_two_variables", items=[angle_reference, speed_measured])
# you can export all the variables available. For a different file format, define 'ext' variable, i.e. pickle (binary)
x2c_scope.export_variables(filename="my_variables", ext=FileType.PICKLE)

# disconnect x2cscope so we can reconnect with another instance
x2c_scope.disconnect()

# Instantiate a different X2Cscope to ensure we have an empty variable list, i.e. x2c
x2c = X2CScope(port=com_port)
# instead of loading the elf file, we load our exported file with all variable
x2c.import_variables("my_variables.pkl")
# or we can load only our two variables
# x2c.import_variables("my_two_variables.yml")
# or we can load our elf file again
# x2c.import_variables(filename=r"..\..\tests\data\qspin_foc_same54.elf")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_ref2 = x2c.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_ref2 = x2c.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# Read the value of the "speed_ref2" variable from the target
print(speed_ref2.get_value())

# housekeeping
os.remove("my_variables.pkl")
os.remove("my_two_variables.yml")

