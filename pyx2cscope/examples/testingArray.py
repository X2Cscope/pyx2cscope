import logging

import matplotlib.pyplot as plt
from xc2scope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\ZSMT_dsPIC33CK_MCLV_48_300.X\dist\default\production\ZSMT_dsPIC33CK_MCLV_48_300.X.production.elf"
x2cScope = X2CScope(port="COM14", elf_file=elf_file)

variable = x2cScope.get_variable("ScopeArray")
variable1 = x2cScope.get_variable("motor.estimator.zsmt.iqHistory")
variable2 = x2cScope.get_variable("motor.estimator.zsmt.idHistory")
variable3 = x2cScope.get_variable("personal")
value = variable3.get_value()
print(value)
print(value[50])
plt.plot(value)
plt.show()
