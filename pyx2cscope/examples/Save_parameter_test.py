import logging

from parser.Elf_Parser import VariableInfo
from variable.variable import Variable_uint16

logging.basicConfig(
    level=0,
    filename="Save_parameter_test.py.log",
)
# logging.info("Start##################")
from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
import serial
from mchplnet.lnet import LNet

from pyx2cscope.variable.variable_factory import VariableFactory
from mchplnet.services.frame_save_parameter import FrameSaveParameter, ScopeConfiguration,ScopeTrigger,ScopeChannel
serial_port = "COM8"  # select COM port
baud_rate = 115200

serial_connection = InterfaceFactory.get_interface(
    IType.SERIAL, port=serial_port, baudrate=baud_rate
)
elf_file = r"C:\_DESKTOP\_Projects\LNET_PROJECT_MCLV2_DSPIC33CK256MP508\dist\default\production\LNET_PROJECT_MCLV2_DSPIC33CK256MP508.production.elf"
l_net = LNet(serial_connection)
variable_factory = VariableFactory(l_net, elf_file)

frame = FrameSaveParameter()

# Set up scope configuration
scope_config = ScopeConfiguration(
    scope_state=0x02, sample_time_factor=4, channels=[]
)
# Add channels to the scope configuration
# variable1 = variable_factory.variable_map.get("a_char")
# variable1 = VariableInfo(name="a_char", address=287454020, byte_size=1,type=0)
variable1 = Variable_uint16(name="a_char", l_net= l_net, address= 287454020)
# variable2 = variable_factory.variable_map.get("b_int")
# variables = [variable1,variable2]
scope_config.trigger = ScopeTrigger(variable=variable1, data_type= 2 , source_type= 00, source_location= 00000000, trigger_level= 0000, trigger_edge= 1, trigger_mode= 0, trigger_delay= 0)
frame.add_channels(scope_config, variable1)
response_save_parameter = l_net.save_parameter(scope_config)

print(response_save_parameter)

# # scope_config.channels.append(
# #     ScopeChannel(
# #         name="Channel 1",
# #         source_type=0x00,
# #         source_location=0xDEADCAFE,
# #         data_type_size=4,
# #     )
# # )
# # scope_config.channels.append(
# #     ScopeChannel(
# #         name="Channel 2",
# #         source_type=0x00,
# #         source_location=0x8899AABB,
# #         data_type_size=2,
# #     )
# # )
# #
# # # Set up trigger configuration
# scope_config.trigger = ScopeTrigger(
#     data_type=4,
#     source_type=0x00,
#     source_location=0x12345678,
#     trigger_level=70000,
#     trigger_delay=600,
#     trigger_edge=0x00,
#     trigger_mode=0x01,
# )
# #
# # # Set the scope configuration in the frame
# frame.set_scope_configuration(scope_config)
# #
# logging.debug(frame._get_data())
#
# # Remove a channel by name
# frame.remove_channel_by_name("Channel 2")
#
# # Convert to bytes again after removing a channel
# logging.debug(frame._get_data())
# print(frame._get_data())
