"""Demo scripting for user to get started."""
from pyx2cscope.x2cscope import X2CScope

elf_file =r"path to your elf file.elf"

x2cscope = X2CScope(port="COM39", elf_file=elf_file)

phase_current = x2cscope.get_variable("motor.iabc.a")
phase_voltage = x2cscope.get_variable("motor.vabc.a")

x2cscope.add_scope_channel(phase_current)
x2cscope.add_scope_channel(phase_voltage)

x2cscope.request_scope_data()

while True:
    if x2cscope.is_scope_data_ready():
        print(x2cscope.get_scope_channel_data())