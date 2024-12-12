<p align="center">
  <img src="https://raw.githubusercontent.com/X2Cscope/pyx2cscope/develop/pyx2cscope/gui/img/pyx2cscope.jpg?token=GHSAT0AAAAAACGXT7TPLZREQNFPHPTGHAVEZHIPUNQ" alt="pyX2Cscope Logo" width="250">
</p>

# pyX2Cscope
The pyx2cscope Python package communicates with X2Cscope enabled firmwares running on microcontrollers. Focusing real time control applications like motor control and power conversion.
- It allows user to:
  - Read - Write variables to the embedded target in runtime
  - Record and Plot fast, continuous signals from the target firmware
  - Implement Automated Unit Tests (TDD) and HIL tests for embedded development
  - Record data in run-time for AI models
  - Implement custom user interface, dashboards for embedded applications (QT, Tkinter, Web)

Detailed documentation is hosted at GitHub.io:
[https://x2cscope.github.io/pyx2cscope/](https://x2cscope.github.io/pyx2cscope/)

## Install

Create a virtual environment and install pyx2cscope using the following commands (Windows):
```
python -m venv .venv
.venv\Scripts\activate
pip install pyx2cscope
```

## Start GUI

To execute Qt version, type:
```
   pyx2cscope
```
To execute the Browser based version type:

```
   pyx2cscope -w
```

## Basic scripting

```py
from pyx2cscope.x2cscope import X2CScope

# initialize the X2CScope class with serial port, by default baud rate is 115200
x2c_scope = X2CScope(port="COM8")
# instead of loading directly the elf file, we can import it after instantiating the X2CScope class
x2c_scope.import_variables(r"..\..\tests\data\qspin_foc_same54.elf")

# Collect some variables.
speed_reference = x2c_scope.get_variable("motor.apiData.velocityReference")
speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speed_measured.get_value())
# Write a new value to the "motor.apiData.velocityReference" variable on the target
speed_reference.set_value(1000)
```

Further [Examples](https://github.com/X2Cscope/pyx2cscope/tree/main/pyx2cscope/examples) directory in the pyX2Cscope project to check out the available examples or create a new .py file according to your requirements.

## Development

[https://github.com/X2Cscope/pyx2cscope/tree/main/doc/development.md](https://github.com/X2Cscope/pyx2cscope/tree/main/doc/development.md)

