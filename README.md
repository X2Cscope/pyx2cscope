<p align="center">
  <img src="https://raw.githubusercontent.com/X2Cscope/pyx2cscope/feat-faster-monitoring/pyx2cscope/gui/img/pyx2cscope.jpg" alt="pyX2Cscope Logo" width="250">
</p>

# pyX2Cscope
- pyX2Cscope is the Python implementation of the X2Cscope plugin from MPLABX.
- This will let the user use the functionality of X2Cscope even outside mplabx enviroment / Standalone.

## Getting Started with Scripting

1. You can install the module using pip: <br>`pip install pyx2cscope`
2. Go to the `Examples` directory in the pyX2Cscope project to check out the available examples or create a new .py file according to your requirements.
3. start with importing pyX2Cscope:  `import pyx2cscope`
4. Choose the communication interface from the interfaces' module. Currently, only Serial is supported: CAN and LIN coming in near future: <br> 
```
from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
``` 
5. Set up the Serial connection with the desired COM port and baud rate:
```
serial_port = "COM9"
baud_rate = 115200
interface = InterfaceFactory.get_interface(IType.SERIAL, port = serial_port, baudrate = baud_rate)
```
6. Initialize the LNet object with the serial connection:
```
l_net = pyx2cscope.LNet(interface)
```
7.  Setup the Variable factory.  
```
variable_factory = pyx2cscope.VariableFactory(l_net, elf_file)
```  
8. Replace the **elf_file** with the path to the ELF file of your project.
9. Create a Variable object for the variable you want to monitor:
```
Variable = variable_factory.get_variable_elf('Variable_name')
``` 
10. Replace 'Variable_name' with the name of the variable you want to monitor. You can create multiple variable objects as needed.
11. Once you have gone through these steps, you can use the get_value() function to retrieve the value of the variable:``Variable.get_value()``. You can also use the ``Variable.set_value(value)`` function to set the value of the variable.


## Getting Started with pyX2Cscope-GUI

1. pyX2Cscope-GUI is based on Serial interface.
2. The Firmware of the microcontroller should have the X2CScope library/Peripheral enabled.
2. Select the COM Port, Baud Rate from the drop-down menus and the ELF file of the project, the microcontroller programmed with. <br>
    ![COM-port](https://raw.githubusercontent.com/X2Cscope/pyx2cscope/feat-faster-monitoring/pyx2cscope/gui/img/Setting.jpg)
3. Sample time can be changed during run time as well, by default its set to 500ms.
4. Press on **Connect**
5. Once the connection between pyX2Cscope and Microcontroller takes place, the buttons will be enabled.


## Contribute
If you discover a bug or have an idea for an improvement, we encourage you to contribute! You can do so by following these steps:

1. Fork the pyX2Cscope repository.
2. Create a new branch for your changes.
3. Make the necessary changes and commit them. 
4. Push your changes to your forked repository. 
5. Open a pull request on the main pyX2Cscope repository, describing your changes.

We appreciate your contribution!



-------------------------------------------------------------------



