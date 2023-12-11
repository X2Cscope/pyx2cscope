"""
Example to change LED by changing the bit value on dspic33ck256mp508 Microchip Using SFR(Special function Register)
"""
import logging

logging.basicConfig(
    level=0,
    filename="BlinkyMCFG.log",
)

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet

from pyx2cscope.variable.variable_factory import VariableFactory

serial_port = "COM8"  # select COM port
baud_rate = 115200
serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)
elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\MUForum material\Firmware\AN1292_LongHurst_MCLV-48V-300W_script.X/dist/default/production/AN1292_LongHurst_MCLV-48V-300W_script.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)

speedReference = variable_factory.get_variable_elf("motor.apiData.velocityReference")
speedMeasured = variable_factory.get_variable_elf("motor.apiData.velocityMeasured")


try:
    logging.debug(speedReference.get_value())
except Exception as e:
    logging.debug(e)
