"""PyX2CScope example reference.

This example get variable data using the scope functionality of X2Cscope and store it
in CSV file as well as to visualise.
"""

import csv
import logging
import time

import matplotlib.pyplot as plt
from utils import get_com_port, get_elf_file_path
from pyx2cscope import set_logger

from pyx2cscope.xc2scope import X2CScope

set_logger(logging.INFO, )# This sets up the logging system, storing logs in a file with the same name as this script but with a .log extension.
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Set up
# The X2C Scope is a tool for real-time data acquisition from a microcontroller.
# Here, we specify the COM port and the path to the ELF file of the microcontroller project.
elf_file = get_elf_file_path()
x2c_scope = X2CScope(port=get_com_port(), elf_file=elf_file)

# Scope Configuration Here, we set up the variables we want to monitor using the X2C Scope. Each variable corresponds
# to a specific data point in the microcontroller.
variable1 = x2c_scope.get_variable("motor.idq.q")
variable2 = x2c_scope.get_variable("motor.vabc.a")
variable3 = x2c_scope.get_variable("motor.vabc.b")
variable4 = x2c_scope.get_variable("motor.vabc.c")
variable5 = x2c_scope.get_variable("motor.apiData.velocityMeasured")

# Adding variables to the scope's monitoring channels
x2c_scope.add_scope_channel(variable1)
x2c_scope.add_scope_channel(variable2)
x2c_scope.add_scope_channel(variable3)
x2c_scope.add_scope_channel(variable4)
x2c_scope.add_scope_channel(variable5)


# Setting up Trigger, any available variable can be selected.
x2c_scope.set_scope_trigger(
    variable3,
    trigger_level=500,
    trigger_mode=1,
    trigger_delay=50,
    trigger_edge=1,
)

# Request and Acquire Scope Data
# This loop requests and receives data from the scope, storing it in a dictionary for later use.
# It continues until a specified number of samples are collected.
data_storage = {}
sample_count = 0
max_sample = 10

while sample_count < max_sample:
    try:
        if x2c_scope.is_scope_data_ready():
            sample_count += 1
            logging.info("Scope data is ready.")

            # Process and store data
            for channel, data in x2c_scope.get_scope_channel_data(
                valid_data=False
            ).items():
                if channel not in data_storage:
                    data_storage[channel] = []
                data_storage[channel].extend(data)

            if sample_count >= max_sample:
                break
            x2c_scope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")
        break

    time.sleep(0.1)

# Data Visualization
# Plots all the collected data for visual analysis.
plt.clf()
for channel, data in data_storage.items():
    plt.plot(data, label=f"Channel {channel}")
plt.xlabel("Data Index")
plt.ylabel("Value")
plt.title("Plot of Byte Data")
plt.legend()
plt.show()

# Data Storage
# This section saves the collected data into a CSV file for further analysis or record-keeping.
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

logging.info(f"Data saved in {csv_file_path}")
