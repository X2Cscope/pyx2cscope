import logging

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from mchplnet.services.frame_save_parameter import (FrameSaveParameter,
                                                    ScopeSetup, ScopeTrigger)

from pyx2cscope.variable.variable_factory import VariableFactory

logging.basicConfig(
    level=0,
    filename="Save_parameter_test.py.log",
)

serial_port = "COM8"  # select COM port
baud_rate = 115200


serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)
elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\testing_x2cscope.X\dist\default\production\testing_x2cscope.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)
variable2 = variable_factory.get_variable("ScopeArray")

variable2.get_value()


variable2.set_value(8192)

print(variable2.get_value())
