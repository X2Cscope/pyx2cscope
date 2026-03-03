This Scripting Section allows you to run Python scripts without the use of an IDE. You can load Python scripts and run them standalone as the examples available under PyX2Cscope examples folder. Otherwise you can take advantage of this App and use the Setup tab to connect to your device. Doing this, the script has access to the x2cscope connection and some methods as described below.

For further information, check the PyX2Cscope scripting documentation at:

[https://x2cscope.github.io/pyx2cscope/scripting.html](https://x2cscope.github.io/pyx2cscope/scripting.html)


## Available Objects/Functions

- **x2cscope** - The X2CScope instance (or `None` if not connected)
- **stop_requested()** - Returns `True` when Stop button is pressed

---

## Basic Example

```python
var = x2cscope.get_variable("myVariable")
value = var.get_value()
print(f"Current value: {value}")
```

## Write a Value

```python
var = x2cscope.get_variable("myVariable")
var.set_value(123.45)
print("Value written successfully")
```

## Read Multiple Variables

```python
variables = ["var1", "var2", "var3"]
for name in variables:
    var = x2cscope.get_variable(name)
    if var:
        print(f"{name} = {var.get_value()}")
```

## List All Variables

```python
all_vars = x2cscope.list_variables()
for name in all_vars[:10]:  # First 10
    print(name)
```

---

## Loop with Stop Support

Use `stop_requested()` to make your loops respond to the **Stop** button:

```python
import time

while not stop_requested():
    var = x2cscope.get_variable("myVar")
    print(f"Value: {var.get_value()}")
    time.sleep(0.5)

print("Script stopped gracefully")
```

---

## Script that Works Both Standalone and in App

Use `globals().get()` to check if variables are injected:

```python
from pyx2cscope.x2cscope import X2CScope
from pyx2cscope.utils import get_elf_file_path
import time

# Use injected x2cscope or create our own
if globals().get("x2cscope") is None:
    x2cscope = X2CScope(port="COM3", elf_file=get_elf_file_path())

# Use injected stop_requested or a dummy
stop_requested = globals().get("stop_requested", lambda: False)

while not stop_requested():
    var = x2cscope.get_variable("myVar")
    print(var.get_value())
    time.sleep(0.5)
```

---

## Create Your Own Connection (Standalone Mode)

If you want to run independently from the GUI connection:

```python
from pyx2cscope.x2cscope import X2CScope

# Create new connection (will fail if GUI is already connected!)
my_scope = X2CScope(port="COM3", elf_file="path/to/your.elf")

# Use my_scope instead of x2cscope
var = my_scope.get_variable("myVar")
print(var.get_value())
```

> **Note:** Creating your own connection while the GUI is connected to the same port will cause conflicts!

---

## Scope Data Example

```python
# Add scope channels
var1 = x2cscope.get_variable("channel1")
x2cscope.add_scope_channel(var1)

# Request data
x2cscope.request_scope_data()

# Wait and get data
import time
time.sleep(0.5)
if x2cscope.is_scope_data_ready():
    data = x2cscope.get_scope_channel_data()
    print(data)
```

---

## Tips

1. Always check if **x2cscope** is available before using it
2. Use `print()` statements - output appears in **Script Output** tab
3. Use `stop_requested()` in loops so the **Stop** button works
4. Enable "Log output to file" to save output to a file
5. The script runs in the same process as the GUI, so avoid blocking operations that take too long
6. Changes made to variables affect the actual hardware!
