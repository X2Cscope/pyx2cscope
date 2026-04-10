# GUI Qt

The Graphic User Interface implemented on Qt is an App built over pyX2Cscope.
The aim of this application is to serve as an example of how to make a desktop
application.

## Starting the GUI Qt

The GUI Qt is currently the default GUI, it runs out-of-the-box when running the command below:

```
python -m pyx2cscope
```

It can also be executed with the argument -q:

```
python -m pyx2cscope -q
```

## Getting Started with pyX2Cscope Reference GUI

The GUI consists of three main tabs: **Setup**, **Data Views**, and **Scripting**.

---

## Tab: Setup

The Setup tab is where you configure the connection to your microcontroller.

### Connection Settings

1. **ELF File**: Click "Select ELF file" to choose the ELF file of the project your microcontroller is programmed with.

2. **Interface**: Select the communication interface:
   - **UART**: Serial communication
   - **TCP/IP**: Network communication
   - **CAN**: CAN bus communication

3. **Connect**: Press to establish the connection. The button changes to "Disconnect" when connected.

### UART Settings

- **Port**: Select the COM port from the dropdown. Use the refresh button to update available ports.
- **Baud Rate**: Select the baud rate (38400, 115200, 230400, 460800, 921600).

### TCP/IP Settings

- **Host**: Enter the IP address or hostname of the target device.
- **Port**: Enter the TCP port number (default: 12666).

### CAN Settings

- **Bus Type**: Select the CAN interface type:
  - **PCAN USB**: Peak-System USB CAN adapters
  - **PCAN LAN**: Peak-System Ethernet CAN gateways
  - **SocketCAN**: Linux native CAN interface
  - **Vector**: Vector CAN hardware
  - **Kvaser**: Kvaser CAN interfaces
- **Channel**: Enter the CAN channel number (numeric: 1, 2, 3...).
- **Baud Rate**: Select from 125K, 250K, 500K, or 1M bits per second.
- **Mode**: Select Standard (11-bit ID) or Extended (29-bit ID).
- **Tx-ID (hex)**: Transmit arbitration ID in hexadecimal (default: 110).
- **Rx-ID (hex)**: Receive arbitration ID in hexadecimal (default: 100).

> **Note**: CAN interface requires vendor-specific drivers to be installed. See the API documentation for driver requirements.

### Device Information

Once connected, device information is displayed on the right side:
- Processor ID
- UC Width
- Date and Time
- App Version
- DSP State

> **Note**: All connection settings are automatically saved and restored on the next application start.

---

## Tab: Data Views

The Data Views tab provides two views that can be toggled independently using the buttons at the top:

- **WatchView**: Monitor and modify variable values in real-time
- **ScopeView**: Capture and visualize variable waveforms

You can enable both views simultaneously for a split-screen layout. You can change the width of each column by dragging the line between them. For this to take effect, adjust the App window size accordingly.

### WatchView

1. Click "Add Variable" to add variables to monitor.
2. Select variables from the dialog window.
3. Configure scaling and offset for each variable.
4. Enable "Live" checkbox to poll values at 500ms intervals.
5. Enter new values and click "Write" to modify variables on the device.
6. Click "Remove" to delete a variable row.

### ScopeView

1. ScopeView supports up to 8 channels for precise signal capture.
2. Select variables for each channel from the dropdown.
3. Configure trigger settings:
   - **Mode**: Auto (continuous) or Triggered
   - **Edge**: Rising or Falling
   - **Level**: Trigger threshold value
   - **Delay**: Trigger delay in samples
4. Check the "Trigger" checkbox on the channel you want to use as trigger source.
5. Click "Sample" to start capturing, "Single" for one-shot capture, or "Stop" to halt.
6. Use the plot toolbar to zoom, pan, and export data (CSV, PNG, SVG, or Matplotlib window).

### Special Function Registers (SFR)

Both **WatchView** and **ScopeView** support searching and adding Special Function Registers
(SFRs) — hardware peripheral registers such as `LATD`, `TMR1`, or `PORTA` — in addition to
ordinary firmware variables.

When the variable selection dialog opens, an **SFR** checkbox appears next to the search bar:

- When the checkbox is **unchecked** (default) the list shows firmware variables.
- When the checkbox is **checked** the list switches to SFRs parsed from the ELF file.

The checkbox is disabled (greyed out) if the connected ELF file contains no SFR entries.

Once an SFR is selected and confirmed, it is retrieved with `sfr=True` internally so it is
mapped to its fixed hardware address. From that point it behaves exactly like any other
variable — values can be read, polled live (WatchView), or captured as a scope channel
(ScopeView).

### Save and Load Config

The **Save Config** and **Load Config** buttons allow you to:
- Save the entire configuration including ELF file path, connection settings, and all variable configurations.
- Load a previously saved configuration to quickly restore your setup.
- When loading, the system automatically attempts to connect using the saved settings.

---

## Tab: Scripting

The Scripting tab allows you to run Python scripts with direct access to the x2cscope connection.

### Script Selection

1. Click **Browse** to select a Python script (.py file).
2. Click **Edit (IDLE)** to open the script in Python's IDLE editor.
3. Click **Help** for documentation on writing scripts.

### Execution Controls

1. Click **Execute** to run the selected script.
2. Click **Stop** to request the script to stop (scripts must check `stop_requested()` in loops).
3. Enable **Log output to file** and select a location to save script output.

### Output Tabs

- **Script Output**: Displays the actual output from your script (print statements, errors).
- **Log**: Displays timestamped system messages (script started, stopped, connection status).

### Available Objects in Scripts

When running from the Scripting tab, your script has access to:

- **x2cscope**: The X2CScope instance (or `None` if not connected via Setup tab)
- **stop_requested()**: Function that returns `True` when the Stop button is pressed

### Example Script

```python
# Example: Read and print a variable value
if globals().get("x2cscope") is not None:
    var = x2cscope.get_variable("myVariable")
    print(f"Value: {var.get_value()}")

# Example: Loop with stop support
stop_requested = globals().get("stop_requested", lambda: False)
while not stop_requested():
    var = x2cscope.get_variable("myVar")
    print(var.get_value())
    time.sleep(0.5)
print("Script stopped.")
```

> **Note**: Scripts run in the same process as the GUI. If connected via the Setup tab, scripts share the same x2cscope connection. Scripts can also create their own connections when running standalone.
