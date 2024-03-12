import logging
from numbers import Number
from typing import Dict, List

from mchplnet.interfaces.abstract_interface import InterfaceABC
from mchplnet.interfaces.factory import InterfaceFactory, InterfaceType
from mchplnet.lnet import LNet
from mchplnet.services.frame_load_parameter import LoadScopeData
from mchplnet.services.scope import ScopeChannel, ScopeTrigger

from pyx2cscope.variable.variable import Variable
from pyx2cscope.variable.variable_factory import VariableFactory

# Configure logging for debugging and tracking
logging.basicConfig(
    level=logging.DEBUG,
    filename=__name__ + ".log",
)


def get_variable_as_scope_channel(variable: Variable) -> ScopeChannel:
    """
    Converts a Variable object to a ScopeChannel object.

    Args:
        variable (Variable): The variable to be converted to a ScopeChannel.

    Returns:
        ScopeChannel: A ScopeChannel object representing the given variable.
    """
    return ScopeChannel(
        name=variable.name,
        source_location=variable.address,
        data_type_size=variable.get_width(),
        source_type=0,
        is_integer=variable.is_integer(),
        is_signed=variable.is_signed(),
    )


class X2CScope:
    """
    X2CScope class for interfacing with the X2C Scope tool.

    This class provides methods for connecting to the scope, setting up scope channels,
    requesting data, and processing received data.

    Attributes:
        elf_file (str): Path to the ELF file.
        interface (InterfaceABC): Interface object for communication.
        lnet (LNet): LNet object for low-level network operations.
        variable_factory (VariableFactory): Factory to create Variable objects.
        scope_setup: Configuration for the scope setup.
        convert_list (dict): Dictionary to store variable conversion functions.
    """

    def __init__(self, elf_file: str, interface: InterfaceABC = None, *args, **kwargs):
        """
        Initialize the X2CScope instance.

        Args:
            elf_file (str): Path to the ELF file.
        """
        i_type = interface if interface is not None else InterfaceType.SERIAL
        self.interface = InterfaceFactory.get_interface(interface_type=i_type, **kwargs)
        self.lnet = LNet(self.interface)
        self.elf_file = elf_file
        self.variable_factory = VariableFactory(self.lnet, elf_file)
        self.scope_setup = self.lnet.get_scope_setup()
        self.convert_list = {}

    def set_interface(self, interface: InterfaceABC):
        """
        Set the communication interface for the scope.

        Args:
            interface (InterfaceABC): The interface to be set for communication.
        """
        self.lnet = LNet(interface)
        self.scope_setup = self.lnet.get_scope_setup()
        self.variable_factory = VariableFactory(self.lnet, self.elf_file)

    def set_elf_file(self, elf_file: str):
        """
        Set the ELF file for the scope.

        Args:
            elf_file (str): Path to the ELF file.
        """
        self.variable_factory = VariableFactory(self.lnet, elf_file)

    def connect(self):
        """Establish a connection with the scope interface."""
        self.interface.start()

    def disconnect(self):
        """Terminate the connection with the scope interface."""
        self.interface.stop()

    def list_variables(self) -> List[str]:
        """
        List all available variables.

        Returns:
            List[str]: A list of available variable names.
        """
        return self.variable_factory.get_var_list()

    def get_variable(self, name: str) -> Variable:
        """
        Retrieve a variable by its name.

        Args:
            name (str): The name of the variable to retrieve.

        Returns:
            Variable: The requested variable object.
        """
        return self.variable_factory.get_variable(name)

    def add_scope_channel(self, variable: Variable, trigger: bool = False) -> int:
        """
        Add a variable as a scope channel.

        Args:
            variable (Variable): The variable to be added as a scope channel.
            trigger (bool, optional): If set to True, the channel will be used as a trigger. Defaults to False.

        Returns:
            int: The ID of the added scope channel.
        """
        scope_channel = get_variable_as_scope_channel(variable)
        self.convert_list[variable.name] = variable.bytes_to_value
        return self.scope_setup.add_channel(scope_channel, trigger)

    def remove_scope_channel(self, variable: Variable):
        """
        Remove a variable from the scope channel.

        Args:
            variable (Variable): The variable to be removed from the scope channel.

        Returns:
            The result of the channel removal operation.
        """
        if variable.name in self.convert_list:
            self.convert_list.pop(variable.name)
        return self.scope_setup.remove_channel(variable.name)

    def get_scope_channel_list(self) -> Dict[str, ScopeChannel]:
        """
        Get a list of all scope channels.

        Returns:
            Dict[str, ScopeChannel]: A dictionary of scope channels with their names as keys.
        """
        return self.scope_setup.list_channels()

    def set_scope_trigger(
        self,
        variable: Variable,
        trigger_level: int,
        trigger_mode: int,
        trigger_delay: int,
        trigger_edge: int,
    ):
        """
        Set the scope trigger configuration.

        Args:
            variable (Variable): The variable to use as the trigger source.
            trigger_level (int): The trigger level value.
            trigger_mode (int): The trigger mode.
            trigger_delay (int): The trigger delay.
            trigger_edge (int): The trigger edge setting.
        """
        scope_trigger = ScopeTrigger(
            channel=get_variable_as_scope_channel(variable),
            trigger_level=trigger_level,
            trigger_delay=trigger_delay,
            trigger_edge=trigger_edge,
            trigger_mode=trigger_mode,
        )
        self.scope_setup.set_trigger(scope_trigger)

    def clear_trigger(self):
        """
        Reset Trigger configuration.
        """
        self.scope_setup.reset_trigger()

    def set_sample_time(self, sample_time: int):
        """
        This paramater defines a pre-scaler when the scope is in the sampling mode. This can be used to extend total sampling time at cost of resolution.
        0 = every sample, 1 = every 2nd sample, 2 = every 3rd sample .....

        Args:
            sample_time (int): The sample time factor.
        """
        self.scope_setup.set_sample_time_factor(sample_time)

    def set_scope_state(self, scope_state: int):
        """
        Set the state of the scope.

        Args:
            scope_state (int): The desired scope state.
        """
        self.scope_setup.set_scope_state(scope_state)

    def request_scope_data(self):
        """
        Request scope data from the LNet layer.

        This function should be called once all the required settings are made for data acquisition.
        """
        self.lnet.save_parameter()

    def is_scope_data_ready(self) -> bool:
        """
        Check if the scope data is ready.

        Returns:
            bool: True if the scope data is ready, False otherwise.
        """
        scope_data = self.lnet.load_parameters()
        logging.debug(scope_data)
        return (
            scope_data.scope_state == 0
            or scope_data.data_array_pointer == scope_data.data_array_used_length
        )

    def get_trigger_position(self) -> int:
        """
        Get the position of the trigger event.

        Returns:
            int: The index position of the trigger event.
        """
        scope_data: LoadScopeData = self.lnet.scope_data
        return int(
            scope_data.trigger_event_position / self.scope_setup.get_dataset_size()
        )

    def get_delay_trigger_position(self) -> int:
        """
        Get the position of the delay trigger.

        Returns:
            int: The index position of the delay trigger.
        """
        trigger_position = self.get_trigger_position()
        return int(trigger_position - self.scope_setup.scope_trigger.trigger_delay)

    def _calc_sda_used_length(self):
        """
        Calculate the used length of the Scope Data Array (SDA).

        Returns:
            The length of the used portion of the SDA.
        """
        # SDA(Scope Data Array) - SDA % DSS(Data Set Size)
        bytes_not_used = (
            self.lnet.scope_data.data_array_size % self.scope_setup.get_dataset_size()
        )
        return self.lnet.scope_data.data_array_size - bytes_not_used

    def _read_array_chunks(self):
        """
        Read array chunks from the LNet layer.

        Returns:
            A list containing the chunk data.
        """
        chunk_data = []
        data_type = 1  # it will always be 1 for array data
        chunk_size = (
            253  # full chunk excluding crc and Service-ID in total bytes 255 0xFF
        )
        # Calculate the number of chunks
        num_chunks = self._calc_sda_used_length() // chunk_size
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
        """
        Sort and convert the dataset byte order into channel byte order.

        Args:
            data: The raw data read from the scope.

        Returns:
            Dict[str, List[Number]]: A dictionary with channel names as keys and lists of sorted data as values.
        """
        channels = {channel: [] for channel in self.scope_setup.list_channels()}
        dataset_size = self.scope_setup.get_dataset_size()
        for i in range(0, len(data), dataset_size):
            dataset = data[i : i + dataset_size]
            j = 0
            for name, channel in self.scope_setup.list_channels().items():
                k = channel.data_type_size + j
                value = self.convert_list[name](dataset[j:k])
                channels[name].append(value)
                j = k
        return channels

    def _filter_channels(self, channels):
        """
        Filter the channels to include only valid data.

        Args:
            channels: The dictionary of channels with raw data.

        Returns:
            The filtered dictionary of channels with valid data only.
        """
        start = self.get_delay_trigger_position()
        nr_of_sda = int(
            self.lnet.scope_data.data_array_size % self.scope_setup.get_dataset_size()
        )
        end = nr_of_sda - start
        for channel in channels:
            channels[channel] = channels[channel][start:end]
        return channels

    def get_scope_channel_data(self, valid_data=False) -> Dict[str, List[Number]]:
        """
        Get the sorted and optionally filtered scope channel data.

        Args:
            valid_data (bool, optional): If True, return only valid data. Defaults to True.

        Returns:
            Dict[str, List[Number]]: A dictionary with channel names as keys and data lists as values.
        """
        data = self._read_array_chunks()
        channels = self._sort_channel_data(data)
        return self._filter_channels(channels) if valid_data else channels
