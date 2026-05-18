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

# ------------------------------------------------------------------
# Guard: make sure we are connected before doing anything
# ------------------------------------------------------------------
if x2cscope is None:
    print("No active connection.  Please connect to the device first.")
else:
    # ------------------------------------------------------------------
    # List available variables (handy during development)
    # ------------------------------------------------------------------
    variable_names = x2cscope.get_variable_list()
    print(f"Connected – {len(variable_names)} variables available.")
    # Uncomment the next line to see all variable names:
    # print("\n".join(variable_names))

    # ------------------------------------------------------------------
    # Example: read a single variable in a loop
    # ------------------------------------------------------------------
    # var = x2cscope.get_variable("myModule.mySignal")  # adapt to your firmware

    # print("Reading 'myModule.mySignal' every 100 ms (press Stop to cancel):")
    # while not stop_requested():
    #     value = var.get_value()
    #     print(f"  {value}")
    #     time.sleep(0.1)

    # ------------------------------------------------------------------
    # Example: capture scope data once
    # ------------------------------------------------------------------
    # ch1 = x2cscope.get_variable("myModule.signalA")
    # ch2 = x2cscope.get_variable("myModule.signalB")
    # x2cscope.add_scope_channel(ch1)
    # x2cscope.add_scope_channel(ch2)
    # x2cscope.set_sample_time(1)
    #
    # x2cscope.request_scope_data()
    # while not x2cscope.is_scope_data_ready():
    #     if stop_requested():
    #         print("Stopped.")
    #         break
    #     time.sleep(0.05)
    # else:
    #     for channel, data in x2cscope.get_scope_channel_data().items():
    #         print(f"Channel {channel}: {len(data)} samples, first={data[0]:.4f}")

    print("Done.")
