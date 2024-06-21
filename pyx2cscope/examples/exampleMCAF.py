"""exampleMCAF.py.

this example is the very basic example to retrieve the value of a certain variable for motorBench generated code.
"""

import logging

from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

# Configure logging settings to capture all levels of log messages and write them to a file
logging.basicConfig(
    level=0,  # Log all levels of messages
    filename="BlinkyMCFG.log",  # Log file name
)

# Configuration for serial port communication
serial_port = get_com_port()  # Get the COM port to use from the utility function
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
    speed_reference_value = (
        speed_reference.get_value()
    )  # Read the value of the speed reference variable
    logging.debug(
        f"Speed Reference Value: {speed_reference_value}"
    )  # Log the retrieved value
except Exception as e:
    logging.debug(
        f"Error reading speed reference value: {e}"
    )  # Log any exceptions that occur
