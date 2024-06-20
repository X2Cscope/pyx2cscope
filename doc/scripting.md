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

Once you have gone through these steps, you can use the method **get_value()** to retrieve the actual 
value of the variable
``` 
variable.get_value() 
```
10. To set the value for the respective variable **set_value()**:
```
variable.set_value(value)
```
## ScopeView
1. To use the scope functionality, add channel to the scope: **add_scope_channel(variable: Variable)** : 
```
x2cScope.add_scope_channel(variable1)
x2cScope.add_scope_channel(variable2)
```
2. To remove channel: **remove_scope_channel(variable: Variable)**:
```
x2cScope.remove_scope_channel(variable2)
```
3. Up to 8 channels can be added. 
4. To Set up Trigger, any available variable can be selected, by default works on no trigger configuration.
```
x2cscope.set_scope_trigger(variable: Variable, trigger_level: int, trigger_mode: int, trigger_delay: int, trigger_edge: int)
```
5. ##### Trigger Parameters:
```
srcChannel: TriggerChannel (variable)
Level: trigger_level
Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
Trigger_delay = Value > 0 Pre-trigger, Value < 0 Post trigger
Trigger_Edge: Rising (1) or Falling (0)
```

```
x2cScope.set_scope_trigger(variable3, trigger_level=500, trigger_mode=1, trigger_delay=50, trigger_edge=1)
```

6. ##### **clear_trigger()**: Clears and diable trigger
```
x2cscope.clear_trigger()
```
7. #### set_sample_time(sample_time: int): 
This paramater defines a pre-scaler when the scope is in the sampling mode. This can be used to extend total sampling time at cost of resolution. 0 = every sample, 1 = every 2nd sample, 2 = every 3rd sample .....
```
x2cScope.set_sample_time(2)
```
8. #### is_scope_data_ready(self) -> bool: 
Returns Scope sampling state. Returns: true if sampling has completed, false if it’s yet in progress.  
```
while not x2cScope.is_scope_data_ready():
    time.sleep(0.1)
```
9. #### get_scope_channel_data(valid_data=False) -> Dict[str, List[Number]]: 
Once sampling is completed, this function could be used to get the sampled data.
```
data = x2cScope.get_scope_channel_data()
```
