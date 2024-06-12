# How-To

## WatchView

### Getting Started with Scripting

1. You can install the module using pip: <br>`pip install pyx2cscope`
![MCU<->PC](/images/pyx2cscopeConsole.gif)
2. Go to the [Examples](https://github.com/X2Cscope/pyx2cscope/tree/develop/pyx2cscope/examples) directory in the pyX2Cscope project to check out the available examples or create a new .py file according to your requirements.
3. start with importing pyX2Cscope:  `import pyx2cscope`
4. Choose the communication interface from the interfaces' module. Currently, **Only Serial** is supported: CAN and LIN coming in near future: <br> 
```
from xc2scope import X2CScope
``` 
5. Initiate the X2CScope and provide the desired COM port, by default baud rate is set to **_115200_**. . If there's a need to change the baud rate, include the baud_rate parameter with your preferred baud rate, In the same way other setting could be made:
```
x2cScope = X2CScope(port="COM16", elf_file=elf_file)
```  
6. Replace the **elf_file** with the path to the ELF file of your project.
7. Create a Variable object for the variable you want to monitor:
```
variable = x2cScope.get_variable('Variable_name')
```
8. Replace 'Variable_name' with the name of the variable you want to monitor. You can create multiple variable objects as required. 
9. Once you have gone through these steps, you can use the **get_value()** function to retrieve the value of the variable:
``` 
variable.get_value() 
```
10. To set the value for the respective variable **set_value()**:
```
variable.set_value(value)
```
