# GUI Web

The Web Graphic User Interface is implemented using Flask, Bootstrap 5, jQuery, Socket.IO, and Chart.js.
It serves as both a fully functional interface and an example of how to build a custom GUI using pyX2Cscope.
This interface allows you to use multiple browser windows or access the application from smart devices on the same network.

The server runs by default on your local machine and does not allow external access.
The default port is 5000 and the interface will be accessible at http://localhost:5000

## Starting the Web GUI

Start the Web GUI with the following command:

```bash
python -m pyx2cscope -w
```

To open the server for external access (allowing connections from other devices on your network):

```bash
python -m pyx2cscope -w --host 0.0.0.0
```

To use a custom port:

```bash
python -m pyx2cscope -w -wp 8080
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-w` | Enable web GUI | - |
| `-wp`, `--web-port` | Web server port | 5000 |
| `--host` | Host address (use 0.0.0.0 for external access) | localhost |

## Interface Overview

The Web GUI consists of four main views accessible via the navigation bar:

1. **Setup** - Connection configuration
2. **Watch View** - Variable monitoring and modification
3. **Scope View** - Oscilloscope-like signal visualization
4. **Dashboard** - Custom widget-based monitoring
4. **Scripting** - Allows to run Python scritps with direct access to the x2cscope connection

---

## Setup View

The Setup view is the starting point for establishing a connection to your microcontroller.

### Interface Selection

Select the communication interface type:

- **Serial** - For UART/USB-to-Serial connections
- **TCP/IP** - For network-based connections
- **CAN** - For CAN bus connections (coming soon)

### Serial Configuration

When Serial is selected:

1. **UART Dropdown** - Select the COM port from the available ports list
2. **Refresh Button** - Click to rescan for available COM ports

### TCP/IP Configuration

When TCP/IP is selected:

1. **Host** - Enter the IP address or hostname of the target device (default: localhost)
2. **Port** - Enter the TCP port number (default: 12666)

### CAN Configuration (Coming Soon)

When CAN is selected:

- **Bus Type** - USB or LAN
- **Channel** - CAN channel number
- **Baudrate** - 125K, 250K, 500K, or 1M
- **Mode** - Standard or Extended
- **TX ID** - Transmit message ID (hex)
- **RX ID** - Receive message ID (hex)

### ELF File Selection

Select an ELF file (or PKL/YML import file) containing the variable information from your firmware.
Supported formats: `.elf`, `.pkl`, `.yml`

### Connecting

Click the **Connect** button to establish communication with the target device.
Once connected, the other views (Watch View, Scope View, Dashboard) become functional.

---

## Watch View

The Watch View allows you to monitor and modify variables in real-time.

### Adding Variables

1. Use the **search dropdown** to find and select a variable from the firmware
2. The variable will be added to the watch table

### Variable Table Columns

| Column | Description |
|--------|-------------|
| **Live** | Checkbox to enable/disable live updates for this variable |
| **Variable** | The variable name |
| **Type** | Data type (int, float, etc.) |
| **Value** | Current raw value from the target |
| **Scaling** | Multiplication factor applied to the value |
| **Offset** | Offset added after scaling |
| **Scaled Value** | Calculated result: (Value x Scaling) + Offset |
| **Actions** | Write value and remove buttons |

### Live Updates

- Click **Refresh** to manually update all variable values
- Use the dropdown menu to set automatic refresh rates:
  - Live @1s - Update every 1 second
  - Live @3s - Update every 3 seconds
  - Live @5s - Update every 5 seconds

### Writing Values

To modify a variable value on the target:

1. Enter a new value in the **Value** column
2. Click the **Write** button (pencil icon) in the Actions column

### Save/Load Configuration

- **Save** - Export the current watch list to a `.cfg` file
- **Load** - Import a previously saved watch list configuration

---

## Scope View

The Scope View provides oscilloscope-like functionality for capturing and visualizing fast signals.

### Scope Plot

The main chart displays captured waveforms. Features include:

- **Zoom** - Use mouse scroll or pinch gestures to zoom in/out
- **Pan** - Click and drag to pan the view
- **Reset Zoom** - Use the Chart Actions menu to reset the view
- **Export Data** - Export captured data to a file

### Sample Control

The Sample Control panel manages data acquisition:

| Control | Description |
|---------|-------------|
| **Sample** | Start continuous sampling |
| **Stop** | Stop sampling |
| **Burst** | Capture a single frame of data |
| **Sample Time** | Prescaler value for sampling rate (1 = fastest) |
| **Sampling Frequency** | Display of the calculated sampling frequency |

#### How Sampling Works

1. Click **Sample** to start continuous data acquisition
2. The firmware collects data points until the buffer is full
3. Data is transferred to the PC and displayed on the chart
4. The cycle repeats automatically until **Stop** is pressed
5. Use **Burst** mode to capture only one frame of data

### Trigger Control

The Trigger Control panel configures when data capture begins:

| Setting | Description |
|---------|-------------|
| **Trigger Enable/Disable** | Enable triggers to start capture at a specific condition |
| **Edge Detection** | Rising edge or Falling edge detection |
| **Level** | The value threshold that triggers data capture |
| **Delay** | Pre/post trigger delay (-50% to +50%) |

#### Trigger Modes

**Disabled (Auto Mode)**
- Sampling starts immediately when requested
- Useful for continuous signal monitoring

**Enabled (Triggered Mode)**
- Sampling waits until the trigger condition is met
- The trigger variable crosses the specified level in the specified direction
- Pre-trigger delay (negative): Capture data before the trigger event
- Post-trigger delay (positive): Capture data after the trigger event

#### Setting Up a Trigger

1. Enable the trigger by clicking **Enable**
2. Select **Rising** or **Falling** edge
3. Enter the trigger **Level** value
4. Set the **Delay** percentage:
   - Negative values (-50 to 0): Pre-trigger - see what happened before the event
   - Positive values (0 to +50): Post-trigger - see what happens after the event
5. Click **Update Trigger** to apply settings
6. In the Source Configuration, select which variable acts as the trigger source

### Source Configuration (Variable Channels)

Configure up to 8 scope channels:

| Column | Description |
|--------|-------------|
| **Trigger** | Radio button to select this channel as the trigger source |
| **Enable** | Checkbox to include this channel in the capture |
| **Variable** | The variable name being monitored |
| **Color** | Click to change the waveform color on the chart |
| **Gain** | Visual scaling factor for display (does not affect raw data) |
| **Offset** | Visual offset for display (does not affect raw data) |
| **Remove** | Delete this channel from the scope |

#### Adding Channels

1. Use the search dropdown to find a variable
2. The variable is automatically added as a new channel
3. Enable the channel checkbox to include it in captures

#### Tips for Best Results

- Start with **Sample Time = 1** for maximum resolution
- Increase Sample Time to capture longer time periods
- Use **Gain** to scale signals for better visualization
- Use **Offset** to separate overlapping waveforms
- Set up triggers to capture specific events consistently

---

## Dashboard View

The Dashboard provides a customizable interface with drag-and-drop widgets for monitoring and controlling variables.

### Edit Mode

Click the **Edit** button in the toolbar to enter edit mode:

- A widget palette appears on the left side
- Existing widgets can be moved and resized
- New widgets can be added from the palette

### Available Widgets

| Widget Type | Description |
|-------------|-------------|
| **Button** | Write values to variables on press/release |
| **Gauge** | Circular gauge displaying a variable value |
| **Label** | Text placeholder, no write/read of variables |
| **Number** | Numeric display of a variable |
| **Plot Logger** | Plots data continuously as a logger |
| **Plot Scope** | Plots scope data, use together with Scope Control widget |
| **Scope Control** | Variable and Trigger configuration for scope functionality |
| **Slider** | Slider control to write values to a variable |
| **Switch** | On/Off toggle switch to write values to a variable |
| **Text** | Display text values of a variable |

### Adding Widgets

1. Enter **Edit Mode**
2. Click a widget type in the palette
3. Configure the widget:
   - Select the target variable
   - Set widget-specific options (min/max values, labels, etc.)
4. Click **Add Widget**
5. Position and resize the widget on the canvas

### Widget Configuration

Each widget can be configured with:

- **Variable Name** - The firmware variable to monitor/control
- **Update Rate** - How frequently the variable value is read (see below)
- **Widget-specific settings** - Depending on widget type (ranges, colors, labels)

### Update Rate

The update rate controls how frequently a widget reads its variable value from the target device.

| Setting | Description |
|---------|-------------|
| **Off (0)** | No automatic updates - value is read only on manual refresh |
| **Live** | Update as fast as possible (continuous polling) |
| **Interval (seconds)** | Update at specified interval (0.5s, 1s, 2s, 5s, etc.) |

**Widgets that support Update Rate:**

| Widget | Update Rate | Reason |
|--------|:-----------:|--------|
| Button | Yes | May reflect current variable state |
| Gauge | Yes | Displays live variable value |
| Number | Yes | Displays live variable value |
| Plot Logger | Yes | Continuously logs data points |
| Slider | Yes | May sync with current value |
| Switch | Yes | May reflect current state |
| Text | Yes | Displays live variable value |

**Widgets that do NOT use Update Rate:**

| Widget | Reason |
|--------|--------|
| Label | Static text, no variable binding |
| Plot Scope | Uses scope sampling mechanism (controlled by Scope Control) |
| Scope Control | Configuration widget, triggers scope sampling |

### Save/Load Layout

- **Save Layout** - Save the current dashboard configuration to a JSON file
- **Load Layout** - Load a previously saved dashboard layout
- Layouts include widget positions, sizes, and configurations

### Dashboard Toolbar

| Button | Description |
|--------|-------------|
| **Edit** | Toggle edit mode on/off |
| **Save** | Save current layout |
| **Load** | Load a saved layout |
| **Export** | Export the current Dashboard to a file |
| **Import** | Import a Dashboard from a file |
| **Clear** | Remove all widgets from the dashboard |

---

## Scripting View

The Scripting view allows you to run Python scripts that interact with the connected device.

### Features

- Load and execute Python scripts
- Scripts have access to the `x2cscope` object for device communication
- Real-time output display
- Stop button to interrupt running scripts

### Script API

Scripts can use the `x2cscope` global variable, you don't need to instantiate it.

```python
# Read a variable
value = x2cscope.get_variable("motor_speed").get_value()
print(f"Motor speed: {value}")

# Write a variable
x2cscope.get_variable("target_speed").set_value(1000)

# Check if stop was requested
if stop_requested():
    print("Script stopped by user")
```

---

## Special Function Registers (SFR)

The Web GUI exposes SFR access through an **SFR** toggle switch placed inline next to every
variable search dropdown.

### Watch View and Scope View

Each view has an **SFR** toggle (Bootstrap form-switch) beside the Select2 search bar:

- When the toggle is **off** (default) the dropdown searches firmware variables.
- When the toggle is **on** the dropdown searches Special Function Registers instead.

Switching the toggle clears the current selection and reinitialises the dropdown so the next
search already queries the correct namespace. When an SFR is selected and added to the watch
or scope table it is retrieved with `sfr=True` on the backend, mapping it to its fixed
hardware address.

### Dashboard

The widget configuration modal includes the same **SFR** toggle above the variable name
selector. The toggle resets to **off** every time the modal is opened and behaves identically
to the Watch/Scope toggles described above.

---

## Tips and Best Practices

### Performance

- The web interface uses WebSocket for real-time updates
- For best performance, limit the number of live-updating variables
- Use Burst mode in Scope View for one-time captures

### Network Access

- By default, the server only accepts local connections
- Use `--host 0.0.0.0` to allow network access
- Consider network security when exposing the interface

### Browser Compatibility

The Web GUI is tested with modern browsers:
- Chrome (recommended)
- Firefox
- Edge
- Safari

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | Check COM port selection, ensure device is powered |
| No variables shown | Verify ELF file matches the running firmware |
| Scope not updating | Check that channels are enabled and sampling is started |
| Scope not updating | Check the trigger level is in range of Variable's values |
| Dashboard not saving | Ensure browser allows local storage |

---

## API Endpoints

For advanced users, the Web GUI exposes REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/connect` | POST | Establish connection |
| `/disconnect` | POST | Close connection |
| `/is-connected` | GET | Check connection status |
| `/variables` | GET | Get list of available variables |
| `/serial-ports` | GET | Get available COM ports |

Additional information can be found in the API documentation.
