"""PyX2CScope enumerator example reference.

This example get a enum variable, get its enum values and set a different value either as a number or as a enum.

following enum is defined as a static variable:

typedef enum {
    A,
    B,
    C,
    D
} LETTERS;

static LETTERS letter = A;
"""



from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# X2C Scope Set up
# The X2C Scope is a tool for real-time data acquisition from a microcontroller.
# Here, we specify the COM port and the path to the ELF file of the microcontroller project.
elf_file = get_elf_file_path()
x2c_scope = X2CScope(port=get_com_port(), elf_file=elf_file)

# Scope Configuration Here, we set up the variables we want to monitor using the X2C Scope. Each variable corresponds
# to a specific data point in the microcontroller.
letter = x2c_scope.get_variable("letter")

# we can check is this variable is an enum
# True
print(letter.is_enum())

# as this variable is an enum, we can get the integer value of the enum
# {'A': 0, 'B': 1, 'C': 2, 'D': 3}
print(letter.get_enum_list())

# we can retrieve its value
# 0
print(letter.get_value())

# we can set the integer value of the enum as by other variable types
letter.set_value(3)
# output is 3
print(letter.get_value())

# we can define a dictionary with the enum values
LETTERS = letter.get_enum_list()
# and use the string values in this manner to set integer values
letter.set_value(LETTERS["B"])
# output is 1
print(letter.get_value())

# or we can call the specific set_enum_value method
letter.set_enum_value("C")
# output is 2
print(letter.get_value())

# we can get the string representation of the enum variable
print(letter.get_enum_value())
# output is 'C'




