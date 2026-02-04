"""Demo scripting for user to get started with TCP-IP."""
import time

from pyx2cscope.x2cscope import X2CScope

elf_file = r"path to your elf file.elf"
host_address = r"IP address of your device"
# The device should have a TCP server enabled listening at port 12666

x2cscope = X2CScope(host=host_address, elf_file=elf_file)

phase_current = x2cscope.get_variable("motor.iabc.a")
phase_voltage = x2cscope.get_variable("motor.vabc.a")

x2cscope.add_scope_channel(phase_current)
x2cscope.add_scope_channel(phase_voltage)

x2cscope.request_scope_data()

while True:
    if x2cscope.is_scope_data_ready():
        print(x2cscope.get_scope_channel_data())
        x2cscope.request_scope_data()
    time.sleep(0.1)