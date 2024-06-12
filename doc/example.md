# Examples

## ExampleMCAF
````python

"""exampleMCAF.py.

this example is the very basic example to retrieve the value of a certain variable for motorBench generated code.
"""

import logging

from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

# Configure logging settings to capture all levels of log messages and write them to a file
logging.basicConfig(
    level=0,  # Log all levels of messages
    filename="ExampleMCAF.log",  # Log file name
)

# Configuration for serial port communication
serial_port = get_com_port()  # Get the COM port to use from the utility function
baud_rate = 115200  # Set baud rate for serial communication

# Specify the path to the ELF file
elf_file = get_elf_file_path()  # Get the path to the ELF file from the utility function

# Initialize the X2CScope with the specified serial port and baud rate
# The default baud rate is 115200
x2c_scope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)

# Retrieve specific variables from the MCU
speed_reference = x2c_scope.get_variable(
    "motor.apiData.velocityReference"
)  # Get the speed reference variable
speed_measured = x2c_scope.get_variable(
    "motor.apiData.velocityMeasured"
)  # Get the measured speed variable

# Attempt to read the value of the 'speedReference' variable and log the result
try:
    speed_reference_value = (
        speed_reference.get_value()
    )  # Read the value of the speed reference variable
    logging.debug(
        f"Speed Reference Value: {speed_reference_value}"
    )  # Log the retrieved value
except Exception as e:
    logging.debug(
        f"Error reading speed reference value: {e}"
    )  # Log any exceptions that occur

````
## SFR_Example
 
````python

"""Example to change LED states by modifying the bit value on a dspic33ck256mp508 using Special Function Register."""

import logging
import time

from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

# Configure logging settings
logging.basicConfig(
    level=0,
    filename="BlinkySFR.log",
)

# Configuration for serial port communication
serial_port = get_com_port()  # Select COM port
baud_rate = 115200
elf_file = get_elf_file_path()

# Initialize the X2CScope with the specified serial port and baud rate
x2cscope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)

# Constants for LED bit positions in the Special Function Register
LED1_BIT = 12  # LATE12
LED2_BIT = 13  # LATE13


def set_led_state(value, bit_position, state):
    """Set or clear the specified bit in the value based on the state.

    Args:
        value (int): The current value of the register.
        bit_position (int): The bit position to modify.
        state (bool): True to set the bit, False to clear the bit.

    Returns:
        int: The modified register value.
    """
    if state:
        value |= 1 << bit_position  # Set the bit to 1 (OR operation)
    else:
        value &= ~(1 << bit_position)  # Clear the bit to 0 (AND operation)
    return value


def sethigh(value, bit_position):
    """Set a specific bit to high (1).

    Args:
        value (int): The current value of the register.
        bit_position (int): The bit position to set high.

    Returns:
        int: The modified register value with the bit set to high.
    """
    return set_led_state(value, bit_position, True)


def setlow(value, bit_position):
    """Set a specific bit to low (0).

    Args:
        value (int): The current value of the register.
        bit_position (int): The bit position to set low.

    Returns:
        int: The modified register value with the bit set to low.
    """
    return set_led_state(value, bit_position, False)


def example():
    """Main function to demonstrate LED state changes using SFR."""
    try:
        # Initialize the variable for the Special Function Register (SFR) controlling the LEDs
        sfr_led = x2cscope.get_variable_raw(
            3702, "int", "sfr"
        )  # LATE address from data sheet 3702

        # Get the initial LED state from the SFR
        initial_led_state = sfr_led.get_value()
        logging.debug("initial value: %s", initial_led_state)

        while True:
            #########################
            # SET LED1 and LED2 High
            ##########################
            led1_high_value = sethigh(initial_led_state, LED1_BIT)
            sfr_led.set_value(led1_high_value)

            initial_led_state = sfr_led.get_value()
            led2_high_value = sethigh(initial_led_state, LED2_BIT)
            sfr_led.set_value(led2_high_value)

            #########################
            # SET LED1 and LED2 LOW
            ##########################
            time.sleep(1)
            initial_led_state = sfr_led.get_value()
            led1_low_value = setlow(initial_led_state, LED1_BIT)
            sfr_led.set_value(led1_low_value)

            initial_led_state = sfr_led.get_value()
            led2_low_value = setlow(initial_led_state, LED2_BIT)
            sfr_led.set_value(led2_low_value)
            time.sleep(1)

    except Exception as e:
        # Handle any other exceptions
        logging.error("Error occurred: {}".format(e))


if __name__ == "__main__":
    example()

````



## Live Scope and saving data to CSV file.

````python

"""This example can be used to try the scope functionality of pyX2Cscope and save the data acquisition in CSV file."""

import csv
import logging
import time

import matplotlib.pyplot as plt
from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

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
] # upto 8 variables could be selected.

for var in variables:
    x2c_scope.add_scope_channel(x2c_scope.get_variable(var))

x2c_scope.set_sample_time(1)

# Create the plot
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()

# Main loop
sample_count = 0
max_sample = 100  # Increase the number of samples if needed

while sample_count < max_sample:
    try:
        if x2c_scope.is_scope_data_ready():
            sample_count += 1
            logging.info("Scope data is ready.")

            data_storage = {}
            for channel, data in x2c_scope.get_scope_channel_data(
                valid_data=False
            ).items():
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
            x2c_scope.request_scope_data()

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
            channel: (
                data_storage[channel][i] if i < len(data_storage[channel]) else None
            )
            for channel in data_storage
        }
        writer.writerow(row)

logging.info(f"Data saved in {csv_file_path}")
````

for more visit the [pyX2Cscope example directory ](https://github.com/X2Cscope/pyx2cscope/tree/develop/pyx2cscope/examples)



