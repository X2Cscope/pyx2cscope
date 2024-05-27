import logging

from pyx2cscope.xc2scope import X2CScope
from utils import get_elf_file_path, get_com_port

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
x2cScope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)


# Retrieve specific variables.
speedReference = x2cScope.get_variable("motor.apiData.velocityReference")
speedMeasured = x2cScope.get_variable("motor.apiData.velocityMeasured")

# Attempt to read the value of the 'speedReference' variable and log the result
try:
    logging.debug(speedReference.get_value())
except Exception as e:
    logging.debug(e)  # Log any exceptions that occur
