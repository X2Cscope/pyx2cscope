from numbers import Number
from typing import List, Dict

from mchplnet.interfaces.abstract_interface import InterfaceABC
from mchplnet.interfaces.factory import InterfaceFactory, InterfaceType
from mchplnet.lnet import LNet
from mchplnet.services.frame_load_parameter import LoadScopeData
from mchplnet.services.scope import ScopeChannel, ScopeTrigger
from variable.variable import Variable
from variable.variable_factory import VariableFactory


def get_variable_as_scope_channel(variable: Variable) -> ScopeChannel:
    return ScopeChannel(
        name=variable.name,
        source_location=variable.address,
        data_type_size=variable.get_width(),
        source_type=0,
        is_integer=variable.is_integer(),
        is_signed=variable.is_signed(),
    )


class X2CScope:
    def __init__(self, elf_file: str, interface: InterfaceABC = None, *args, **kwargs):
        i_type = interface if interface is not None else InterfaceType.SERIAL
        self.interface = InterfaceFactory.get_interface(interface_type=i_type, **kwargs)
        self.lnet = LNet(self.interface)
        self.elf_file = elf_file
        self.variable_factory = VariableFactory(self.lnet, elf_file)
        self.scope_setup = self.lnet.get_scope_setup()

    def set_interface(self, interface: InterfaceABC):
        self.lnet = LNet(interface)
        self.scope_setup = self.lnet.get_scope_setup()
        self.variable_factory = VariableFactory(self.lnet, self.elf_file)

    def set_elf_file(self, elf_file: str):
        self.variable_factory = VariableFactory(self.lnet, elf_file)

    def connect(self):
        self.interface.start()

    def disconnect(self):
        self.interface.stop()

    def list_variables(self) -> List[str]:
        return self.variable_factory.get_var_list()

    def get_variable(self, name: str) -> Variable:
        return self.variable_factory.get_variable(name)

    def add_scope_channel(self, variable: Variable, trigger: bool = False) -> int:
        scope_channel = get_variable_as_scope_channel(variable)
        return self.scope_setup.add_channel(scope_channel, trigger)

    def remove_scope_channel(self, variable: Variable):
        return self.scope_setup.remove_channel(variable.name)

    def get_scope_channel_list(self) -> dict[str, ScopeChannel]:
        return self.scope_setup.list_channels()

    def set_scope_trigger(
        self,
        variable: Variable,
        trigger_level: int,
        trigger_mode: int,
        trigger_delay: int,
        trigger_edge: int,
    ):
        scope_trigger = ScopeTrigger(
            channel=get_variable_as_scope_channel(variable),
            trigger_level=trigger_level,
            trigger_delay=trigger_delay,
            trigger_edge=trigger_edge,
            trigger_mode=trigger_mode,
        )
        scope_setup = self.lnet.get_scope_setup()
        scope_setup.set_trigger(scope_trigger)

    def request_scope_data(self):
        self.lnet.save_parameter()

    def is_scope_data_ready(self) -> bool:
        load_parameter = self.lnet.load_parameters()
        return (
            load_parameter.scope_state == 0
            or load_parameter.data_array_pointer
            == load_parameter.data_array_used_length
        )

    def _calc_sda_used_length(self):
        # SDA(Scope Data Array) - SDA % DSS(data Set Size)
        scope_data: LoadScopeData = self.lnet.load_parameter
        nr_of_data_sets = scope_data.data_array_size % self.scope_setup.get_dataset_size()
        return scope_data.data_array_size - nr_of_data_sets

    def get_trigger_position(self):
        scope_data: LoadScopeData = self.lnet.load_parameter
        return scope_data.trigger_event_position / self.scope_setup.get_dataset_size()

    def get_delay_trigger_position(self):
        scope_data: LoadScopeData = self.lnet.load_parameter
        return (
            scope_data.trigger_event_position / self.scope_setup.get_dataset_size()
            - self.scope_setup.scope_trigger.trigger_delay,
        )

    def get_scope_channel_data(self) -> Dict[str, List[Number]]:
        return {"e": [1]}


# Refactor these functions to adapt on class x2cscope
# Function to read array chunks
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
            if i + size < len(data):
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