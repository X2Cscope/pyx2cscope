import logging
import time

from pyx2cscope.xc2scope import X2CScope
from utils import get_elf_file_path, get_com_port

logging.basicConfig(level=logging.DEBUG)

elf_file = get_elf_file_path()
serial_port = get_com_port()

x2cscope = X2CScope(port=serial_port, elf_file=elf_file)
serial_connection = x2cscope.interface

variable2 = x2cscope.get_variable("ScopeArray")

variable2.get_value()
start_time = time.time()
variable2.set_value(8192)

print(variable2.get_value())
end_time = time.time()
print(end_time - start_time)
