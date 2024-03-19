from pyx2cscope.xc2scope import X2CScope

# initialize the x2cscope with serial port, by default baud rate is 115200,
x2cScope = X2CScope(port="COM8", baud_rate=115200, elf_file="production.elf")

# Retrieve specific variables.
speedReference = x2cScope.get_variable("motor.apiData.velocityReference")
speedMeasured = x2cScope.get_variable("motor.apiData.velocityMeasured")

# Read the value of the "motor.apiData.velocityMeasured" variable from the target
print(speedMeasured.get_value())
# Write a new value to the "motor.apiData.velocityReference" variable on the target
speedReference.set_value(1000)
