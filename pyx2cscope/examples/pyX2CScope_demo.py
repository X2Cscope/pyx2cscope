import csv
import logging
import time

import matplotlib.pyplot as plt
from xc2scope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# Set up X2C Scope
elf_file = "C:\\_DESKTOP\\_Projects\\Motorbench_Projects\\ACT57BLF02_MCLV2.X\\dist\\default\\production\\ACT57BLF02_MCLV2.X.production.elf"
x2cScope = X2CScope(port="COM9", elf_file=elf_file)

# Set up scope configuration
variable1 = x2cScope.get_variable("motor.idq.q")
# variable2 = x2cScope.get_variable("motor.estimator.qei.position.electrical")
variable3 = x2cScope.get_variable("motor.vabc.a")
variable4 = x2cScope.get_variable("motor.vabc.b")
variable5 = x2cScope.get_variable("motor.vabc.c")
variable6 = x2cScope.get_variable("motor.apiData.velocityMeasured")

x2cScope.add_scope_channel(variable1)
# x2cScope.add_scope_channel(variable2)
x2cScope.add_scope_channel(variable3)
x2cScope.add_scope_channel(variable4)
x2cScope.add_scope_channel(variable5)
x2cScope.add_scope_channel(variable6)

x2cScope.set_scope_trigger(
    variable3,
    trigger_level=500,
    trigger_mode=1,
    trigger_delay=50,
    trigger_edge=1,
)

x2cScope.request_scope_data()

# Initialize data storage
data_storage = {}

# Save and Load Parameters
for i in range(10):
    try:
        if x2cScope.is_scope_data_ready():
            print("Scope finished")
            print("look at:", x2cScope.get_trigger_position())
            print("delayed trigger", x2cScope.get_delay_trigger_position())

            # Read array chunks and store data
            for channel, data in x2cScope.get_scope_channel_data(
                valid_data=True
            ).items():
                if channel not in data_storage:
                    data_storage[channel] = []
                data_storage[channel].extend(data)

            # Request new scope data
            x2cScope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")

    time.sleep(0.1)

# Plot all the data at once
plt.clf()
for channel, data in data_storage.items():
    plt.plot(data, label=f"Channel {channel}")
plt.xlabel("Data Index")
plt.ylabel("Value")
plt.title("Plot of Byte Data")
plt.legend()
plt.show()

# Save data in CSV file
csv_file_path = "scope_data.csv"
max_length = max(len(data) for data in data_storage.values())
with open(csv_file_path, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=data_storage.keys())
    writer.writeheader()
    for i in range(max_length):
        row = {
            channel: data_storage[channel][i]
            if i < len(data_storage[channel])
            else None
            for channel in data_storage
        }
        writer.writerow(row)

print(f"Data saved in {csv_file_path}")
