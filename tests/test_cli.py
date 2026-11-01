"""Unit tests for CLI argument parsing and execution modes.

Tests cover:
- Argument parsing with the parser defined in pyx2cscope.__main__
- Help output, including the serial AUTO port and the --install option
- Version flag (end-to-end via subprocess)
- Qt mode (default and -q) and Web mode (-w)
- main() entry point used by the pyx2cscope console script
- Logging configuration
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import pyx2cscope
from pyx2cscope import __main__ as cli

WEB_PORT_DEFAULT = 5000
WEB_PORT_CUSTOM = 8080
ARGPARSE_ERROR = 2


def _create_argument_parser():
    """Return the argument parser used by pyx2cscope.__main__."""
    return cli.build_parser()


def _run_cli(*args):
    """Run python -m pyx2cscope with the given arguments and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "pyx2cscope", *args],
        capture_output=True,
        text=True,
        timeout=30, check=False,
    )


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
        assert args.qt is False
        assert args.web is False
        assert args.web_port == WEB_PORT_DEFAULT
        assert args.host == "localhost"
        assert args.install is None
        assert args.with_deps is False

    def test_parse_web_mode_arguments(self):
        """Test -w flag enables web mode."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-w"])

        assert args.web is True
        assert args.qt is False

    def test_parse_web_mode_with_port(self):
        """Test web mode with custom port."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-w", "-wp", "8080"])

        assert args.web is True
        assert args.web_port == WEB_PORT_CUSTOM

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

    def test_parse_auto_port(self, elf_file_path):
        """Test AUTO is accepted as port value."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-e", elf_file_path, "-p", "AUTO"])

        assert args.port == "AUTO"

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

    def test_parse_qt_flag(self):
        """Test -q flag selects the Qt GUI."""
        parser = _create_argument_parser()
        args, unknown = parser.parse_known_args(["-q"])

        assert args.qt is True
        assert args.web is False

    def test_qt_and_web_are_mutually_exclusive(self):
        """Test -q and -w cannot be used together."""
        parser = _create_argument_parser()

        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["-q", "-w"])
        assert exc.value.code == ARGPARSE_ERROR

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
        result = _run_cli("-v")

        assert result.returncode == 0
        assert pyx2cscope.__version__ in result.stdout

    def test_version_flag_long(self):
        """Test --version flag shows version."""
        result = _run_cli("--version")

        assert result.returncode == 0
        assert pyx2cscope.__version__ in result.stdout


class TestCLIHelpFlag:
    """Tests for help flag via subprocess."""

    def test_help_flag_short(self):
        """Test -h flag shows help."""
        result = _run_cli("-h")

        assert result.returncode == 0
        assert "pyX2Cscope" in result.stdout
        assert "--web" in result.stdout
        assert "--elf" in result.stdout

    def test_help_flag_long(self):
        """Test --help flag shows help."""
        result = _run_cli("--help")

        assert result.returncode == 0
        assert "pyX2Cscope" in result.stdout

    def test_help_describes_auto_port(self):
        """Test the help text describes the AUTO serial port detection."""
        help_text = _create_argument_parser().format_help()

        assert "AUTO" in help_text

    def test_help_describes_install(self):
        """Test the help text lists --install and --with-deps."""
        help_text = _create_argument_parser().format_help()

        assert "--install" in help_text
        assert "--with-deps" in help_text


class TestCLIInstall:
    """Tests for the --install option."""

    def test_install_outside_executable_prints_pip_hint(self):
        """Test --install outside the standalone executable points to pip and exits."""
        result = _run_cli("--install", "scipy")

        assert result.returncode == 0
        assert "pip install scipy" in result.stdout

    def test_install_without_packages(self):
        """Test --install without package names prints an error message."""
        result = _run_cli("--install")

        assert result.returncode == 0
        assert "requires at least one package" in result.stdout

    def test_install_does_not_start_gui(self, mocker):
        """Test main() returns after handling --install without starting any GUI."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        cli.main(["--install", "scipy"])

        mock_execute_qt.assert_not_called()
        mock_execute_web.assert_not_called()


class TestCLIExecutionModes:
    """Tests for CLI execution mode selection in main()."""

    @pytest.fixture(autouse=True)
    def _no_logger_and_config(self, mocker):
        """Avoid writing log files and reading config.ini during the tests."""
        mocker.patch("pyx2cscope.set_logger")
        mocker.patch("pyx2cscope.utils.get_elf_file_path", return_value="")

    def test_qt_mode_called_by_default(self, mocker):
        """Test Qt GUI is launched by default."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        cli.main([])

        mock_execute_qt.assert_called_once()
        mock_execute_web.assert_not_called()

    def test_qt_mode_called_with_q_flag(self, mocker):
        """Test Qt GUI is launched with -q flag."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        cli.main(["-q"])

        mock_execute_qt.assert_called_once()
        mock_execute_web.assert_not_called()

    def test_web_mode_called_with_w_flag(self, mocker):
        """Test Web GUI is launched with -w flag."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        cli.main(["-w"])

        mock_execute_web.assert_called_once()
        mock_execute_qt.assert_not_called()

    def test_elf_and_port_forwarded_to_gui(self, mocker, elf_file_path):
        """Test -e and -p are forwarded to the GUI."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")

        cli.main(["-e", elf_file_path, "-p", "AUTO"])

        kwargs = mock_execute_qt.call_args.kwargs
        assert kwargs["elf"] == elf_file_path
        assert kwargs["port"] == "AUTO"

    def test_unknown_args_forwarded_to_qt(self, mocker):
        """Test unknown arguments are forwarded to the Qt application."""
        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")

        cli.main(["-style", "fusion"])

        assert mock_execute_qt.call_args.args[0] == ["-style", "fusion"]


class TestCLIEntryPoint:
    """Tests for the pyx2cscope console script entry point."""

    def test_console_script_target_exists(self):
        """Test the [project.scripts] entry point refers to a callable main()."""
        # tomllib is only available from Python 3.11, so read the entry with a regex
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        match = re.search(r'^pyx2cscope\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
        assert match, "pyx2cscope console script not found in pyproject.toml"

        module_name, func_name = match.group(1).split(":")
        assert module_name == "pyx2cscope.__main__"
        assert callable(getattr(cli, func_name))

    def test_import_does_not_start_gui(self, mocker):
        """Test importing pyx2cscope.__main__ does not run the application."""
        import importlib

        mock_execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        mock_execute_web = mocker.patch("pyx2cscope.gui.execute_web")

        importlib.reload(cli)

        mock_execute_qt.assert_not_called()
        mock_execute_web.assert_not_called()


class TestCLILogging:
    """Tests for CLI logging configuration."""

    def test_set_logger_called_with_level(self, mocker):
        """Test that main() configures the logger with the given level."""
        mock_set_logger = mocker.patch("pyx2cscope.set_logger")
        mocker.patch("pyx2cscope.gui.execute_qt")
        mocker.patch("pyx2cscope.utils.get_elf_file_path", return_value="")

        cli.main(["-l", "DEBUG", "-c"])

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
