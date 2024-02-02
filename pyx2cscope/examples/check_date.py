import logging

logging.basicConfig(level=logging.DEBUG)
import time

from pyx2cscope.xc2scope import X2CScope

serial_port = "COM16"  # select COM port
baud_rate = 115200
elf_file = r"C:\Users\m67250\OneDrive - Microchip Technology Inc\Desktop\testing_x2cscope.X\dist\default\production\testing_x2cscope.X.production.elf"

x2cscope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)
serial_connection = x2cscope.interface

variable2 = x2cscope.get_variable("ScopeArray")

variable2.get_value()
start_time = time.time()
variable2.set_value(8192)

print(variable2.get_value())
end_time = time.time()
print(end_time - start_time)
