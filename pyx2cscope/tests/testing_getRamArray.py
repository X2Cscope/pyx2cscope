"""
Example to change LED by changing the bit value on dspic33ck256mp508 Microchip Using SFR(Special function Register)
"""
import logging

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from pyx2cscope.variable.variable_factory import VariableFactory

logging.basicConfig(
    level=0,
    filename="BlinkySFR.log",
)

serial_port = "COM15"  # select COM port
baud_rate = 115200
serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)
elf_file = r"C:\_DESKTOP\MC FG F2F Vienna\pyx2cscope_dspic33ck_48-300W.X\dist\default\production\pyx2cscope_dspic33ck_48-300W.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)
