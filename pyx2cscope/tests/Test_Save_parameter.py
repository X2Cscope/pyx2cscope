import logging
from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
import time
from pyx2cscope.variable.variable_factory import VariableFactory
from mchplnet.services.frame_save_parameter import ScopeSetup, ScopeTrigger
import struct
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.DEBUG,
    filename="Save_parameter_test.py.log",
)

# Function to read array chunks
def read_array_chunks(l_net, data_array_address, array_size, chunk_size=252, data_type=1):
    chunks = []

    # Calculate the number of chunks
    num_chunks = array_size // chunk_size

    for i in range(num_chunks):
        # Calculate the starting address for the current chunk
        current_address = data_array_address + i * chunk_size

        try:
            # Read the chunk of data
            chunk_data = l_net.get_ram_array(address=current_address, data_type=data_type, bytes_to_read=chunk_size)


            values = convert_data(chunk_data, variable1._get_width())
            # Append the chunk data to the list
            chunks.extend(values)
        except Exception as e:
            logging.error(f"Error reading chunk {i}: {str(e)}")

    #values = [int.from_bytes(chunks[i:i + 2], byteorder='little') for i in range(0, len(chunks), variable1._get_width())]
    return chunks


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
            channel_data[channel].extend(data[i:i + size])
            i += size

    return channel_data

def channel_config():

    return [(channel_name, 1) for channel_name, channel_info in enumerate(scope_config.list_channels().values())]


def convert_data(chunk_data, width):
    # Interpret as signed integer
    return struct.unpack("<{}h".format(len(chunk_data) // width), chunk_data)


# Initialize LNet and VariableFactory
serial_port = "COM9"
baud_rate = 115200
serial_connection = InterfaceFactory.get_interface(IType.SERIAL, port=serial_port, baudrate=baud_rate)
elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\motorbench_longhurst_mclv2_dsPIC33ck\motorbench_longhurst.X\dist\default\production\motorbench_longhurst.X.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)

# Set up scope configuration
scope_config = ScopeSetup()
variable1 = variable_factory.get_variable_elf("motor.idq.q")
variable2 = variable_factory.get_variable_elf("motor.estimator.qei.position.electrical")
scope_config.add_channel(variable1.as_channel(), trigger=True)
scope_config.add_channel(variable2.as_channel())


print(len(scope_config.list_channels()))
scope_config.set_trigger(channel=variable2.as_channel(), trigger_level=3000, trigger_mode=1, trigger_delay=0, trigger_edge=1)
l_net.scope_save_parameter(scope_config)

# Save and Load Parameters
for i in range(50000):
    try:
        # Load parameters
        load_parameter = l_net.load_parameters()
        print(load_parameter)

        # Check if scope finished
        if load_parameter.scope_state == 0:
            print("Scope finished")

            # Read array chunks
            data = read_array_chunks(l_net, load_parameter.data_array_address, array_size=load_parameter.data_array_size)
            print(data)
            extracted_data = extract_channels(data, channel_config())
            print(extracted_data)

            # Uncomment the following lines if you want to plot the data
            # numeric_data = [item for sublist in data for item in sublist]

            for channel, data in extracted_data.items():

                plt.plot(data, label= f"Channel {channel}" )
            #
            plt.plot(extracted_data[1])
            plt.xlabel('Data Index')
            plt.ylabel('Value')
            plt.title('Plot of Byte Data')
            plt.show()


            # Save the data to scope using your scope_save_parameter function
            response_save_parameter = l_net.scope_save_parameter(scope_config)
            print(response_save_parameter)

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")

    time.sleep(0.1)
