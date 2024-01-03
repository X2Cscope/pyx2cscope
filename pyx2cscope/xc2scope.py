import logging
import struct
from numbers import Number
from typing import List, Dict

from mchplnet.interfaces.abstract_interface import InterfaceABC
from mchplnet.interfaces.factory import InterfaceFactory, InterfaceType
from mchplnet.lnet import LNet
from mchplnet.services.frame_load_parameter import LoadScopeData
from mchplnet.services.scope import ScopeChannel, ScopeTrigger
from variable.variable import Variable
from variable.variable_factory import VariableFactory

logging.basicConfig(
    level=logging.DEBUG,
    filename=__name__ + ".log",
)


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
        self.convert_list = {}

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
        self.convert_list[variable.name] = variable.bytes_to_value
        return self.scope_setup.add_channel(scope_channel, trigger)

    def remove_scope_channel(self, variable: Variable):
        if variable.name in self.convert_list:
            self.convert_list.pop(variable.name)
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
        self.scope_setup.set_trigger(scope_trigger)

    def request_scope_data(self):
        self.lnet.save_parameter()

    def is_scope_data_ready(self) -> bool:
        scope_data = self.lnet.load_parameters()
        logging.debug(scope_data)
        return (
            scope_data.scope_state == 0
            or scope_data.data_array_pointer == scope_data.data_array_used_length
        )

    def get_trigger_position(self) -> int:
        scope_data: LoadScopeData = self.lnet.scope_data
        return int(scope_data.trigger_event_position / self.scope_setup.get_dataset_size())

    def get_delay_trigger_position(self) -> int:
        trigger_position = self.get_trigger_position()
        return int(trigger_position - self.scope_setup.scope_trigger.trigger_delay)

    def _calc_sda_used_length(self):
        # SDA(Scope Data Array) - SDA % DSS(data Set Size)
        bytes_not_used = (
            self.lnet.scope_data.data_array_size % self.scope_setup.get_dataset_size()
        )
        return self.lnet.scope_data.data_array_size - bytes_not_used

    def _read_array_chunks(self):
        chunk_data = []
        data_type = 1
        chunk_size = 253
        # Calculate the number of chunks
        sda_size = self._calc_sda_used_length()
        print(sda_size)
        print(self.scope_setup.get_dataset_size())
        num_chunks = sda_size // chunk_size
        for i in range(num_chunks):
            # Calculate the starting address for the current chunk
            current_address = self.lnet.scope_data.data_array_address + i * chunk_size
            try:
                # Read the chunk of data
                data = self.lnet.get_ram_array(current_address, chunk_size, data_type)
                chunk_data.extend(data)
            except Exception as e:
                logging.error(f"Error reading chunk {i}: {str(e)}")
        return chunk_data

    def _sort_channel_data(self, data) -> Dict[str, List[Number]]:
        channels = {channel: [] for channel in self.scope_setup.list_channels()}
        dataset_size = self.scope_setup.get_dataset_size()
        for i in range(0, len(data), dataset_size):
            dataset = data[i: i + dataset_size]
            j = 0
            for name, channel in self.scope_setup.list_channels().items():
                k = channel.data_type_size + j
                value = self.convert_list[name](dataset[j:k])
                channels[name].append(value)
                j = k
        return channels

    def _filter_channels(self, channels):
        start = self.get_delay_trigger_position()
        total_sdas = int(self.lnet.scope_data.data_array_size % self.scope_setup.get_dataset_size())
        end = total_sdas - start
        for channel in channels:
            channels[channel] = channels[channel][start: end]
        return channels

    def get_scope_channel_data(self, filter=True) -> Dict[str, List[Number]]:
        data = self._read_array_chunks()
        channels = self._sort_channel_data(data)
        return self._filter_channels(channels) if filter else channels
