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

X2CScope class needs one parameter to be instantiated:

- **port**: The desired communication port name, i.e.:"COM3", "dev/ttyUSB", etc.

X2CScope will support multiple communication interfaces. Currently, only **Serial** is supported: CAN, LIN, 
and TCP/IP are coming in near future. For serial, the only parameter needed is the desired port name, by 
default baud rate is set to **115200**. If there's a need to change the baud rate, include the baud_rate 
parameter with your preferred baud rate.

2. Instantiate X2CScope with the serial port number:

.. code-block:: python

    x2c_scope = X2CScope(port="COM16")

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

    x2c_scope.import_variables(r"..\..\tests\data\qspin_foc_same54.elf")

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

.. _import-and-export-variables:

Import and Export variables
---------------------------

Easiest way to assembly a variable list is to import it from an elf file. The elf file is the output of the firmware compilation 
and contains all the information about the variables, their addresses, and sizes.
Once the list of variables are available from the elf file, it can be exported to a pickle binary file or a YML text file.
It is possible to export selected variables or the whole list of variables. 
Having the exported file (yml or pickle) it is possible to import it back to the X2CScope object.
YML is human readable and can be edited with any text editor, while pickle is a binary file and can be used to store the variables in a more secure way.

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

    trigger_config = TriggerConfig(Variable, trigger_level: int, trigger_mode: int, trigger_delay: int, trigger_edge: int)
    x2cscope.set_scope_trigger(trigger_config)

TriggerConfig needs some parameters like the variable and some trigger values like:

* Variable: the variable which will be monitored
* Trigger_Level: at which level the trigger will start executing
* Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
* Trigger_delay: Value > 0 Pre-trigger, Value < 0 Post trigger
* Trigger_Edge: Rising (1) or Falling (0)

Additional information on how to change triggers, clear and change sample time, may be
found on the API documentation.
