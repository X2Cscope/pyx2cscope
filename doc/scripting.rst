API Interface
=============


The API interface is managed over the X2CScope class. 

Simplest example
----------------

.. literalinclude:: ../pyx2cscope/examples/simplest.py
    :language: python
    :linenos:

Further examples in the repository: https://github.com/X2Cscope/pyx2cscope/tree/main/pyx2cscope/examples


X2CScope class
--------------

1. Import the X2Cscope class:

.. code-block:: python

    from pyx2scope import X2CScope

X2CScope supports multiple communication interfaces: **Serial**, **CAN**, and **TCP/IP**.

Communication Interfaces
^^^^^^^^^^^^^^^^^^^^^^^^

**Serial (UART) Interface**

The most common interface for connecting to microcontrollers. Parameters:

.. list-table::
   :widths: 20 15 15 50
   :header-rows: 1

   * - Parameter
     - Type
     - Default
     - Description
   * - ``port``
     - str
     - "COM1"
     - Serial port name (e.g., "COM3", "/dev/ttyUSB0")
   * - ``baud_rate``
     - int
     - 115200
     - Communication speed in bits per second
   * - ``parity``
     - int
     - 0
     - Parity setting (0=None)
   * - ``stop_bit``
     - int
     - 1
     - Number of stop bits
   * - ``data_bits``
     - int
     - 8
     - Number of data bits

Example - Serial connection with default baud rate:

.. code-block:: python

    x2c_scope = X2CScope(port="COM16", elf_file="firmware.elf")

Example - Serial connection with custom baud rate:

.. code-block:: python

    x2c_scope = X2CScope(port="COM16", baud_rate=9600, elf_file="firmware.elf")

**TCP/IP Interface**

For network-based connections to embedded systems with Ethernet capability. Parameters:

.. list-table::
   :widths: 20 15 15 50
   :header-rows: 1

   * - Parameter
     - Type
     - Default
     - Description
   * - ``host``
     - str
     - "localhost"
     - IP address or hostname of the target device
   * - ``tcp_port``
     - int
     - 12666
     - TCP port number for the connection
   * - ``timeout``
     - float
     - 0.1
     - Connection timeout in seconds

Example - TCP/IP connection with default tcp_port:

.. code-block:: python

    x2c_scope = X2CScope(host="192.168.1.100", elf_file="firmware.elf")

Example - TCP/IP with custom tcp_port:

.. code-block:: python

    x2c_scope = X2CScope(host="192.168.1.100", tcp_port=12345, elf_file="firmware.elf")

**CAN Interface**

For CAN bus communication with microcontrollers. The CAN interface supports multiple hardware vendors through the python-can library. Parameters:

.. list-table::
   :widths: 20 15 15 50
   :header-rows: 1

   * - Parameter
     - Type
     - Default
     - Description
   * - ``bustype``
     - str
     - "pcan_usb"
     - CAN interface type: "pcan_usb", "pcan_lan", "socketcan", "vector", "kvaser"
   * - ``channel``
     - int
     - 1
     - Channel number (numeric: 1, 2, 3...). Automatically converted to vendor-specific format
   * - ``baud_rate``
     - int
     - 500000
     - CAN bus baud rate in bits per second (common: 125000, 250000, 500000, 1000000)
   * - ``id_tx``
     - int
     - 0x110
     - CAN arbitration ID for transmitting messages
   * - ``id_rx``
     - int
     - 0x100
     - CAN arbitration ID for receiving messages
   * - ``mode``
     - str
     - "standard"
     - CAN ID mode: "standard" (11-bit) or "extended" (29-bit)

**Supported CAN Interfaces:**

- **PCAN USB** (``bustype="pcan_usb"``): Peak-System USB CAN adapters
- **PCAN LAN** (``bustype="pcan_lan"``): Peak-System Ethernet CAN gateways
- **SocketCAN** (``bustype="socketcan"``): Linux native CAN interface
- **Vector** (``bustype="vector"``): Vector CAN hardware
- **Kvaser** (``bustype="kvaser"``): Kvaser CAN interfaces

.. note::

   CAN interface support requires the ``python-can`` library and vendor-specific drivers:

   - **PCAN**: Requires PCAN driver installation from Peak-System website
   - **SocketCAN**: Built into Linux kernel (no additional driver needed)
   - **Vector**: Requires Vector driver installation
   - **Kvaser**: Requires Kvaser driver installation

   The ``python-can`` package includes base support for all vendors, but hardware-specific
   drivers must be installed separately according to each vendor's documentation.

Example - CAN connection with PCAN USB (default settings):

.. code-block:: python

    x2c_scope = X2CScope(bustype="pcan_usb", channel=1, elf_file="firmware.elf")

Example - CAN connection with custom parameters:

.. code-block:: python

    x2c_scope = X2CScope(
        bustype="pcan_usb",
        channel=2,
        baud_rate=250000,
        id_tx=0x120,
        id_rx=0x110,
        mode="extended",
        elf_file="firmware.elf"
    )

Example - SocketCAN on Linux:

.. code-block:: python

    x2c_scope = X2CScope(
        bustype="socketcan",
        channel=1,  # Maps to can0
        baud_rate=500000,
        elf_file="firmware.elf"
    )

Example - Using configuration file:

.. code-block:: python

    from pyx2cscope.utils import get_can_config, get_elf_file_path

    can_config = get_can_config()  # Loads CAN parameters from config.ini
    x2c_scope = X2CScope(
        elf_file=get_elf_file_path(),
        **can_config  # Unpacks all CAN parameters
    )

For detailed CAN interface documentation, see the `mchplnet documentation <https://mchp-lnet.readthedocs.io/>`_.

2. Basic instantiation examples:

.. code-block:: python

    # Serial connection (most common)
    x2c_scope = X2CScope(port="COM16", elf_file="firmware.elf")

    # TCP/IP connection
    x2c_scope = X2CScope(host="192.168.1.100", elf_file="firmware.elf")

Load variables
----------------

X2Cscope needs to know which variables are currently available on the firmware. 
The list of variables can be loaded from multiple file formats: 

- Executable and Linkable Format (ELF, .elf, binary)
- Pickle (PKL, .pkl, binary) 
- Yaml (YML, .yml, text)

See more details at :ref:`Import and Export variables <import-and-export-variables>` section.
The ELF file is one artifact generated during code compilation. To load the variables, Execute
the code below:

.. code-block:: python

    x2c_scope.import_variables(r"..\..\tests\data\dsPIC33ak128mc106_foc.elf")

Variable class
--------------

X2CScope class handles variables, either for retrieving and writing values as well for plotting graphics.
The next step is to get a variable object that will represent the variable inside the microcontroller.
Use the method `get_variable` to link to a desired variable. The only parameter needed for that method
is a string containing the variable name.

3. Create a Variable object for the variable you want to monitor:

.. code-block:: python

    variable = x2c_scope.get_variable('variable_name')

Replace 'variable_name' with the name of the variable you want to monitor. You can create multiple variable 
objects as required. To get variables that are underneath a struct, use the "dot" convention: 
"struct_name.variable". It is only possible to link to **final** variables, i.e., it is not possible to
link to a structure directly, only to its members.

Reading values
^^^^^^^^^^^^^^

4. Once you have gone through these steps, you can use the method **get_value()** to retrieve the actual 
value of the variable:

.. code-block:: python

    variable.get_value()

Writing values
^^^^^^^^^^^^^^

5. To set the value for the respective variable use the method **set_value()**:

.. code-block:: python

    variable.set_value(value)

Special Function Registers (SFR)
---------------------------------

In addition to firmware variables, pyX2Cscope can access **Special Function Registers (SFRs)** —
hardware peripheral registers with fixed addresses defined in the MCU's ELF file (e.g. ``LATD``,
``TMR1``, ``PORTA``). SFR access uses the same ``Variable`` interface as ordinary variables, so
``get_value()`` and ``set_value()`` work identically.

Listing available SFRs
^^^^^^^^^^^^^^^^^^^^^^^

Use ``list_sfr()`` to retrieve a sorted list of all SFR names parsed from the ELF file:

.. code-block:: python

    sfr_names = x2c_scope.list_sfr()
    print(sfr_names)
    # ['ADCON1', 'ADCON2', ..., 'LATD', ..., 'TMR1', ...]

This is the SFR counterpart of ``list_variables()``, which lists firmware variables only.

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Method
     - Description
   * - ``list_variables()``
     - Returns all firmware (DWARF) variable names from the ELF symbol table.
   * - ``list_sfr()``
     - Returns all peripheral register (SFR) names from the ELF register map.

Retrieving an SFR variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pass ``sfr=True`` to ``get_variable()`` to look up the name in the SFR register map instead of
the firmware variable table:

.. code-block:: python

    latd = x2c_scope.get_variable("LATD", sfr=True)
    tmr1 = x2c_scope.get_variable("TMR1", sfr=True)

The returned object is a standard ``Variable`` instance — read and write it the same way:

.. code-block:: python

    # Read the current register value
    value = latd.get_value()
    print(f"LATD = 0x{value:04X}")

    # Write a new value to the register
    latd.set_value(value | (1 << 12))   # set bit 12 (LATE12)

.. note::

    ``get_variable("NAME")`` and ``get_variable("NAME", sfr=False)`` both search the firmware
    variable map.  ``get_variable("NAME", sfr=True)`` searches the SFR register map.  The two
    namespaces are independent — a name can exist in both without conflict.

Full SFR example
^^^^^^^^^^^^^^^^

.. literalinclude:: ../pyx2cscope/examples/SFR_Example.py
    :language: python
    :linenos:

.. _import-and-export-variables:

Import and Export variables
---------------------------

Easiest way to assembly a variable list is to import it from an elf file. The elf file is the output of the firmware compilation 
and contains all the information about the variables, their addresses, and sizes.
Once the list of variables are available from the elf file, it can be exported to a pickle binary file or a YML text file.
It is possible to export selected variables or the whole list of variables. 
Having the exported file (yml or pickle) it is possible to import it back to the X2CScope object.
YML is human readable and can be edited with any text editor, while pickle is a binary file and can be used to store the variables in a more secure way.

Exported files preserve both firmware variables and SFR entries. If a selected list contains SFRs,
they are stored in the register section of the export file and can be imported again with
``get_variable("NAME", sfr=True)``.

See the example below:

.. literalinclude:: ../pyx2cscope/examples/export_import_variables.py
    :language: python
    :linenos:

Scope Channel
-------------

X2CScope class provide means to retrieve scope data, i.e., instead of getting the current value of
a variable, collect the values during a time frame, triggering according some trigger values or not,
and return and array that could be plotted with any available python graphic framework as matplotlib,
seaborn, etc.

1. To use the scope functionality, first you need to link a variable as previously explained, and 
add this variable to the scope by means of the method: **add_scope_channel(variable: Variable)** :

.. code-block:: python

    variable1 = x2c_scope.get_variable("variable1")
    variable2 = x2c_scope.get_variable("variable2")

    x2c_scope.add_scope_channel(variable1)
    x2c_scope.add_scope_channel(variable2)

2. To remove a variable from the scope: **remove_scope_channel(variable: Variable)**, to clear all
variables and reset the scope use instead: **clear_all_scope_channel()**

.. code-block:: python

    x2c_scope.remove_scope_channel(variable2)

or

.. code-block:: python

    x2c_scope.clear_all_scope_channel()

Up to 8 channels can be added. Each time you add or remove a variable, the number of channels present
on the channel are returned.

Getting Data from Scope
^^^^^^^^^^^^^^^^^^^^^^^

To get data from scope channel you need to follow this sequence:

::

    +------------------------------------+
    | Add variables to the scope channel |
    +------------------------------------+
                |
                v
    +--------------------------+
    | Request scope data       | <---------------+
    +--------------------------+                 | 
                |                                |
                v                                |
    +--------------------------+                 |
    | Is scope data ready?     |                 |
    +--------------------------+                 |
        / Yes          \ No                      |
        v               v                        |
    +-----------------+  +--------------------+  |
    | Handle the data |  | Execute some delay |  |
    +-----------------+  +--------------------+  |
            |                 |                  |
            +-----------------+------------------+


Step-by-step you need:

1. Request to X2CScope to collect data for the variables registered on the scope channels.

.. code-block:: python

    x2c_scope.request_scope_data()

2. Check if the data is ready: 
Returns Scope sampling state. Returns: true if sampling has completed, false if it’s yet in progress.

.. code-block:: python

    while not x2c_scope.is_scope_data_ready():
            time.sleep(0.1)

3. Get the scope data once sampling is completed

.. code-block:: python

    data = x2c_scope.get_scope_channel_data()

A simple loop request example to get only 1 frame of scope data is depicted below:

.. code-block:: python

    # request scope to start sampling data
    x2c_scope.request_scope_data()

    # wait while the data is not yet ready for reading
    while not x2c_scope.is_scope_data_ready():
            time.sleep(0.1)

    for channel, data in x2c_scope.get_scope_channel_data().items():
            # Do something with the data. 
            # channel contains the variable name, data is an array of values 

Triggering
^^^^^^^^^^

To set up a Trigger, any variable added to the scope channel can be selected. 
By default, there is no trigger selected.
To set any trigger configuration, you need to pass a TriggerConfig imported from pyx2cscope.x2cscope

.. code-block:: python

    trigger_config = TriggerConfig(Variable, trigger_level: float, trigger_mode: int, trigger_delay: int, trigger_edge: int)
    x2cscope.set_scope_trigger(trigger_config)

TriggerConfig needs some parameters like the variable and some trigger values like:

* Variable: the variable which will be monitored
* Trigger_Level: at which level the trigger will start executing (float)
* Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
* Trigger_delay: Value > 0 Pre-trigger, Value < 0 Post trigger
* Trigger_Edge: Rising (1) or Falling (0)

Data resolution
^^^^^^^^^^^^^^^

The scope sampling resolution can be adjusted with ``set_sample_time()``.

.. code-block:: python

    x2c_scope.set_sample_time(sample_time)

``sample_time`` starts at ``1`` in the pyX2Cscope API and interfaces:

* ``1``: take every sample
* ``2``: take every second sample
* ``3``: take every third sample

Higher values increase the total captured time window, but reduce the time resolution of the acquired data.
In other words, the scope skips more firmware samples before storing the next point in the scope buffer.

Internally, LNET uses a 0-based value, but pyX2Cscope exposes this parameter as 1-based in the API and interfaces.

Additional information on how to change triggers, clear and change sample time, may be
found on the API documentation.

Utility Functions
-----------------

The ``pyx2cscope.utils`` module provides helper functions for managing configuration settings
used in examples and scripts. These utilities simplify the process of specifying ELF file paths
and communication parameters without hardcoding them into your scripts.

Configuration File (config.ini)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When any utility function is called for the first time, a ``config.ini`` file is automatically
generated in the current working directory if it doesn't already exist. This file contains
default placeholder values that you should update with your actual settings:

.. code-block:: ini

    [ELF_FILE]
    path = path_to_your_elf_file

    [COM_PORT]
    com_port = your_com_port, ex:COM3

    [HOST_IP]
    host_ip = your_host_ip

    [CAN]
    bustype = pcan_usb
    channel = 1
    baud_rate = 500000
    id_tx = 0x110
    id_rx = 0x100
    mode = standard

After the file is created, edit it to specify your actual ELF path and the connection settings
needed for Serial, TCP/IP, or CAN.

Available Functions
^^^^^^^^^^^^^^^^^^^

**get_elf_file_path()**

Retrieves the ELF file path from the configuration:

.. code-block:: python

    from pyx2cscope.utils import get_elf_file_path

    elf_path = get_elf_file_path()
    if elf_path:
        x2cscope = X2CScope(port="COM8", elf_file=elf_path)

**get_com_port()**

Retrieves the COM port from the configuration:

.. code-block:: python

    from pyx2cscope.utils import get_com_port

    port = get_com_port()
    if port:
        x2cscope = X2CScope(port=port, elf_file="firmware.elf")

**get_host_address()**

Retrieves the host IP address for TCP/IP connections:

.. code-block:: python

    from pyx2cscope.utils import get_host_address

    host = get_host_address()
    if host:
        x2cscope = X2CScope(host=host, tcp_port=12666, elf_file="firmware.elf")

**get_can_config()**

Retrieves the CAN interface configuration from the ``[CAN]`` section in ``config.ini``:

.. code-block:: python

    from pyx2cscope.utils import get_can_config

    can_config = get_can_config()
    x2cscope = X2CScope(elf_file="firmware.elf", **can_config)

The returned dictionary contains these parameters:

* ``bustype``
* ``channel``
* ``baud_rate``
* ``id_tx``
* ``id_rx``
* ``mode``



Example Usage
^^^^^^^^^^^^^

The utility functions are particularly useful in example scripts where you want to avoid
hardcoding paths and interface settings:

.. code-block:: python

    from pyx2cscope import X2CScope
    from pyx2cscope.utils import get_elf_file_path, get_com_port

    # Get configuration from config.ini
    elf_path = get_elf_file_path()
    port = get_com_port()

    if not elf_path or not port:
        print("Please configure config.ini with your ELF file path and COM port")
        exit(1)

    # Initialize X2CScope with configured values
    x2cscope = X2CScope(port=port, elf_file=elf_path)

For CAN, the same approach can be used with the CAN configuration block:

.. code-block:: python

    from pyx2cscope import X2CScope
    from pyx2cscope.utils import get_can_config, get_elf_file_path

    elf_path = get_elf_file_path()
    can_config = get_can_config()

    if not elf_path:
        print("Please configure config.ini with your ELF file path")
        exit(1)

    x2cscope = X2CScope(elf_file=elf_path, **can_config)

For TCP/IP, the host address can also be loaded from the configuration file:

.. code-block:: python

    from pyx2cscope import X2CScope
    from pyx2cscope.utils import get_elf_file_path, get_host_address

    elf_path = get_elf_file_path()
    host = get_host_address()

    if not elf_path or not host:
        print("Please configure config.ini with your ELF file path and host IP")
        exit(1)

    x2cscope = X2CScope(elf_file=elf_path, host=host)

.. note::

    The utility functions return an empty string if the configuration contains placeholder
    values (containing "your"). This allows you to check if the configuration has been
    properly set up before proceeding.
