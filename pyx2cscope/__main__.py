"""Main entry point for the X2Cscope application.

This module initializes the logging configuration based on a command-line argument,
sets up the PyQt5 application, and launches the X2Cscope GUI.
"""

import logging

logging.basicConfig(level=logging.ERROR)

import argparse

import pyx2cscope
from pyx2cscope import gui, utils


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
        epilog="For documentation visit https://x2cscope.github.io/pyx2cscope/.",
    )

    parser.add_argument(
        "-l",
        "--log-level",
        default="ERROR",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Configure the logging level, INFO is the default value.",
    )
    parser.add_argument(
        "-c", "--log-console", action="store_true", help="Output log to the console."
    )
    parser.add_argument("-e", "--elf", help="Path to elf-file, i.e. -e my_elf.elf.")
    parser.add_argument(
        "-p", "--port", help="The serial COM port to be used. Use together with -e"
    )
    parser.add_argument(
        "-q",
        "--qt",
        action="store_false",
        help="Start the Qt user interface, pyx2cscope.gui.generic_gui.generic_gui.X2Cscope",
    )
    parser.add_argument(
        "-w",
        "--web",
        action="store_true",
        help="Start the Web user interface, pyx2cscope.gui.web.app.",
    )
    parser.add_argument(
        "-wp",
        "--web-port",
        type=int,
        default="5000",
        help="Configure the Web Server port. Use together with -w",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Configure the Web Server address. Use together with -w",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s " + pyx2cscope.__version__,
    )

    return parser.parse_known_args()


def _args_check(k_args: argparse.Namespace):
    # if both elf and port are not supplied, check if there is a valid config file
    if k_args.elf is None and k_args.port is None:
        path = utils.get_elf_file_path()
        com_port = utils.get_com_port()
        if path and com_port:
            k_args.elf = path
            k_args.port = com_port
    # if we supplied and elf but no port
    elif k_args.elf and not k_args.port:
        com_port = utils.get_com_port()
        if com_port:
            k_args.port = com_port
        else:
            raise ValueError("A communication port must be supplied!")
    elif not k_args.elf and k_args.port:
        path = utils.get_elf_file_path()
        if path:
            k_args.elf = path
        else:
            raise ValueError("An elf-file path must be supplied!")


known_args, unknown_args = parse_arguments()
# if arguments logic is correct,
_args_check(known_args)

logging.root.handlers.clear()
pyx2cscope.set_logger(level=known_args.log_level, console=known_args.log_console)

if known_args.qt and not known_args.web:
    gui.execute_qt(unknown_args, **known_args.__dict__)

if known_args.web:
    gui.execute_web(**known_args.__dict__)
