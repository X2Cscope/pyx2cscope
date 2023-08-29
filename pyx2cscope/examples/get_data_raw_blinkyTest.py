import logging

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet

from pyx2cscope.variable.variable_factory import VariableFactory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    filename="BlinkyTest.log",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def example():
    try:
        # Initialize serial communication
        serial_port = "COM13"  # select COM port
        baud_rate = 115200
        serial_connection = InterfaceFactory.get_interface(
            IType.SERIAL, port=serial_port, baudrate=baud_rate
        )
        # select the appropriate elf file of your project.
        elf_file = (
            r"C:\_DESKTOP\_Projects\Motorbench_Projects\zsmt--42BLF02-MCLV-48V-300W.X\dist\default\production\zsmt--42BLF02-MCLV-48V-300W.X.production.elf"
        )

        # Initialize LNet and VariableFactory
        l_net = LNet(serial_connection)
        variable_factory = VariableFactory(l_net, elf_file)
        variable_elf = variable_factory.get_variable_elf("motor.ui.isrCount")
        logging.debug(variable_elf)

        while True:
            value_get = variable_elf.get_value()
            logging.debug("variable_elf", value_get)
            #value_put = variable_elf.set_value(500)
            #logging.debug(value_put)

    except Exception as e:
        # Handle any other exceptions
        logging.error("Error occurred: {}".format(e))


if __name__ == "__main__":
    example()
