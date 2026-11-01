"""Demo scripting for user to get started with CAN interface."""
import time

from pyx2cscope.utils import get_can_config, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Check if x2cscope was injected by the Scripting tab, otherwise create our own
owns_connection = globals().get("x2cscope") is None
if owns_connection:
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
    # Disconnect only if this script opened the connection; an injected
    # instance belongs to the GUI and must stay connected.
    if owns_connection:
        x2cscope.disconnect()
