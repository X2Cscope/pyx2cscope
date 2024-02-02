import time

from pyx2cscope.xc2scope import X2CScope

elf_file = (
    r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2"
    r"\motorbench_FOC_PLL_dsPIC33CK_MCLV2_FH.X\dist\default\production\motorbench_FOC_PLL_dsPIC33CK_MCLV2.X"
    r".production.elf"
)
x2cScope = X2CScope(port="COM16", elf_file=elf_file)
ser = x2cScope.interface

torque_current = x2cScope.get_variable("motor.idq.q")

while 1:
    start_time = time.time()
    print(torque_current.get_value())
    end_time = time.time()
    print("time to send and receive one request:", end_time - start_time)
