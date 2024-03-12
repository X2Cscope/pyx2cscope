import logging

# Configure logging settings
logging.basicConfig(
    level=0,  # Log all levels of messages
    filename="BlinkyMCFG.log",  # Log file name
)

from pyx2cscope.xc2scope import X2CScope

# Configuration for serial port communication
serial_port = "COM8"  # Define the COM port to use
baud_rate = 115200  # Set baud rate for serial communication
# Specify the path to the ELF file
elf_file = (
    r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\MUForum "
    r"material\Firmware\AN1292_LongHurst_MCLV-48V-300W_script.X/dist/default/production/AN1292_LongHurst_MCLV"
    r"-48V-300W_script.X.production.elf"
)
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
