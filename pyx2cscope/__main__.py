import sys

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.minimal_gui import X2Cscope_GUI

import logging
# Define a function to set the logging level based on a string argument
def set_logging_level(level_str):
    numeric_level = getattr(logging, level_str.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level_str}")
    print(numeric_level)
    logging.basicConfig(level=numeric_level)


if len(sys.argv) > 1:
    log_level_arg = sys.argv[1]
    set_logging_level(log_level_arg)

app = QApplication(sys.argv)
ex = X2Cscope_GUI()
ex.show()
app.exec_()
