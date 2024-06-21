"""This module contains the pyx2cscope package.

Version: 0.2.0
"""
import logging

__version__ = "0.2.0"

def set_logger(level: int = logging.ERROR, filename: str = "logger"):
    """Call the logging basicConfig.

    BasicConfig only work when called by the first time. Multiple calls
    of basicConfig has no effect. Call set_logger on every file that could
    be run as standalone. A filename.log file will be created on the local
    folder where the program is running.

    Args:
         level (int): the log level logging.(WARNING, DEBUG, INFO, ERROR, CRITICAL, etc.)
         filename (str): only the filename without extension, it will receive ".log" extension
    """
    logging.basicConfig(
        level=level,
        filename=filename + ".log",
    )
