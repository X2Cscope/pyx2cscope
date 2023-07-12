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
        serial_port = "COM8"
        baud_rate = 115200
        serial_connection = InterfaceFactory.get_interface(
            IType.SERIAL, port=serial_port, baudrate=baud_rate
        )
        elf_file = (
            "C:\\_DESKTOP\\_Projects\\AN1160_dsPIC33CK256MP508_MCLV2_MCHV\\bldc_MCLV2.X\\dist\\MCLV2\\"
            "production/bldc_MCLV2.X.production.elf"
        )

        # Initialize LNet and VariableFactory
        l_net = LNet(serial_connection)
        variable_factory = VariableFactory(l_net, elf_file)
        variable_elf = variable_factory.get_variable_elf("PotVal")

        while True:
            value_get = variable_elf.get_value()
            print("variable_elf", value_get)
            value_put = variable_elf.set_value(500)
            print(value_put)

    except Exception as e:
        # Handle any other exceptions
        logging.error("Error occurred: {}".format(e))


if __name__ == "__main__":
    example()
