<p align="center">
  <img src="https://raw.githubusercontent.com/X2Cscope/pyx2cscope/develop/pyx2cscope/gui/img/pyx2cscope.jpg?token=GHSAT0AAAAAACGXT7TPLZREQNFPHPTGHAVEZHIPUNQ" alt="pyX2Cscope Logo" width="250">
</p>

# pyX2Cscope
- pyX2Cscope is the Python implementation of the X2Cscope plugin from MPLABX.
- This will let the user use the functionality of X2Cscope even outside mplabx environment / Standalone.
- It allows user to:
  - Automated Unit Tests (TDD) using pytest
  - BDD(behaviour driven development), Framework: "Cucumber"
  - Different user interface
  - Data collection for machine learning and training models
  - Run-Time data analysis
  - Use of a Real Time AI model
  - HiL(Hardware in the loop) testing and tuning

Dor detailed documentation is hosted at GitHub.io:
[https://x2cscope.github.io/pyx2cscope/](https://x2cscope.github.io/pyx2cscope/)

## Install

Create a virtual environment and install pyx2cscope using the following commands (Windows):
```
python -m venv .venv
.venv\Scripts\activate
pip install pyx2cscope
```

It is highly recommended to install python libraries underneath a virtual environment.

Nevertheless, to install at system level, we advise to install it on user area. (Global insallation may not work.) 
Execute the following lines:

```
pip install pyx2cscope --user
```

In case you already have installed pyx2cscope, you only need to update the package to the
new version typing:
```
pip install --upgrade pyx2cscope
```
## Start GUI

The GUI interface

There are currently two implementations, one based on Qt and one Browser based. These GUIs are more examples
on how to implement your own custom interfaces than an official user interface.

To execute Qt version, type:
```
   pyx2cscope
```
To execute the Browser based version type:

```
   pyx2cscope -w
```

## Getting Started with Scripting

1. Go to the [Examples](https://github.com/X2Cscope/pyx2cscope/tree/main/pyx2cscope/examples) directory in the pyX2Cscope project to check out the available examples or create a new .py file according to your requirements.
2. start with importing pyX2Cscope:  `import pyx2cscope`
3. Choose the communication interface from the interfaces' module. Currently, **Only Serial** is supported: CAN and LIN coming in near future: <br> 
```
from xc2scope import X2CScope
``` 
1. Initiate the X2CScope and provide the desired COM port, by default baud rate is set to **_115200_**. . If there's a need to change the baud rate, include the baud_rate parameter with your preferred baud rate, In the same way other setting could be made:
```
x2cScope = X2CScope(port="COM16", elf_file=elf_file)
```  
1. Replace the **elf_file** with the path to the ELF file of your project.
2. Create a Variable object for the variable you want to monitor:
```
variable = x2cScope.get_variable('Variable_name')
```
1. Replace 'Variable_name' with the name of the variable you want to monitor. You can create multiple variable objects as required. 
2. Once you have gone through these steps, you can use the **get_value()** function to retrieve the value of the variable:
``` 
variable.get_value() 
```
1. To set the value for the respective variable **set_value()**:
```
variable.set_value(value)
```
# Scope Functionality
1. To use the scope functionality, add channel to the scope: **add_scope_channel(variable: Variable)** : 
```
x2cScope.add_scope_channel(variable1)
x2cScope.add_scope_channel(variable2)
```
1. To remove channel: **remove_scope_channel(variable: Variable)**:
```
x2cScope.remove_scope_channel(variable2)
```
1. Up to eight channels can be added. 
2. To Set up Trigger, any available variable can be selected, by default works on no trigger configuration.
```
x2cscope.set_scope_trigger(variable: Variable, trigger_level: int, trigger_mode: int, trigger_delay: int, trigger_edge: int)
```
1. ##### Trigger Parameters:
```
srcChannel: TriggerChannel (variable)
Level: trigger_level
Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
Trigger_delay = Value > 0 Pre-trigger, Value < 0 Post trigger
Trigger_Edge: Rising (1) or Falling (0)
```
#### Example
```
x2cScope.set_scope_trigger(variable3, trigger_level=500, trigger_mode=1, trigger_delay=50, trigger_edge=1)
```

1. ##### **clear_trigger()**: Clears and disable trigger
```
x2cscope.clear_trigger()
```
1. #### **set_sample_time(sample_time: int)**: This parameter defines a pre-scaler when the scope is in the sampling mode. This can be used to extend total sampling time at cost of resolution. 0 = every sample, 1 = every second sample, 2 = every third sample …
```
x2cScope.set_sample_time(2)
```
1. #### is_scope_data_ready(self) → bool: Returns Scope sampling state. Returns: true if sampling has completed, false if it’s yet in progress.  
```
while not x2cScope.is_scope_data_ready():
    time.sleep(0.1)
```
1. #### get_scope_channel_data(valid_data=False) → Dict[str, List[Number]]: Once sampling is completed, this function could be used to get the sampled data.
```
data = x2cScope.get_scope_channel_data()
```
1. #### This data now could be used according to the preference. 

## Getting Started with pyX2Cscope reference GUI
## Tab: WatchPlot
![WatchPlot](https://raw.githubusercontent.com/X2Cscope/pyx2cscope/refs/heads/main/pyx2cscope/gui/img/NewGui.jpg)
1. pyX2Cscope-GUI is based on Serial interface.
2. The Firmware of the microcontroller should have the X2Cscope library/Peripheral enabled.
3. in Tab WatchPlot, five channels values can be viewed, modified and can be plotted in the plot window.
4. In COM Port, either select **Auto Connect** or select the appropriate COM Port, Baud Rate from the drop-down menus and the ELF file of the project, the microcontroller programmed with. <br>
5. Sample time can be changed during run time as well, by default its set to 500 ms.
6. Press on **Connect**
7. Once the connection between pyX2Cscope and Microcontroller takes place, the buttons will be enabled.
8. Information related to the microcontroller will be displayed in the top-left corner.  

## Tab: ScopeView
![ScopeView](https://raw.githubusercontent.com/X2Cscope/pyx2cscope/refs/heads/main/pyx2cscope/gui/img/NewGui2.jpg)

1. ScopeView supports up to 8 PWM resolution channels for precise signal control.
2. You can configure all trigger settings directly within the window. To enable the trigger for a variable, check the corresponding trigger checkbox.
3. To apply modifications during sampling, first stop the sampling, make the necessary changes, then click Sample again to update and apply the modifications.
4. From the plot window, User can export the plot in various formats, including CSV, image files, Matplotlib Window, and Scalable Vector Graphics (SVG).
5. To zoom in on the plot, left-click and drag on the desired area. To return to the original view, right-click and select View All.

## Tab: WatchView
![WatchView](https://raw.githubusercontent.com/X2Cscope/pyx2cscope/refs/heads/main/pyx2cscope/gui/img/NewGui3.jpg)

1. WatchView lets users add or remove variables as needed. To remove a variable, click the Remove button next to it.
2. Users can visualize variables in live mode with an update rate of 500 milliseconds. This rate is the default setting and cannot be changed.
3. Users can select, view, and modify all global variables during runtime, providing real-time control and adjustments.

## Save and Load Config. 
1. The Save and Load buttons, found at the bottom of the GUI, allow users to save or load the entire configuration, including the COM Port, Baud Rate, ELF file path, and all other selected variables across different tabs. This ensures a consistent setup, regardless of which tab is active.
2. When a pre-saved configuration file is loaded, the system will automatically attempt to load the ELF file and establish a connection. If the ELF file is missing or unavailable at the specified path, user will need to manually select the correct ELF file path.

## Contribute
If you discover a bug or have an idea for an improvement, we encourage you to contribute! You can do so by following these steps:

1. Fork the pyX2Cscope repository.
2. Create a new branch for your changes.
3. Make the necessary changes and commit them. 
4. Push your changes to your forked repository. 
5. Open a pull request on the main pyX2Cscope repository, describing your changes.

We appreciate your contribution!



-------------------------------------------------------------------



