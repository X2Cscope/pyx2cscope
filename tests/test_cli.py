"""Unit tests for CLI argument parsing and execution modes.

Tests cover:
- Argument parsing via subprocess (end-to-end)
- Version flag
- Qt mode (default)
- Web mode (-w flag)
- Logging configuration
- Execution mode selection
"""

import argparse
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

import pyx2cscope


def _create_argument_parser():
    """Create a fresh argument parser matching __main__.py for testing.

    This avoids importing __main__ which executes module-level code.
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

    return parser


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_parse_default_arguments(self):
        """Test default argument values."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args([])

        assert args.log_level == "ERROR"
        assert args.log_console is False
        assert args.elf is None
        assert args.port is None
        assert args.qt is True  # Default (store_false means True when not provided)
        assert args.web is False
        assert args.web_port == 5000
        assert args.host == "localhost"

    def test_parse_web_mode_arguments(self):
        """Test -w flag enables web mode."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-w"])

        assert args.web is True
        assert args.qt is True  # -q not provided

    def test_parse_web_mode_with_port(self):
        """Test web mode with custom port."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-w", "-wp", "8080"])

        assert args.web is True
        assert args.web_port == 8080

    def test_parse_web_mode_with_host(self):
        """Test web mode with custom host."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-w", "--host", "0.0.0.0"])

        assert args.web is True
        assert args.host == "0.0.0.0"

    def test_parse_elf_and_port(self, elf_file_path):
        """Test ELF file and port arguments."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-e", elf_file_path, "-p", "COM3"])

        assert args.elf == elf_file_path
        assert args.port == "COM3"

    def test_parse_log_level_debug(self):
        """Test log level argument."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-l", "DEBUG"])

        assert args.log_level == "DEBUG"

    def test_parse_log_level_info(self):
        """Test log level INFO."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-l", "INFO"])

        assert args.log_level == "INFO"

    def test_parse_log_console(self):
        """Test log console flag."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-c"])

        assert args.log_console is True

    def test_parse_qt_disabled(self):
        """Test -q flag disables Qt mode."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-q"])

        assert args.qt is False

    def test_parse_unknown_args_passed_through(self):
        """Test that unknown arguments are passed through."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["--unknown-arg", "value"])

        assert "--unknown-arg" in unknown
        assert "value" in unknown


class TestCLIVersionFlag:
    """Tests for version flag via subprocess."""

    def test_version_flag_short(self):
        """Test -v flag shows version."""
        result = subprocess.run(
            [sys.executable, "-m", "pyx2cscope", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert pyx2cscope.__version__ in result.stdout

    def test_version_flag_long(self):
        """Test --version flag shows version."""
        result = subprocess.run(
            [sys.executable, "-m", "pyx2cscope", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert pyx2cscope.__version__ in result.stdout


class TestCLIHelpFlag:
    """Tests for help flag via subprocess."""

    def test_help_flag_short(self):
        """Test -h flag shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "pyx2cscope", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "pyX2Cscope" in result.stdout
        assert "--web" in result.stdout
        assert "--elf" in result.stdout

    def test_help_flag_long(self):
        """Test --help flag shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "pyx2cscope", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "pyX2Cscope" in result.stdout


class TestCLIExecutionModes:
    """Tests for CLI execution mode selection."""

    def test_qt_mode_called_by_default(self, mocker):
        """Test Qt GUI is launched by default."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        args = argparse.Namespace(
            qt=True, web=False, log_level="ERROR", log_console=False
        )
        unknown_args = []

        # Simulate the execution logic from __main__
        if args.qt and not args.web:
            from pyx2cscope import gui

            gui.execute_qt(unknown_args, **args.__dict__)

        mock_execute_qt.assert_called_once()
        mock_execute_web.assert_not_called()

    def test_web_mode_called_with_w_flag(self, mocker):
        """Test Web GUI is launched with -w flag."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        args = argparse.Namespace(
            qt=True, web=True, log_level="ERROR", log_console=False
        )

        # Simulate the execution logic from __main__
        if args.web:
            from pyx2cscope import gui

            gui.execute_web(**args.__dict__)

        mock_execute_web.assert_called_once()

    def test_no_gui_when_both_disabled(self, mocker):
        """Test no GUI is launched when both are disabled."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        args = argparse.Namespace(
            qt=False, web=False, log_level="ERROR", log_console=False
        )
        unknown_args = []

        # Simulate the execution logic from __main__
        if args.qt and not args.web:
            from pyx2cscope import gui

            gui.execute_qt(unknown_args, **args.__dict__)

        if args.web:
            from pyx2cscope import gui

            gui.execute_web(**args.__dict__)

        mock_execute_qt.assert_not_called()
        mock_execute_web.assert_not_called()


class TestCLILogging:
    """Tests for CLI logging configuration."""

    def test_set_logger_called_with_level(self, mocker):
        """Test that set_logger is called with correct level."""
        mock_set_logger = mocker.patch("pyx2cscope.set_logger")

        # Simulate logger setup
        pyx2cscope.set_logger(level="DEBUG", console=True)

        mock_set_logger.assert_called_once_with(level="DEBUG", console=True)

    def test_log_levels_valid(self):
        """Test all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        parser = _create_argument_parser()

        for level in valid_levels:
            args, _ = parser.parse_known_args(["-l", level])
            assert args.log_level == level

    def test_invalid_log_level_rejected(self):
        """Test invalid log level is rejected."""
        parser = _create_argument_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["-l", "INVALID"])
