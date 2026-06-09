"""Main entry point for the X2Cscope application.

This module initializes the logging configuration based on a command-line argument,
sets up the PyQt5 application, and launches the X2Cscope GUI.
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


def _early_install() -> bool:
    """Handle --install before argparse so it never reaches _args_check."""
    if "--install" not in sys.argv:
        return False

    idx = sys.argv.index("--install")
    packages = [p for p in sys.argv[idx + 1:] if p != "--with-deps"]
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
    if "--with-deps" not in sys.argv:
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
        help="Start the Qt user interface, pyx2cscope.gui.qt.main_window.MainWindow",
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
    # if elf is not supplied, check if there is a valid config file
    if k_args.elf is None:
        path = utils.get_elf_file_path()
        if path:
            k_args.elf = path


if not _early_install():
    known_args, unknown_args = parse_arguments()
    _args_check(known_args)

    logging.root.handlers.clear()
    pyx2cscope.set_logger(level=known_args.log_level, console=known_args.log_console)

    if known_args.qt and not known_args.web:
        gui.execute_qt(unknown_args, **known_args.__dict__)

    if known_args.web:
        gui.execute_web(**known_args.__dict__)
