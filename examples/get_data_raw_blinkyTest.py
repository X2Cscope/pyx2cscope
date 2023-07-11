import logging

import pyx2cscope
from pylnet.pylnet.interfaces.factory import InterfaceFactory
from pylnet.pylnet.interfaces.factory import InterfaceType as IType

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

        # elf_file = 'C:\\Users\\m67250\\Downloads\\mc_apps_sam_d5x_e5x-master\\apps\\pmsm_foc_pll_estimator_sam_e54\\' \
        #            'firmware\\mclv2_sam_e54_pim.X\\dist\\mclv2_sam_e54_pim\\production\\' \
        #            'mclv2_sam_e54_pim.X.production.elf'
        elf_file = "C:\_DESKTOP\_Projects\AN1160_dsPIC33CK256MP508_MCLV2_MCHV\\bldc_MCLV2.X\dist\MCLV2\production/bldc_MCLV2.X.production.elf"

        # Initialize LNet and VariableFactory
        l_net = pyx2cscope.LNet(serial_connection)
        variable_factory = pyx2cscope.VariableFactory(l_net, elf_file)
        variable_elf = variable_factory.get_variable_elf("Flags.RotorAlignment")

        # new_variable = variable_factory.get_variable_elf('newme')
        # jessy = variable_factory.get_variable_elf('jessy')

        while True:
            print("variable_elf", variable_elf.get_value())
            print(variable_elf.set_value(10))
            # print('new_variable', new_variable.get_value())
            # print('jessy', jessy.get_value())

    except Exception as e:
        # Handle any other exceptions
        logging.error("Error occurred: {}".format(e))


if __name__ == "__main__":
    example()
