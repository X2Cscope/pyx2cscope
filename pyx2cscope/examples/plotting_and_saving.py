"""Plotting and saving example for live data from a dspic33ck256mp508 using X2CScope.

here data acquisition is based on different speed, with a desired step.
"""


import logging
import queue
import threading
import time

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import animation
from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    filename="BlinkyTest.log",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Initialize serial communication
serial_port = get_com_port()
baud_rate = 115200
# Specify the path to your ELF file
elf_file = get_elf_file_path()

# Initialize X2CScope with the specified serial port and baud rate
x2cscope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)

# Get the required variables from the ELF file
variable_current = x2cscope.get_variable("I_b")
variable_vm1 = x2cscope.get_variable("V_M1")
start_stop = x2cscope.get_variable("buttonStartStop.debounceCount")
pot = x2cscope.get_variable("PotVal")
CurrentSpeed = x2cscope.get_variable("CurrentSpeed")
start_stop.set_value(10)

# Create thread-safe data queues
speed_queue = queue.Queue()
current_queue = queue.Queue()
pot_queue = queue.Queue()

# Constants
SAMPLE_RANGE = 250  # Number of samples to display on the plot
DATA_COLLECTION_LIMIT = 400  # Limit for data collection iterations

# Create a figure and axes for live plotting
fig, ax = plt.subplots()


def on_close(event):
    """Handle plot window close event to reset start/stop variable."""
    start_stop.set_value(10)


# fig.canvas.mpl_connect('close_event', on_close)


def update_plot(frame):
    """Update the plot with the latest data from the queues.

    Args:
        frame: Current frame number (unused).
    """
    current_value = list(current_queue.queue)
    speed_value = list(speed_queue.queue)
    pot_value = list(pot_queue.queue)

    if len(current_value) > SAMPLE_RANGE:
        current_value = current_value[-SAMPLE_RANGE:]
        speed_value = speed_value[-SAMPLE_RANGE:]
        pot_value = pot_value[-SAMPLE_RANGE:]

    ax.clear()
    ax.plot(current_value, label="Current")
    ax.plot(speed_value, label="Speed")
    ax.plot(pot_value, label="PotVal")
    ax.set_xlim(0, SAMPLE_RANGE)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value")
    ax.set_title("Live Current and Voltage Plot")
    ax.legend(loc="upper right")


# Create the animation
ani = animation.FuncAnimation(fig, update_plot, interval=1)  # Timer interval set to 2ms


def data_collection():
    """Collect data from the MCU and store it in queues for plotting."""
    i = 0
    start_value = 500
    step = 10
    while i < DATA_COLLECTION_LIMIT:
        pot.set_value(start_value)
        pot_queue.put(pot.get_value())
        speed_queue.put(CurrentSpeed.get_value())
        current_queue.put(variable_current.get_value())
        start_value += step
        logging.debug(i)
        i += 1
        time.sleep(0.1)

    pot.set_value(250)
    start_stop.set_value(10)


# Create a thread for data collection
data_collection_thread = threading.Thread(target=data_collection)

# Start the data collection thread
data_collection_thread.start()

# Show the plot
plt.show()

# Wait for the data collection thread to finish
data_collection_thread.join()

# Add a delay to allow all the data to be processed
time.sleep(2)

# Create a dictionary of lists
data_dict = {
    "speed": list(speed_queue.queue),
    "current": list(current_queue.queue),
    "Pot": list(pot_queue.queue),
}

# Create a DataFrame from the dictionary
df = pd.DataFrame(data_dict)

# Save the DataFrame to a CSV file
df.to_csv("data.csv", index=False)
