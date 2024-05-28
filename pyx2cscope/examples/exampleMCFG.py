import logging

from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

# Configure logging settings
logging.basicConfig(
    level=0,  # Log all levels of messages
    filename="BlinkyMCFG.log",  # Log file name
)

# Configuration for serial port communication
serial_port = get_com_port()  # Define the COM port to use
baud_rate = 115200  # Set baud rate for serial communication
# Specify the path to the ELF file
elf_file = get_elf_file_path()
# initialize the x2cscope with serial port, by default baud rate is 115200,
x2c_scope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)


# Retrieve specific variables.
speed_reference = x2c_scope.get_variable("motor.apiData.velocityReference")
speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")

# Attempt to read the value of the 'speedReference' variable and log the result
try:
    logging.debug(speed_reference.get_value())
except Exception as e:
    logging.debug(e)  # Log any exceptions that occur
