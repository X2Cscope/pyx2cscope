"""
Example to change LED by changing the bit value on dspic33ck256mp508 Microchip Using SFR(Special function Register)
"""
import logging
import time

logging.basicConfig(
    level=0,
    filename="BlinkySFR.log",
)

from pyx2cscope.xc2scope import X2CScope

serial_port = "COM15"  # select COM port
baud_rate = 115200
elf_file = r"C:\_DESKTOP\MC FG F2F Vienna\pyx2cscope_dspic33ck_48-300W.X\dist\default\production\pyx2cscope_dspic33ck_48-300W.X.production.elf"

x2cscope = X2CScope(port=serial_port, baud_rate=baud_rate, elf_file=elf_file)
# Constants for LED bit positions
LED1_BIT = 12  # LATE12
LED2_BIT = 13  # LATE13


def set_led_state(value, bit_position, state):
    """Set or clear the specified bit in the value based on the state."""
    if state:
        value |= 1 << bit_position  # Set the bit to 1 OR operator
    else:
        value &= ~(1 << bit_position)  # Clear the bit to 0 AND operator
    return value


def sethigh(value, variable):
    """Set LED1 to high (bit to one) and return the resulting value."""
    return set_led_state(value, variable, True)


def setlow(value, variable):
    """Set LED1 to low (bit to zero) and return the resulting value."""
    return set_led_state(value, variable, False)


def example():
    try:
        # Initialize serial communication and other setup code...

        SFR_LED = x2cscope.get_variable_raw(
            3702, "int", "sfr"
        )  # LATE address from data sheet 3702

        # Get the initial LED state from SFR_LED or any other source
        initial_led_state = SFR_LED.get_value()
        logging.debug("initial value: %s", initial_led_state)
        while 1:
            #########################
            # SET LED1 and LED2 High
            ##########################
            led1_high_value = sethigh(initial_led_state, LED1_BIT)
            SFR_LED.set_value(led1_high_value)

            initial_led_state = SFR_LED.get_value()
            led2_high_value = sethigh(initial_led_state, LED2_BIT)
            SFR_LED.set_value(led2_high_value)

            #########################
            # SET LED1 and LED2 LOW
            ##########################
            time.sleep(1)
            initial_led_state = SFR_LED.get_value()
            led1_low_value = setlow(initial_led_state, LED1_BIT)
            SFR_LED.set_value(led1_low_value)

            initial_led_state = SFR_LED.get_value()
            led2_low_value = setlow(initial_led_state, LED2_BIT)
            SFR_LED.set_value(led2_low_value)
            time.sleep(1)

    except Exception as e:
        # Handle any other exceptions
        logging.error("Error occurred: {}".format(e))


if __name__ == "__main__":
    # Configure logging

    example()
