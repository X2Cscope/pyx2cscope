import logging

import matplotlib.pyplot as plt
from xc2scope import X2CScope
from utils import get_com_port, get_elf_file_path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = get_elf_file_path()
com_port = get_com_port()
x2cScope = X2CScope(port=com_port, elf_file=elf_file)

variable = x2cScope.get_variable("ScopeArray")
variable1 = x2cScope.get_variable("motor.estimator.zsmt.iqHistory")
variable2 = x2cScope.get_variable("motor.estimator.zsmt.idHistory")
variable3 = x2cScope.get_variable("personal")
value = variable3.get_value()
print(value)
print(value[50])
plt.plot(value)
plt.show()
