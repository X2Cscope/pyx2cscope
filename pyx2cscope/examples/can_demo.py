"""Demo scripting for user to get started with CAN interface."""
import time

from mchplnet.interfaces.factory import InterfaceType
from pyx2cscope.utils import get_can_config, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope


# Check if x2cscope was injected by the Scripting tab, otherwise create our own
if globals().get("x2cscope") is None:
    # Get configuration from config.ini
    # check documentation for details on how to set up CAN parameters in the config file
    can_config = get_can_config()
    x2cscope = X2CScope(
        elf_file=get_elf_file_path(),
        **can_config # Unpacks all CAN parameters
    )

# Get stop_requested function if running from Scripting tab, otherwise use a dummy
stop_requested = globals().get("stop_requested", lambda: False)

# Connect to the device
# x2cscope.connect()

try:
    # Get a variable to monitor
    counter = x2cscope.get_variable("u16Counter")

    # Add it to the scope channel
    x2cscope.add_scope_channel(counter)

    # Request initial scope data
    x2cscope.request_scope_data()

    # Main loop
    while not stop_requested():
        if x2cscope.is_scope_data_ready():
            scope_data = x2cscope.get_scope_channel_data()
            print(scope_data)
            x2cscope.request_scope_data()
        time.sleep(0.1)

    print("Script stopped.")

finally:
    # Disconnect from the device
    x2cscope.disconnect()
