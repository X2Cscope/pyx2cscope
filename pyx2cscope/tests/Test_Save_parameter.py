import logging
import time

import matplotlib.pyplot as plt

from xc2scope import X2CScope

logging.basicConfig(
    level=logging.DEBUG,
    filename="Save_parameter_test.py.log",
)

# elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\motorbench_longhurst_mclv2_dsPIC33ck\motorbench_longhurst.X\dist\default\production\motorbench_longhurst.X.production.elf"
elf_file = r"C:\Users\M71906\MPLABXProjects\MotorControl\dsPIC33-LVMC-MB-FOC-Sensorless.X\dist\default\production\dsPIC33-LVMC-MB-FOC-Sensorless.X.production.elf"

x2cScope = X2CScope(port="COM4", elf_file=elf_file)

# Set up scope configuration
variable1 = x2cScope.get_variable("motor.idq.q")
# variable2 = x2cScope.get_variable("motor.estimator.qei.position.electrical")
variable3 = x2cScope.get_variable("motor.vabc.a")
variable4 = x2cScope.get_variable("motor.vabc.b")
variable5 = x2cScope.get_variable("motor.vabc.c")

x2cScope.add_scope_channel(variable1)
# x2cScope.add_scope_channel(variable2)
x2cScope.add_scope_channel(variable3)
x2cScope.add_scope_channel(variable4)
x2cScope.add_scope_channel(variable5)

x2cScope.set_scope_trigger(
    variable3,
    trigger_level=-500,
    trigger_mode=1,
    trigger_delay=50,
    trigger_edge=1,
)

x2cScope.request_scope_data()

# Save and Load Parameters
for i in range(50000):
    try:
        if x2cScope.is_scope_data_ready():
            print("Scope finished")
            print("look at:", x2cScope.get_trigger_position())
            print("delayed trigger", x2cScope.get_delay_trigger_position())

            # Read array chunks
            plt.clf()
            for channel, data in x2cScope.get_scope_channel_data().items():
                plt.plot(data, label=f"Channel {channel}")

            # plt.plot(extracted_data[1])
            plt.xlabel("Data Index")
            plt.ylabel("Value")
            plt.title("Plot of Byte Data")
            plt.legend()
            plt.show()

            # Save the data to scope using your scope_save_parameter function
            x2cScope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")

    time.sleep(0.1)
