"""Example to change LED states by modifying the bit value on a dspic33ck256mp508 using Special Function Register."""

import logging
import time

from utils import get_com_port, get_elf_file_path

from pyx2cscope.xc2scope import X2CScope

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
