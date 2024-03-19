import logging
import queue
import threading
import time

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    filename="BlinkyTest.log",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from pyx2cscope.xc2scope import X2CScope

# Initialize serial communication
serial_port = "COM8"
baud_rate = 115200
# Specify the path to your ELF file
elf_file = "C:\\_DESKTOP\\_Projects\\AN1160_dsPIC33CK256MP508_MCLV2_MCHV\\bldc_MCLV2.X\\dist\\MCLV2\\production/bldc_MCLV2.X.production.elf"

# Initialize LNet and VariableFactory
x2cscope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)
# Get the required variables from the ELF file
variable_current = x2cscope.get_variable("I_b")
variable_VM1 = x2cscope.get_variable("V_M1")
start_stop = x2cscope.get_variable("buttonStartStop.debounceCount")
pot = x2cscope.get_variable("PotVal")
CurrentSpeed = x2cscope.get_variable("CurrentSpeed")
start_stop.set_value(10)

# Create thread-safe data queues
speed_queue = queue.Queue()
current_queue = queue.Queue()
pot_queue = queue.Queue()

sample_range = 250  # Number of samples to display on the plot

# Create a figure and axes for live plotting
fig, ax = plt.subplots()


def on_close(event):
    # Set value on plot close
    start_stop.set_value(10)


# fig.canvas.mpl_connect('close_event', on_close)

start_value = 500
step = 10


def update_plot(frame):
    current_value = list(current_queue.queue)
    speed_value = list(speed_queue.queue)
    pot_value = list(pot_queue.queue)

    if len(current_value) > sample_range:
        current_value = current_value[-sample_range:]
        speed_value = speed_value[-sample_range:]
        pot_value = pot_value[-sample_range:]

    ax.clear()
    ax.plot(current_value, label="Current")
    ax.plot(speed_value, label="Speed")
    ax.plot(pot_value, label="PotVal")
    ax.set_xlim(0, sample_range)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Value")
    ax.set_title("Live Current and Voltage Plot")
    ax.legend(loc="upper right")


# Create the animation
ani = animation.FuncAnimation(fig, update_plot, interval=1)  # Timer interval set to 2ms


def data_collection():
    i = 0
    start_value = 500
    step = 10
    while i < 400:
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
