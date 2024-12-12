# GUI Qt

The Graphic User Interface implemented on Qt is an App built over pyX2Cscope.
The aim of this application is to serve as an example of how to make a desktop
application.

## Starting the GUI Qt

The GUI Qt is currently the default GUI, it runs out-of-the-box when running the command below:

```
python -m pyx2cscope 
``` 

It can also be executed over argument -q

```
python -m pyx2cscope -q
``` 

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
