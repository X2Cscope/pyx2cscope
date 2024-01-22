import logging

# Configure logging settings
logging.basicConfig(
    level=0,  # Log all levels of messages
    filename="BlinkyMCFG.log",  # Log file name
)

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from pyx2cscope.variable.variable_factory import VariableFactory

# Configuration for serial port communication
serial_port = "COM8"  # Define the COM port to use
baud_rate = 115200  # Set baud rate for serial communication

# Create a serial interface instance for communication
serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)

# Specify the path to the ELF file
elf_file = (r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\MUForum "
            r"material\Firmware\AN1292_LongHurst_MCLV-48V-300W_script.X/dist/default/production/AN1292_LongHurst_MCLV"
            r"-48V-300W_script.X.production.elf")

# Initialize LNet instance with the created serial connection
l_net = LNet(serial_connection)

# Create a VariableFactory instance for managing variables from the ELF file
variable_factory = VariableFactory(l_net, elf_file)

# Retrieve specific variables.
speedReference = variable_factory.get_variable("motor.apiData.velocityReference")
speedMeasured = variable_factory.get_variable("motor.apiData.velocityMeasured")

# Attempt to read the value of the 'speedReference' variable and log the result
try:
    logging.debug(speedReference.get_value())
except Exception as e:
    logging.debug(e)  # Log any exceptions that occur
