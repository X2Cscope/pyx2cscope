"""This module contains the pyx2cscope package.

Version: 0.4.2
"""

import logging

__version__ = "0.4.2"


def set_logger(
    level: int = logging.ERROR,
    filename: str = __name__,
    console: bool = False,
    mode: str = "a",
):
    """Call the logging basicConfig.

    call set_logger on every file that could be run as standalone. a filename.log file will be created on the local
    folder where the program is running. this function calls BasicConfig and BasicConfig only executes when called
    by the first time. multiple calls of basicConfig have no effect.

    Args:
         level (int): the log level logging.(WARNING, DEBUG, INFO, ERROR, CRITICAL, etc.)
         filename (str): only the filename without extension, it will receive ".log" extension
         console (bool): True outputs the log messages to file AND console, False (default) only to file.
         mode (bool): 'w' create a new file for every run, 'a' (default) append the messages to the file.
    """
    logging.basicConfig(
        level=level, filename=filename.split(".")[-1] + ".log", filemode=mode
    )

    # add console only if not yet added
    if console:
        if not any(
            [
                type(handler) is logging.StreamHandler
                for handler in logging.root.handlers
            ]
        ):
            ch = logging.StreamHandler()
            ch.setLevel(level)
            logging.root.addHandler(ch)
