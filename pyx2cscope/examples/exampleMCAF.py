"""exampleMCAF.py.

this example is a basic example to retrieve the value of a variable from motorBench auto-generated code.
"""

from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Configuration for serial port communication
serial_port = get_com_port()  # Get the COM port from the utility function
baud_rate = 115200  # Set baud rate for serial communication

# Specify the path to the ELF file
elf_file = get_elf_file_path()  # Get the path to the ELF file from the utility function

# Initialize the X2CScope with the specified serial port and baud rate
# The default baud rate is 115200
x2c_scope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)

# Retrieve specific variables from the MCU
speed_reference = x2c_scope.get_variable(
    "motor.apiData.velocityReference"
)  # Get the speed reference variable
speed_measured = x2c_scope.get_variable(
    "motor.apiData.velocityMeasured"
)  # Get the measured speed variable

# Attempt to read the value of the 'speedReference' variable and log the result
try:
    # Read the value of the speed reference variable
    speed_reference_value = speed_reference.get_value()
    print(f"Speed Reference Value: {speed_reference_value}")
except Exception as e:
    print(f"Error reading speed reference value: {e}")
