"""Main entry point for the X2Cscope application.

This module initializes the logging configuration based on a command-line argument,
sets up the PyQt5 application, and launches the X2Cscope GUI.
"""
import logging

logging.basicConfig(level=logging.ERROR)

import argparse
import sys

from PyQt5.QtWidgets import QApplication

import pyx2cscope
from pyx2cscope.gui.watchView.minimal_gui import X2cscopeGui
from pyx2cscope.gui.web import app


def parse_arguments():
    """Forward the received arguments to ArgParse and parse them.

    possible arguments are:
      | "-l", Configure the logging level, INFO is the default value
      | "-v", action='version'
      | "-w", Start the Web user interface, pyx2cscope.gui.web.app.
      |
      | For a complete list of arguments, execute python -m pyx2cscope --help
    """
    parser = argparse.ArgumentParser(
        prog="pyX2Cscope",
        description="Microchip python implementation of X2Cscope and LNet protocol.",
        epilog="For documentation visit https://x2cscope.github.io/pyx2cscope/.")

    parser.add_argument("-l", "--log-level", default="ERROR", type=str,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Configure the logging level, INFO is the default value.")
    parser.add_argument("-c", "--log-console", action="store_true",
                        help="Output log to the console.")
    parser.add_argument("-q", "--qt", action="store_false",
                        help="Start the Qt user interface, pyx2cscope.gui.watch_view.minimal_gui.")
    parser.add_argument("-w", "--web", action="store_true",
                        help="Start the Web user interface, pyx2cscope.gui.web.app.")
    parser.add_argument("-p", "--port", type=int, default="5000",
                        help="Configure the Web Server port. Use together with -w")
    parser.add_argument("--host", type=str, default="localhost",
                        help="Configure the Web Server address. Use together with -w")
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s ' + pyx2cscope.__version__)

    return parser.parse_known_args()

def execute_qt(args):
    """Execute the GUI Qt implementation.

    Args:
        args: non-keyed arguments for Qt App.
    :return:
    """
    # QApplication expects the first argument to be the program name.
    qt_args = sys.argv[:1] + args
    # Initialize a PyQt5 application
    app = QApplication(qt_args)
    # Create an instance of the X2Cscope_GUI
    ex = X2cscopeGui()
    # Display the GUI
    ex.show()
    # Start the PyQt5 application event loop
    app.exec_()

def execute_web(*args, **kwargs):
    """Start the web server.

    Args:
        *args: non-keyed arguments
        **kwargs: keyed arguments related to the web server. See parse_arguments function documentations.
    """
    app.main(*args, **kwargs)

known_args, unknown_args = parse_arguments()

logging.root.handlers.clear()
pyx2cscope.set_logger(level=known_args.log_level, console=known_args.log_console)

if known_args.qt and not known_args.web:
    execute_qt(unknown_args)

if known_args.web:
    execute_web(**known_args.__dict__)


