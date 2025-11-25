"""This example can be used to try the scope functionality of pyX2Cscope and save the data acquisition in CSV file."""

import csv
import logging
import time

import matplotlib.pyplot as plt

from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
elf_file = get_elf_file_path()
x2c_scope = X2CScope(port=get_com_port(), elf_file=elf_file)

# Define variables
variables = [
    "motor.idq.q",
    "motor.vabc.a",
    "motor.vabc.b",
    "motor.vabc.c",
    "motor.apiData.velocityMeasured",
]

for var in variables:
    x2c_scope.add_scope_channel(x2c_scope.get_variable(var))

x2c_scope.set_sample_time(1)

# Create the plot
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()

# Main loop
nr_of_samples = 10  # Increase the number of samples if needed
data_storage = {}

# request scope to start sampling data
x2c_scope.request_scope_data()

while nr_of_samples > 0:
    # check if scope data is already available
    if x2c_scope.is_scope_data_ready():
        logging.info("Scope data is ready.")

        for channel, data in x2c_scope.get_scope_channel_data().items():
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

        nr_of_samples -= 1
        x2c_scope.request_scope_data()

    # wait for 100 ms before calling is_scope_data_ready() again
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
            channel: (
                data_storage[channel][i] if i < len(data_storage[channel]) else None
            )
            for channel in data_storage
        }
        writer.writerow(row)

logging.info(f"Data saved in {csv_file_path}")
