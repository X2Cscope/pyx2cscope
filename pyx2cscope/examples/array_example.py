"""PyX2CScope array example reference.

This example shows different use cases for single and multidimensional arrays.

We define 3 different arrays:

static uint8_t my_array1D[3] = {3, 2, 1};
static uint8_t my_array2D[2][3] = { {6, 5, 4}, {3, 2, 1} };
static uint8_t my_array3D[2][2][3] = {
    {
        {12, 11, 10}, {9, 8, 7},
    },
    {
        {6, 5, 4}, {3, 2, 1},
    }
};
"""

import logging

from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = get_elf_file_path()
com_port = get_com_port()
x2c_scope = X2CScope(port=com_port, elf_file=elf_file)

my_array_1d = x2c_scope.get_variable("my_array1D")
my_array_2d = x2c_scope.get_variable("my_array2D")
my_array_3d = x2c_scope.get_variable("my_array3D")

print(my_array_1d.get_value())
# [3, 2, 1]
print(my_array_2d.get_value())
# [6, 5, 4, 3, 2, 1]
print(my_array_3d.get_value())
# [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

my_array_2d_10 = x2c_scope.get_variable("my_array2D[1][0]")
my_array_2d_10.set_value(10)
print(my_array_2d.get_value())
# [6, 5, 4, 10, 2, 1]

my_array_2d[4] = 11
print(my_array_2d.get_value())
# [6, 5, 4, 10, 11, 1]

print(my_array_2d[5])
# 1

my_array_3d_102 = x2c_scope.get_variable("my_array3D[1][0][2]")
my_array_3d_102.set_value(10)
print(my_array_3d.get_value())
# [12, 11, 10, 9, 8, 7, 6, 5, 10, 3, 2, 1]


