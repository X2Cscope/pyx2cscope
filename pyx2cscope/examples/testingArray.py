"""This example is for testing array functionality implementation."""
import logging

import matplotlib.pyplot as plt
from utils import get_com_port, get_elf_file_path
from xc2scope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = get_elf_file_path()
com_port = get_com_port()
x2c_scope = X2CScope(port=com_port, elf_file=elf_file)

variable = x2c_scope.get_variable("ScopeArray")
variable1 = x2c_scope.get_variable("motor.estimator.zsmt.iqHistory")
variable2 = x2c_scope.get_variable("motor.estimator.zsmt.idHistory")
variable3 = x2c_scope.get_variable("personal")
value = variable3.get_value()
print(value)
print(value[50])
plt.plot(value)
plt.show()
