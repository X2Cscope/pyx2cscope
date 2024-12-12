"""The simplest usage of the pyX2Cscope library without using and elf_file.

The script initializes the X2CScope class with a specified serial port without ELF file.
At this way, we can't know which variables are available on the processor, but we can
get connection info, processor id, and x2cscope version.

It is possible to set later the path to and elf file through method set_elf_file
"""

from pyx2cscope.x2cscope import X2CScope

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

# set the elf_file later, post instantiation
x2c_scope.import_variables("""your_path_to_elf_file.elf""")

# Collect some variables, i.e.: from QSPIN on SAME54 MCLV-48V-300W
angle_reference = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecAngle")
speed_measured = x2c_scope.get_variable("mcFocI_ModuleData_gds.dOutput.elecSpeed")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())


