"""Demo scripting for user to get started with TCP-IP."""
import time

from pyx2cscope.utils import get_elf_file_path, get_host_address
from pyx2cscope.x2cscope import X2CScope

# Check if x2cscope was injected by the Scripting tab, otherwise create our own
if globals().get("x2cscope") is None:
    x2cscope = X2CScope(host=get_host_address(), elf_file=get_elf_file_path())

# Get stop_requested function if running from Scripting tab, otherwise use a dummy
stop_requested = globals().get("stop_requested", lambda: False)

phase_current = x2cscope.get_variable("my_counter")

x2cscope.add_scope_channel(phase_current)

x2cscope.request_scope_data()

while not stop_requested():
    if x2cscope.is_scope_data_ready():
        print(x2cscope.get_scope_channel_data())
        x2cscope.request_scope_data()
    time.sleep(0.1)

print("Script stopped.")
