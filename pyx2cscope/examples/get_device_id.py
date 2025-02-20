"""The simplest usage of the pyX2Cscope library without using and elf_file on the constructor.

The script initializes the X2CScope class with a specified serial port without ELF file.
At this way, we don't know which variables are available on the processor, but we can
get connection info, processor id, and x2cscope version.

It is possible to import later and elf file or a variable import file as .yml/.pkl
In this way you can read variables available at flashed programm. Or use the method
x2c_scope.get_variable_raw(VariableInfo var_info) to retrieve variables directly from the
device's memory.
"""

from pyx2cscope.x2cscope import X2CScope
from variable.variable import VariableInfo

# initialize the X2CScope class with serial port, by default baud rate is 115200
x2c_scope = X2CScope(port="COM32")

# Read device_info
device_info = x2c_scope.get_device_info()

# Print the controller info
# i.e.: {
#   'processor_id': '__GENERIC_MICROCHIP_PIC32__',
#   'uc_width': '32-bit',
#   'date': 'Mar 32019',
#   'time': '1220',
#   'AppVer': 1,
#   'dsp_state': 'Application runs on target'
#   }
print(device_info)

# set the elf_file later, post instantiation to get some variables
x2c_scope.import_variables("""your_path_to_elf_file.elf""")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_reference = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_measured = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# or load a variable directly from the memory
speed_measured_info = VariableInfo("speed_measured", "float", 2, 536879832, 0, {})
speed_measured_raw = x2c_scope.get_variable_raw(speed_measured_info)

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())


