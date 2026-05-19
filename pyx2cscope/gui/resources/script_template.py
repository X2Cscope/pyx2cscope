"""pyX2Cscope script template.

When executed from the Scripting tab the variable ``x2cscope`` is
automatically injected into this script's namespace.  It holds the live
:class:`~pyx2cscope.x2cscope.X2CScope` instance when the application is
connected, or ``None`` when it is not.

``stop_requested`` is also injected: a callable that returns ``True`` once
the user presses the *Stop* button.  Call it inside every loop iteration so
the script can be interrupted gracefully.
"""
import time

from pyx2cscope.utils import get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Check if x2cscope was injected by the Scripting tab, otherwise create our own
if globals().get("x2cscope") is None:
    x2cscope = X2CScope(elf_file=get_elf_file_path())

# Get stop_requested function if running from Scripting tab, otherwise use a dummy
stop_requested = globals().get("stop_requested", lambda: False)

# ------------------------------------------------------------------
# List available variables (handy during development)
# ------------------------------------------------------------------
variable_names = x2cscope.get_variable_list()
print(f"Connected – {len(variable_names)} variables available.")
# Uncomment the next line to see all variable names:
# print("\n".join(variable_names))

# ------------------------------------------------------------------
# Example: read from and write to variables
# ------------------------------------------------------------------
var = x2cscope.get_variable("myModule.mySignal")  # adapt to your firmware
value = var.get_value()  # read the current value of the variable
print(f"Current value of {var.name} is {value}")
var.set_value(42)  # set the value of the variable

# ------------------------------------------------------------------
# Example: read a single variable in a loop
# ------------------------------------------------------------------
print("Reading 'myModule.mySignal' every 100 ms (press Stop to cancel):")
while not stop_requested():
    value = var.get_value()
    print(f"  {value}")
    time.sleep(0.1)

# ------------------------------------------------------------------
# Example: capture scope data once
# ------------------------------------------------------------------
signal_a = x2cscope.get_variable("myModule.signalA")
signal_b = x2cscope.get_variable("myModule.signalB")

x2cscope.clear_all_scope_channel()
x2cscope.add_scope_channel(signal_a)
x2cscope.add_scope_channel(signal_b)
x2cscope.set_sample_time(1) # capture every sample, adapt as needed

# Uncomment and adapt the following lines to set up triggering if needed:
# trigger = TriggerConfig(signal_a)
# trigger.trigger_level = 600
# trigger.trigger_delay = 50
# trigger.trigger_edge = 1 # trigger enable
# trigger.trigger_mode = 1 # rising edge
# x2cscope.set_scope_trigger(trigger)

x2cscope.request_scope_data()
while not x2cscope.is_scope_data_ready():
    if stop_requested():
        print("Stopped.")
        break
    time.sleep(0.05)
else:
    for channel, data in x2cscope.get_scope_channel_data().items():
        print(f"Channel {channel}: {len(data)} samples, first={data[0]:.4f}")

print("Done.")
