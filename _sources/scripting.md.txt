# Scripting

Once you have successfully installed pyX2Cscope into your environment or python project,
start importing the X2CScope class. So you be able to read and write values from/to variables 
inside the controller. Follow the steps below to get your script running.

## X2CScope class

1. Import the X2Cscope clss:
```
from pyx2scope import X2CScope
``` 

X2CScope class needs two parameters to be instantiated:
- **port**: The desired communication port name, i.e.:"COM3", "dev/ttyUSB", etc.
- **elf_file**: The path to the elf file. 

### Port
X2CScope will support multiple communication interfaces. Currently, only **Serial** is supported: CAN, LIN, 
and TCP/IP are coming in near future. For serial, the only parameter needed is the desired port name, by 
default baud rate is set to **_115200_**. If there's a need to change the baud rate, include the baud_rate 
parameter with your preferred baud rate.

### Elf File
When compiling your C/C++ program with Microchip DevTools, two files will be generated: the .hex file which
will be flashed on the microcontroller and the .elf file, which contains the description of the variables
and addresses included into your program. X2Cscope needs this file to locate variables and its values inside
the running memory of the microcontroller. The elf file may be found under your MPLABX project folder at 
dist > production > your_elf_file.elf.

2. Once defined the desired comm port and elf file path, instantiate X2CScope:

```
x2cScope = X2CScope(port="COM16", elf_file="your_path_to_elf_file/elf_file.elf")
```  

## Variable class

X2CScope class handles variables, either for retrieving and writing values as well for plotting graphics.
The next step is to get a variable object that will represent the variable inside the microcontroller.
Use the method `get_variable` to link to a desired variable. The only parameter needed for that method
is a string containing the variable name. 

3. Create a Variable object for the variable you want to monitor:
```
variable = x2cScope.get_variable('variable_name')
```
Replace 'variable_name' with the name of the variable you want to monitor. You can create multiple variable 
objects as required. To get variables that are underneath a struct, use the "dot" convention: 
"struct_name.variable". It is only possible to link to **final** variables, i.e., it is not possible to
link to a structure directly, only to its members.

### Reading values

4. Once you have gone through these steps, you can use the method **get_value()** to retrieve the actual 
value of the variable:
``` 
variable.get_value() 
```
5. To set the value for the respective variable use the method **set_value()**:
```
variable.set_value(value)
```
## Scope Channel

X2CScope class provide means to retrieve scope data, i.e., instead of getting the current value of
a variable, collect the values during a time frame, triggering according some trigger values or not,
and return and array that could be plotted with any available python graphic framework as matplotlib,
seaborn, etc.  
 
6. To use the scope functionality, first you need to link a variable as previously explained, and 
add this variable to the scope by means of the method: **add_scope_channel(variable: Variable)** : 
```
variable1 = x2cScope.get_variable("variable1")
variable2 = x2cScope.get_variable("variable2")

x2cScope.add_scope_channel(variable1)
x2cScope.add_scope_channel(variable2)
```

7. To remove a variable from the scope: **remove_scope_channel(variable: Variable)**, to clear all
variables and reset the scope use instead: **clear_scope_channel()**
```
x2cScope.remove_scope_channel(variable2)
```
or 
```
x2cScope.clear_scope_channel()
```

Up to 8 channels can be added. Each time you add or remove a variable, the number of channels present
on the channel are returned. 

### Getting Data from Scope

To get data from scope channel you need to follow this sequence:

* Request data
* Check if data is ready (sampling is done)
    * Data is ready? Yes, get the data and handle it.
    * Data is not ready? Execute some delay and check again.
* After handling the data, start from the beginning requesting new data.

Step-by-step you need:

8. Request to X2CScope to collect data for the variables registered on the scope channels.  
```
x2c_scope.request_scope_data()
```

9. Check if the data is ready: 
Returns Scope sampling state. Returns: true if sampling has completed, false if it’s yet in progress.  
```
while not x2cScope.is_scope_data_ready():
    time.sleep(0.1)
```
10. Get the scope data once sampling is completed
```
data = x2cScope.get_scope_channel_data()
```

A simple loop request example to get only 1 frame of scope data is depicted below:
```
# request scope to start sampling data
x2c_scope.request_scope_data()
# wait while the data is not yet ready for reading
while not x2c_scope.is_scope_data_ready():
    time.sleep(0.1)
for channel, data in x2c_scope.get_scope_channel_data().items():
    # Do something with the data. 
    # channel contains the variable name, data is an array of values 
```

### Triggering 

To Set up Trigger, any available variable can be selected, by default works on no trigger configuration.
To set any trigger configuration, you need to pass a TriggerConfig imported from from pyx2cscope.xc2scope
```
trigger_config = TriggerConfig(Variable, trigger_level: int, trigger_mode: int, trigger_delay: int, trigger_edge: int)
x2cscope.set_scope_trigger(trigger_config)
```

TriggerConfig needs some parameters like the variable and some trigger values like:

* Variable: the variable which will be monitored
Trigger_Level: at which level the trigger will start executing
Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
Trigger_delay = Value > 0 Pre-trigger, Value < 0 Post trigger
Trigger_Edge: Rising (1) or Falling (0)

Additional information on how to change triggers, clear and change sample time, may be
found on the API documentation.

