import time

from pyx2cscope.xc2scope import X2CScope
from utils import get_elf_file_path, get_com_port

elf_file = get_elf_file_path()
com_port = get_com_port()
x2cScope = X2CScope(port=com_port, elf_file=elf_file)
ser = x2cScope.interface

torque_current = x2cScope.get_variable("motor.idq.q")

while 1:
    start_time = time.time()
    print(torque_current.get_value())
    end_time = time.time()
    print("time to send and receive one request:", end_time - start_time)
