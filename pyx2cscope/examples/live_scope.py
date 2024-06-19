import csv
import logging
import time

import matplotlib.pyplot as plt

from pyx2cscope.xc2scope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2\ZSMT_dsPIC33CK_MCLV_48_300.X\dist\default\production\ZSMT_dsPIC33CK_MCLV_48_300.X.production.elf"
x2cScope = X2CScope(port="COM14", elf_file=elf_file)

# Define variables
variables = [
    "motor.idq.q",
    "motor.vabc.a",
    "motor.vabc.b",
    "motor.vabc.c",
    "motor.apiData.velocityMeasured",
]

for var in variables:
    x2cScope.add_scope_channel(x2cScope.get_variable(var))

x2cScope.set_sample_time(1)

# Create the plot
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()

# Main loop
sample_count = 0
max_sample = 100  # Increase the number of samples if needed

x2cScope.request_scope_data()

while sample_count < max_sample:
    try:
        if x2cScope.is_scope_data_ready():
            sample_count += 1
            logging.info("Scope data is ready.")

            data_storage = {}
            for channel, data in x2cScope.get_scope_channel_data(valid_data=False).items():
                data_storage[channel] = data

            ax.clear()
            for channel, data in data_storage.items():
                # Assuming data is sampled at 1 kHz, adjust as needed
                time_values = [i * 0.001 for i in range(len(data))]  # milliseconds
                # time_values = [i * 0.000001 for i in range(len(data))]  # microseconds
                ax.plot(time_values, data, label=f"Channel {channel}")

            ax.set_xlabel("Time (ms)")  # Change axis label accordingly
            ax.set_ylabel("Value")
            ax.set_title("Live Plot of Byte Data")
            ax.legend()

            plt.pause(0.001)  # Add a short pause to update the plot

            if sample_count >= max_sample:
                break
            x2cScope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")
        break

    time.sleep(0.1)

plt.ioff()  # Turn off interactive mode after the loop
plt.show()

logging.info("Data collection complete.")

# Data Storage
csv_file_path = "scope_data.csv"
max_length = max(len(data) for data in data_storage.values())

with open(csv_file_path, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=data_storage.keys())
    writer.writeheader()
    for i in range(max_length):
        row = {
            channel: (data_storage[channel][i] if i < len(data_storage[channel]) else None) for channel in data_storage
        }
        writer.writerow(row)

logging.info(f"Data saved in {csv_file_path}")
