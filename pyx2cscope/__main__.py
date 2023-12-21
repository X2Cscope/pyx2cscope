import logging
import sys

from gui.watchView.minimal_gui import X2Cscope_GUI
from PyQt5.QtWidgets import QApplication


# Define a function to set the logging level based on a string argument
def set_logging_level(level_str):
    numeric_level = getattr(logging, level_str.upper(), None)
    if numeric_level is None:
        logging.info(f"Invalid logging level: {level_str}")
    else:
        logging.root.setLevel(numeric_level)
        logging.info(f"Logging level set to {numeric_level}")
        logging.debug("Debug message")
        logging.info("Info message")
        logging.warning("Warning message")
        logging.error("Error message")


if len(sys.argv) > 1:
    log_level_arg = sys.argv[1]

set_logging_level(log_level_arg)
app = QApplication(sys.argv)
ex = X2Cscope_GUI()
ex.show()
app.exec_()
