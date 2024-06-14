import logging
import sys
import argparse

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.watchView.minimal_gui import X2Cscope_GUI
from pyx2cscope.gui.web import app
import pyx2cscope


# Define a function to set the logging level based on a string argument
def set_logging_level(args):
    """
    Sets the logging level based on the provided argument 'level'.

    Args:
        the parsed arguments. (ArgumentParser): args contain property level (e.g., 'DEBUG', 'INFO').

    """
    levels={
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    logger = logging.getLogger(__name__)
    logger.setLevel(levels[args.log_level])
    logging.info(f"Logging level set to {args.log_level}")

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="pyX2Cscope",
        description="Microchip python implementation of X2Cscope and LNet protocol.",
        epilog="For documentation visit https://x2cscope.github.io/pyx2cscope/.")

    parser.add_argument("-l", "--log-level", default="INFO", type=str,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Configure the logging level, INFO is the default value.")
    parser.add_argument("-q", "--qt", action="store_false",
                        help="Start the Qt user interface, pyx2cscope.gui.watch_view.minimal_gui.")
    parser.add_argument("-w", "--web", action="store_true",
                        help="Start the Web user interface, pyx2cscope.gui.web.app.")
    parser.add_argument("-p", "--port", type=int, default="5000",
                        help="Configure the Web Server port. Use together with -w")
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s ' + pyx2cscope.__version__)

    return parser.parse_args()

def execute_qt(args):
    # Initialize a PyQt5 application
    app = QApplication(sys.argv)
    # Create an instance of the X2Cscope_GUI
    ex = X2Cscope_GUI()
    # Display the GUI
    ex.show()
    # Start the PyQt5 application event loop
    app.exec_()

def execute_web(args):
    app.main(host="0.0.0.0", port=args.port)

args = parse_arguments()

set_logging_level(args)

if args.qt and not args.web:
    execute_qt(args)

if args.web:
    execute_web(args)


