import logging
import sys

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.watchView.minimal_gui import X2Cscope_GUI


# Define a function to set the logging level based on a string argument
def set_logging_level(level_str):
    """
    Sets the logging level based on the provided level string.

    Args:
        level_str (str): A string representing the logging level (e.g., 'DEBUG', 'INFO').

    This function attempts to set the logging level based on the level_str argument.
    If an invalid logging level is provided, it logs an informational message.
    """
    # Try to get the numeric logging level from the string
    numeric_level = getattr(logging, level_str.upper(), None)

    # Check if the logging level is valid and set it, else log an informational message
    if numeric_level is None:
        logging.info(f"Invalid logging level: {level_str}")
    else:
        logging.root.setLevel(numeric_level)
        logging.info(f"Logging level set to {numeric_level}")

        # Log messages of all levels to test the logging configuration
        logging.debug("Debug message")
        logging.info("Info message")
        logging.warning("Warning message")
        logging.error("Error message")


# Check if a command-line argument was provided for the logging level
if len(sys.argv) > 1:
    log_level_arg = sys.argv[1]
    set_logging_level(log_level_arg)

# Initialize a PyQt5 application
app = QApplication(sys.argv)

# Create an instance of the X2Cscope_GUI
ex = X2Cscope_GUI()

# Display the GUI
ex.show()

# Start the PyQt5 application event loop
app.exec_()
