"""Main entry point for the X2Cscope application.

This module parses the command-line arguments, initializes the logging configuration,
and launches the Qt or the Web user interface.

It is used by ``python -m pyx2cscope``, by the ``pyx2cscope`` console script
(``pyx2cscope.__main__:main``) and by the standalone executable.
"""

import os
import sys

# When running as a PyInstaller executable, add a 'libs' folder (next to the
# executable) to sys.path so scripts can import packages installed there.
# Append rather than insert so bundled packages always take priority over libs/,
# preventing version conflicts (e.g. a newer NumPy in libs/ shadowing the bundled one).
if getattr(sys, "frozen", False):
    import site
    _libs_dir = os.path.join(os.path.dirname(sys.executable), "libs")
    os.makedirs(_libs_dir, exist_ok=True)
    # addsitedir appends to sys.path and processes .pth files.
    site.addsitedir(_libs_dir)

import logging

logging.basicConfig(level=logging.ERROR)

import argparse

import pyx2cscope
from pyx2cscope import gui, utils

_EPILOG = """\
examples:
  pyX2Cscope -e my_elf.elf -p AUTO           Qt GUI, connect via auto-detected serial port
  pyX2Cscope -e my_elf.elf -p COM3 -w        Web GUI, connect via COM3
  pyX2Cscope -w --host 0.0.0.0 -wp 8080      Web GUI reachable from other devices
  pyX2Cscope --install scipy pandas          install packages for scripts (executable only)

For documentation visit https://x2cscope.github.io/pyx2cscope/."""


def _early_install(argv: list) -> bool:
    """Handle --install before argparse so it never reaches _args_check.

    Args:
        argv: The command-line arguments without the program name.

    Returns:
        bool: True if --install was given and handled, False otherwise.
    """
    if "--install" not in argv:
        return False

    idx = argv.index("--install")
    packages = [p for p in argv[idx + 1:] if p != "--with-deps"]
    if not packages:
        print("--install requires at least one package name.")
        return True

    if not getattr(sys, "frozen", False):
        print("--install is intended for the standalone executable.")
        print(f"Use:  pip install {' '.join(packages)}")
        return True

    libs_dir = os.path.join(os.path.dirname(sys.executable), "libs")
    os.makedirs(libs_dir, exist_ok=True)
    print(f"Installing into: {libs_dir}")

    python = _find_matching_python()
    if python is None:
        ver = sys.version_info
        print(f"ERROR: Could not find Python {ver.major}.{ver.minor} on this system.")
        print("Install it from https://www.python.org/downloads/ then retry.")
        return True

    import subprocess
    print(f"Using Python: {python}")
    # --no-deps: skip pulling in packages already bundled in the exe (e.g. numpy).
    # Users can override with: pyX2Cscope --install scipy --with-deps
    cmd = [python, "-m", "pip", "install", "--target", libs_dir]
    if "--with-deps" not in argv:
        cmd.append("--no-deps")
    cmd += packages
    subprocess.run(cmd, check=False)
    return True


def _find_matching_python() -> str | None:
    """Find a system Python executable whose version matches the frozen bundle."""
    import glob
    import subprocess

    major, minor = sys.version_info.major, sys.version_info.minor
    tag = f"{major}.{minor}"

    # Candidates in order of preference.
    candidates = [
        # Versioned names on PATH (most reliable cross-platform).
        f"python{tag}",
        f"python{major}",
        "python",
        "python3",
        # Common Windows install locations.
        *glob.glob(
            f"C:/Users/*/AppData/Local/Programs/Python/Python{major}{minor}/python.exe"
        ),
        *glob.glob(f"C:/Python{major}{minor}/python.exe"),
        *glob.glob(f"C:/Program Files/Python{major}{minor}/python.exe"),
    ]

    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "-c",
                 f"import sys; v=sys.version_info; exit(0 if (v.major,v.minor)==({major},{minor}) else 1)"],
                capture_output=True,
                timeout=5, check=False,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            continue
    return None


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.

    Returns:
        argparse.ArgumentParser: The parser with all supported arguments.
    """
    parser = argparse.ArgumentParser(
        prog="pyX2Cscope",
        description="Microchip python implementation of X2Cscope and LNet protocol.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-l",
        "--log-level",
        default="ERROR",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Configure the logging level, ERROR is the default value.",
    )
    parser.add_argument(
        "-c", "--log-console", action="store_true", help="Output log to the console."
    )
    parser.add_argument(
        "-e",
        "--elf",
        help="Path to elf-file, i.e. -e my_elf.elf. If omitted, the path stored in config.ini is used.",
    )
    parser.add_argument(
        "-p",
        "--port",
        help="The serial port to be used, i.e. COM3 or /dev/ttyUSB0. "
        "Use AUTO to try every available serial port and connect to the first one with an LNet device. "
        "Together with an elf-file, the GUI connects at startup.",
    )

    gui_group = parser.add_mutually_exclusive_group()
    gui_group.add_argument(
        "-q",
        "--qt",
        action="store_true",
        help="Start the Qt user interface (default).",
    )
    gui_group.add_argument(
        "-w",
        "--web",
        action="store_true",
        help="Start the Web user interface.",
    )
    parser.add_argument(
        "-wp",
        "--web-port",
        type=int,
        default="5000",
        help="Configure the Web Server port, 5000 is the default value. Use together with -w.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Configure the Web Server address, localhost is the default value. "
        "Use 0.0.0.0 to accept connections from other devices. Use together with -w.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s " + pyx2cscope.__version__,
    )

    # --install is handled by _early_install before parsing; it is declared here for the help output.
    install_group = parser.add_argument_group("standalone executable")
    install_group.add_argument(
        "--install",
        nargs="+",
        metavar="PACKAGE",
        help="Install Python packages into the libs folder next to the executable, "
        "so scripts can import them. Dependencies are not installed.",
    )
    install_group.add_argument(
        "--with-deps",
        action="store_true",
        help="Use together with --install to also install the dependencies of the packages.",
    )

    return parser


def parse_arguments(argv: list | None = None):
    """Parse the command-line arguments.

    For a complete list of arguments, execute python -m pyx2cscope --help

    Args:
        argv: The arguments to parse without the program name. Defaults to sys.argv[1:].

    Returns:
        tuple: The known arguments (argparse.Namespace) and the list of unknown arguments,
        which are forwarded to the Qt application.
    """
    return build_parser().parse_known_args(argv)


def _args_check(k_args: argparse.Namespace):
    # if elf is not supplied, check if there is a valid config file
    if k_args.elf is None:
        path = utils.get_elf_file_path()
        if path:
            k_args.elf = path


def main(argv: list | None = None):
    """Run pyX2Cscope from the command line.

    Args:
        argv: The arguments without the program name. Defaults to sys.argv[1:].
    """
    argv = sys.argv[1:] if argv is None else argv
    if _early_install(argv):
        return

    known_args, unknown_args = parse_arguments(argv)
    _args_check(known_args)

    logging.root.handlers.clear()
    pyx2cscope.set_logger(level=known_args.log_level, console=known_args.log_console)

    if known_args.web:
        gui.execute_web(**known_args.__dict__)
    else:
        gui.execute_qt(unknown_args, **known_args.__dict__)


if __name__ == "__main__":
    main()
