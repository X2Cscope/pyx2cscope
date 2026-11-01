# GUI Qt

The Graphic User Interface implemented on Qt is an App built over pyX2Cscope.
The aim of this application is to serve as an example of how to make a desktop
application.

## Starting the GUI Qt

The GUI Qt is currently the default GUI, it runs out-of-the-box when running the command below:

```
python -m pyx2cscope
```

It can also be started explicitly with the argument -q:

```
python -m pyx2cscope -q
```

## Getting Started with pyX2Cscope Reference GUI

The GUI consists of three main tabs: **Setup**, **Data Views**, and **Scripting**.

The window title shows the pyX2Cscope version and the project of the selected ELF file, e.g.
`pyX2Cscope - v0.7.1 - my_project`, so several pyX2Cscope windows running in parallel can be told
apart. The project name is taken from the project that generated the ELF file:

- MPLAB X: the project folder `my_project.X`.
- VS Code with the MPLAB extension: the project file `.vscode/my_project.mplab.json`.
- Otherwise the ELF file name without the `.elf` extension.

---

## Tab: Setup

The Setup tab is where you configure the connection to your microcontroller.

### Sessions

The Sessions group, below Device Information, reopens a project with everything you set up for it.
Sessions are available in the Qt GUI only.

A session holds the ELF/YML/PKL file, the connection settings, the WatchView and ScopeView variables
with trigger and sample settings, the view mode, and the script loaded in the Scripting tab.

- **Recent**: the last 10 projects, most recent first, shown as project name and date
  (e.g. `LAB1_HALL - 01.11.2026 21:30`). Choosing an entry only selects it. A session whose file was
  deleted is marked `(file not found)`.
- **Load Session**: opens the selected session. It fills in the file, connection and script, connects,
  and restores the WatchView and ScopeView variables. Variables that are no longer in a rebuilt ELF
  file, and a script that was moved, are reported.
- **Remove**: removes the selected session from the list.
- **Save to File... / Load from File...**: save the current session to a `.json` file or load one,
  e.g. to pass a setup to a colleague. They write and read the same file as **Save Config** and
  **Load Config** on the Data Views tab.

The recent list is updated automatically: when you connect (file and connection), and when you
disconnect or close the window (also the variables and the script). When you connect to a project for
the first time, its entry starts without variables, so the variables of the previous project are not
stored under the new one. It is stored in `recent_sessions.json` in the user configuration folder
(on Windows `%LOCALAPPDATA%\Microchip\pyX2Cscope`).

While connected, the Recent list, **Load Session**, **Remove** and **Load from File...** are disabled;
disconnect first to switch to another project.

### Connection Settings

1. **Select File**: Click `ELF / YML / PKL` to load variable information. Supported formats are `.elf`, `.yml`, and `.pkl`.

2. **Interface**: Select the communication interface:
   - **UART**: Serial communication
   - **TCP/IP**: Network communication
   - **CAN**: CAN bus communication

3. **Connect**: Press to establish the connection. The button changes to "Disconnect" when connected.

### UART Settings

- **Port**: Select the COM port from the dropdown.
  - **AUTO**: Automatically detects the first available LNet device (recommended for single device).
  - **Specific Port**: Choose a specific COM port (COM1, COM3, etc.) for manual connection.
  - **Refresh Button**: Updates the list of available ports.
- **Baud Rate**: Select the baud rate (38400, 115200, 230400, 460800, 921600).

> **Tip**: When using AUTO mode, the system will scan available COM ports and connect to the first device that responds to the LNet protocol. This is useful when the exact port number is unknown or when working across different machines.

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

### Run Script

The **Run Script** button beside the view toggles runs the script loaded in the **Scripting** tab (see below),
so you can start a script and watch its effect in WatchView and ScopeView without switching tabs.

- The button is disabled until a script is loaded in the Scripting tab with **Browse** or **New Script**.
- While the script runs, the button changes to **Stop Script**. Clicking it requests the script to stop, like
  the **Stop** button of the Scripting tab (the script must check `stop_requested()` in its loops).
- The status beside the button shows **Running...**, **Completed**, or the exit code if the script ended with
  an error. The script output and error messages are shown in the Scripting tab.

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

### Export Variables

The **Export Variables** button in the Data Views toolbar allows you to:
- Export only the variables currently selected in WatchView and ScopeView.
- Save the selection as `.yml` or `.pkl`.
- Preserve SFR selections in the exported file too.

### Save and Load Config

The **Save Config** and **Load Config** buttons allow you to:
- Save the current WatchView and ScopeView variable lists to a `.json` file.
- Load a previously saved configuration to quickly restore your setup.
- The saved file also stores the ELF file path, the connection settings and the loaded script, so that,
  when loading, the script is loaded and the system automatically attempts to reconnect.
- When a configuration is loaded while connected, the current file and connection are kept and only the
  variables and the script are loaded.

These are the same files as **Save to File...** and **Load from File...** in the Sessions group of the Setup tab.

The config file uses a **shared JSON format** that is cross-compatible with the Web GUI:

```json
{
    "watch_view": [
        {"variable": "motorSpeedRPM", "sfr": false, "live": true, "scaling": "1.0", "offset": "0.0"}
    ],
    "scope_view": [
        {"variable": "motorSpeedRPM", "sfr": false, "trigger": false, "enable": true,
         "color": "#ff0000", "gain": "1.0", "offset": "0.0"}
    ],
    "elf_file": "/path/to/firmware.elf",
    "connection": { "interface": "UART", "port": "COM3", "baud_rate": 115200 },
    "script": "/path/to/my_script.py"
}
```

A config file saved from the Web GUI (which omits `elf_file`, `connection` and `script`) can be loaded into the Qt app — the variable lists will be restored and the app will skip the reconnect step if no ELF path is present. The Web GUI ignores these keys when it loads a file saved by the Qt app.

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

The loaded script can also be started and stopped from the **Run Script** button on the Data Views tab.

### Output Tabs

- **Script Output**: Displays the actual output from your script (print statements, errors).
- **Log**: Displays timestamped system messages (script started, stopped, connection status).

### Available Objects in Scripts

When running from the Scripting tab, your script has access to:

- **x2cscope**: The X2CScope instance (or `None` if not connected via Setup tab)
- **stop_requested()**: Function that returns `True` when the Stop button is pressed

### Example Script

```python
import time

# x2cscope is None when the GUI is not connected via the Setup tab
if globals().get("x2cscope") is None:
    raise SystemExit("Connect to the target in the Setup tab first.")

stop_requested = globals().get("stop_requested", lambda: False)

# Example: Read and print a variable value
var = x2cscope.get_variable("myVar")
print(f"Value: {var.get_value()}")

# Example: Loop with stop support
while not stop_requested():
    print(var.get_value())
    time.sleep(0.5)
print("Script stopped.")
```

> **Note**: Scripts run in the same process as the GUI. If connected via the Setup tab, scripts share the same x2cscope connection, so a script must not call `x2cscope.disconnect()` on it. To write scripts that also run standalone, see [Running Scripts in the GUI](scripting_scripts.rst).
