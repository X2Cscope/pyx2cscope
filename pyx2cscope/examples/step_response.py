"""Capture a speed step response with a triggered scope and save the plot as PNG.

Runs standalone or inside the Qt/web Scripting tab.
"""

import logging
import os
import time

import matplotlib

matplotlib.use("Agg")  # no GUI windows: the script may run in a worker thread or on a headless server
import matplotlib.pyplot as plt  # noqa: E402

from pyx2cscope.utils import get_elf_file_path  # noqa: E402
from pyx2cscope.x2cscope import TriggerConfig, X2CScope  # noqa: E402

STEP_FROM = 300  # [RPM]
STEP_TO = 1000  # [RPM]
SAMPLE_FACTOR = 30  # store every 30th sample of the scope ISR
ISR_FREQUENCY_HZ = 20_000  # rate of the firmware X2Cscope update call
SAMPLE_PERIOD_S = SAMPLE_FACTOR / ISR_FREQUENCY_HZ  # 1.5 ms
TRIGGER_LEVEL = 600  # between STEP_FROM and STEP_TO
TRIGGER_DELAY = 50  # pre-trigger samples
SETTLE_S = 3.0
PRE_TRIGGER_S = 1.0
CAPTURE_TIMEOUT_S = 30.0
POLL_S = 0.1

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# Check if x2cscope was injected by the Scripting tab, otherwise create our own
owns_connection = globals().get("x2cscope") is None
if owns_connection:
    x2cscope = X2CScope(elf_file=get_elf_file_path())

# Get stop_requested function if running from Scripting tab, otherwise use a dummy
stop_requested = globals().get("stop_requested", lambda: False)


def wait(seconds):
    """Sleep in short slices so the Stop button stays responsive."""
    end = time.time() + seconds
    while time.time() < end:
        if stop_requested():
            raise SystemExit("Stopped by user.")
        time.sleep(POLL_S)


def get_var(name):
    """Return a variable or stop the script with a clear message."""
    var = x2cscope.get_variable(name)
    if var is None:
        raise SystemExit(f"Variable '{name}' not found in the ELF file.")
    return var


tune = None
v_ref = None
v_ref_original = None
try:
    motor_speed = get_var("motorSpeedRPM")
    v_ref = get_var("SpeedReference")
    tune = get_var("RelayTuningEnable")
    v_ref_original = v_ref.get_value()

    x2cscope.clear_all_scope_channel()
    x2cscope.add_scope_channel(motor_speed)
    x2cscope.add_scope_channel(v_ref)

    trig = TriggerConfig(v_ref)
    trig.trigger_level = TRIGGER_LEVEL
    trig.trigger_delay = TRIGGER_DELAY
    trig.trigger_edge = 1  # rising edge
    trig.trigger_mode = 1  # triggered

    x2cscope.set_scope_trigger(trig)

    print("Connected to x2cscope, channels added, and trigger configured.")
    print(f"Set speed to {STEP_FROM} RPM and wait {SETTLE_S:.0f} seconds to settle before capture.")
    print(trig)

    tune.set_value(1)  # enable tuning relay to apply steps to reference
    v_ref.set_value(STEP_FROM)
    wait(SETTLE_S)  # ensure the change is applied before capture

    print("Capturing data…")
    x2cscope.set_sample_time(SAMPLE_FACTOR)
    x2cscope.request_scope_data()

    wait(PRE_TRIGGER_S)  # let the pre-trigger part of the buffer fill before applying the step
    print(f"Applying step to {STEP_TO} RPM …")
    v_ref.set_value(STEP_TO)

    deadline = time.time() + CAPTURE_TIMEOUT_S
    while not x2cscope.is_scope_data_ready():
        if stop_requested():
            raise SystemExit("Stopped by user.")
        if time.time() > deadline:
            raise SystemExit("Scope capture timed out: the trigger did not fire.")
        time.sleep(POLL_S)

    print("Data ready, processing…")

    fig, ax = plt.subplots()
    for channel, data in x2cscope.get_scope_channel_data().items():
        time_values = [i * SAMPLE_PERIOD_S for i in range(len(data))]
        ax.plot(time_values, data, label=f"{channel}")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Value")
    ax.legend()
    fig.tight_layout()

    out_png = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.path.splitext(os.path.basename(__file__))[0] + ".png",
    )
    fig.savefig(out_png, dpi=100)
    plt.close(fig)
    print(f"Plot saved to {out_png}")
finally:
    # Leave the target as we found it, also after errors or Stop
    if v_ref_original is not None:
        v_ref.set_value(v_ref_original)
    if tune is not None:
        tune.set_value(0)  # hand the reference back to the firmware
    if owns_connection:
        x2cscope.disconnect()
    print("finish")
