"""This example can be used to try the scope functionality of pyX2Cscope and save the data acquisition in CSV file."""

import csv
import logging
import time

import matplotlib
import matplotlib.pyplot as plt

from pyx2cscope.utils import get_elf_file_path
from pyx2cscope.x2cscope import X2CScope
from pyx2cscope.x2cscope import TriggerConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# Check if x2cscope was injected by the Scripting tab, otherwise create our own
if globals().get("x2cscope") is None:
    x2cscope = X2CScope(elf_file=get_elf_file_path())

# Get stop_requested function if running from Scripting tab, otherwise use a dummy
stop_requested = globals().get("stop_requested", lambda: False)

motor_speed = x2cscope.get_variable("motorSpeedRPM")
v_ref = x2cscope.get_variable("SpeedReference")
tune = x2cscope.get_variable("RelayTuningEnable")

x2cscope.clear_all_scope_channel()
x2cscope.add_scope_channel(motor_speed)
x2cscope.add_scope_channel(v_ref)

trig = TriggerConfig(v_ref)
trig.trigger_level = 600
trig.trigger_delay = 50
trig.trigger_edge = 1
trig.trigger_mode = 1

x2cscope.set_scope_trigger(trig)

print("Connected to x2cscope, channels added, and trigger configured.")
print("Set speed to 300 RPM and wait 3 seconds to settle before capture.")
print(trig)

tune.set_value(1.0)     # enable tuning relay to apply steps to reference
v_ref.set_value(300)
time.sleep(3)       # ensure the change is applied before capture

LIVE_PNG = __file__.replace(".py", ".png")

fig, ax = plt.subplots()

print("Capturing data…")
x2cscope.set_sample_time(30)
x2cscope.request_scope_data()

time.sleep(1)   # give it a moment to start the capture before applying the step
print("Applying step to 1000 RPM …")
v_ref.set_value(1000) # set step to 1000

while not stop_requested():
    if x2cscope.is_scope_data_ready():
        break
    time.sleep(0.1)

print("Data ready, processing…")
tune.set_value(0) 

ax.clear()
for channel, data in x2cscope.get_scope_channel_data().items():
    time_values = [i * 0.0015 for i in range(len(data))]  # ms
    ax.plot(time_values, data, label=f"{channel}")

ax.set_xlabel("Time (ms)")
ax.set_ylabel("Value")
ax.legend()
fig.tight_layout()

# Overwrite the same file each frame — open it in any image viewer
fig.savefig(LIVE_PNG, dpi=100)
plt.close(fig)
print("finish")
