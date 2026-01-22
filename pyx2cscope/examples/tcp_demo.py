"""Demo scripting for user to get started."""
import time

from mchplnet.interfaces.factory import InterfaceType
from pyx2cscope.x2cscope import X2CScope

from pyx2cscope.utils import get_elf_file_path, get_host_address

x2cscope = X2CScope(host=get_host_address(), interface=InterfaceType.TCP_IP, elf_file=get_elf_file_path())

counter = x2cscope.get_variable("my_counter")
rx_len = x2cscope.get_variable("tcp_rx_count")
rx_full = x2cscope.get_variable("tcp_rx_full")

x2cscope.add_scope_channel(counter)
x2cscope.set_sample_time(1)

x2cscope.request_scope_data()

while True:
    start = time.perf_counter()
    ready_status =  x2cscope.is_scope_data_ready()
    end = time.perf_counter()
    elapsed = end - start  # in seconds
    print(f"Time taken to check: {elapsed:.6f} seconds")
    if ready_status:
        start = time.perf_counter()
        data = x2cscope.get_scope_channel_data()
        end = time.perf_counter()
        elapsed = end - start  # in seconds
        print(f"Time taken to get data: {elapsed:.6f} seconds")
        print(data)
        print("Biggest RX:", rx_len.get_value(), " rx full?", rx_full.get_value())
        x2cscope.request_scope_data()
    time.sleep(0.1)