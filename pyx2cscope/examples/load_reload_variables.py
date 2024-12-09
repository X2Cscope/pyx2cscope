"""The simplest usage of the pyX2Cscope library.

The script initializes the X2CScope class with a specified serial port and ELF file,
retrieves specific variables, reads their values, and writes new values to them.
"""

from pyx2cscope.x2cscope import X2CScope

# initialize the X2CScope class with serial port, by default baud rate is 115200
com_port = "COM32"
x2c_scope = X2CScope(port=com_port, elf_file="C:/Users/M71906/MPLABXProjects/MotorControl/SAME54-48V300W-Qspin-FOC/foc_same54.X/dist/default/production/foc_same54.X.production.elf")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_reference = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_measured = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())

x2c_scope.export_variables(filename="my_variables")
x2c_scope.disconnect()

# Instantiate a different X2Cscope to ensure we have an empty variable list, i.e. x2c
x2c = X2CScope(port=com_port)
x2c.import_variables(filename="my_variables")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_ref2 = x2c.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_ref2 = x2c.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# Read the value of the "speed_ref2" variable from the target
print(speed_ref2.get_value())

