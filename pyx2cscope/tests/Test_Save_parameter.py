import logging
import struct
import time

import matplotlib.pyplot as plt

from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from mchplnet.services.frame_save_parameter import ScopeSetup
from pyx2cscope.variable.variable_factory import VariableFactory

logging.basicConfig(
    level=logging.DEBUG,
    filename="Save_parameter_test.py.log",
)


def data_set_size():
    return sum(
        channel.data_type_size for channel in scope_config.list_channels().values()
    )


def SDA_used_length():
    # SDA(Scope Data Array) - SDA % DSS(data Set Size)
    return (
        load_parameter.data_array_size
        - load_parameter.data_array_size % data_set_size()
    )


# Function to read array chunks
def read_array_chunks(
    l_net, data_array_address, array_size, chunk_size=253, data_type=1
):
    chunks = []

    # Calculate the number of chunks
    num_chunks = array_size // chunk_size

    for i in range(num_chunks):
        # Calculate the starting address for the current chunk
        current_address = data_array_address + i * chunk_size

        try:
            # Read the chunk of data
            chunk_data = l_net.get_ram_array(
                address=current_address, data_type=data_type, bytes_to_read=chunk_size
            )

            # Append the chunk data to the list
            chunks.extend(chunk_data)
        except Exception as e:
            logging.error(f"Error reading chunk {i}: {str(e)}")

    extracted_channels = extract_channels(chunks, channel_config())

    extracted_channel_data = convert_data(
        extracted_channels, variable1._get_width()
    )  # TODO dynamic width
    # values = [int.from_bytes(chunks[i:i + 2], byteorder='little') for i in range(0, len(chunks), variable1._get_width())]
    return extracted_channel_data


def extract_channels(data, channel_configs):
    """
    Extracts channel data from a given array.

    :param data: The input data array.
    :param channel_configs: A list of tuples, where each tuple contains the channel number and its byte size.
    :return: A dictionary containing the extracted data for each channel.
    """
    channel_data = {channel: [] for channel, _ in channel_configs}
    i = 0

    while i < len(data):
        for channel, size in channel_configs:
            if i + size > len(data):
                break  # Avoid going out of index
            channel_data[channel].extend(data[i : i + size])
            i += size

    return channel_data


def channel_config():
    return [
        (channel_info.name, channel_info.data_type_size)
        for index, channel_info in enumerate(scope_config.list_channels().values())
    ]


def convert_data(extracted_channels, width):
    converted_data = {}
    for key, byte_list in extracted_channels.items():
        # Ensure the byte list length is even for pairs of bytes
        if len(byte_list) % 2 != 0:
            raise ValueError(f"Byte list length for {key} is not even.")

        # Convert the list of bytes to a bytes object
        bytes_data = bytes(byte_list)

        # Interpret each pair of bytes as a 16-bit signed integer
        format_string = f"<{len(bytes_data) // width}h"
        converted_data[key] = struct.unpack(format_string, bytes_data)

    return converted_data


# Initialize LNet and VariableFactory
serial_port = "COM4"
baud_rate = 115200
serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)
# elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\motorbench_longhurst_mclv2_dsPIC33ck\motorbench_longhurst.X\dist\default\production\motorbench_longhurst.X.production.elf"
elf_file = r"C:\Users\M71906\MPLABXProjects\MotorControl\dsPIC33-LVMC-MB-FOC-Sensorless.X\dist\default\production\dsPIC33-LVMC-MB-FOC-Sensorless.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)

# Set up scope configuration
variable1 = variable_factory.get_variable("motor.idq.q")
variable2 = variable_factory.get_variable("motor.estimator.qei.position.electrical")
variable3 = variable_factory.get_variable("motor.vabc.a")
variable4 = variable_factory.get_variable("motor.vabc.b")
variable5 = variable_factory.get_variable("motor.vabc.c")

scope_config = l_net.get_scope_setup()
scope_config.add_channel(variable1.as_channel(), trigger=True)
# scope_config.add_channel(variable2.as_channel())
# scope_config.add_channel(variable3.as_channel())
# scope_config.add_channel(variable4.as_channel())
# scope_config.add_channel(variable5.as_channel())

print(len(scope_config.list_channels()))
scope_config.set_trigger(
    channel=variable3.as_channel(),
    trigger_level=-500,
    trigger_mode=1,
    trigger_delay=50,
    trigger_edge=1,
)
# l_net.save_parameter()

# Save and Load Parameters
for i in range(50000):
    try:
        # Load parameters
        load_parameter = l_net.load_parameters()
        print(load_parameter)
        # Check if scope finished
        if (
            load_parameter.scope_state == 0
            or load_parameter.data_array_pointer
            == load_parameter.data_array_used_length
        ):
            print("Scope finished")
            print("look at:", load_parameter.trigger_event_position / data_set_size())
            print(
                "delayed trigger",
                load_parameter.trigger_event_position / data_set_size()
                - scope_config.scope_trigger.trigger_delay,
            )

            # Read array chunks
            data = read_array_chunks(
                l_net, load_parameter.data_array_address, array_size=SDA_used_length()
            )

            for channel, data in data.items():
                plt.plot(data, label=f"Channel {channel}")

            # plt.plot(extracted_data[1])
            plt.xlabel("Data Index")
            plt.ylabel("Value")
            plt.title("Plot of Byte Data")
            plt.legend()
            plt.show()

            # Save the data to scope using your scope_save_parameter function
            response_save_parameter = l_net.save_parameter()
            print(response_save_parameter)

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")

    time.sleep(0.1)
