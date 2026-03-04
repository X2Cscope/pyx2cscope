"""Shared pytest fixtures for all tests.

This module provides common fixtures for CLI, Qt GUI, and Web GUI testing.
"""

import os
import sys

import pytest

from tests import data
from tests.utils.serial_stub import SerialStub, fake_serial

# Test data paths
TEST_DATA_DIR = os.path.dirname(data.__file__)
TEST_ELF_FILE = os.path.join(TEST_DATA_DIR, "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf")
TEST_ELF_FILE_32BIT = os.path.join(TEST_DATA_DIR, "qspin_foc_same54.elf")


@pytest.fixture
def elf_file_path():
    """Provide path to test ELF file (16-bit)."""
    return TEST_ELF_FILE


@pytest.fixture
def elf_file_path_32bit():
    """Provide path to test ELF file (32-bit)."""
    return TEST_ELF_FILE_32BIT


@pytest.fixture
def mock_serial_16bit(mocker):
    """Mock serial connection for 16-bit device."""
    fake_serial(mocker, 16)


@pytest.fixture
def mock_serial_32bit(mocker):
    """Mock serial connection for 32-bit device."""
    fake_serial(mocker, 32)


@pytest.fixture
def serial_stub_16bit():
    """Create a SerialStub instance for 16-bit device."""
    return SerialStub(uc_width=16)


@pytest.fixture
def serial_stub_32bit():
    """Create a SerialStub instance for 32-bit device."""
    return SerialStub(uc_width=32)


# ============================================================================
# Flask/Web GUI Fixtures
# ============================================================================

@pytest.fixture
def flask_app():
    """Create Flask test application."""
    from pyx2cscope.gui.web.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def flask_client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def flask_app_context(flask_app):
    """Create Flask application context."""
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def web_scope_instance():
    """Create a fresh WebScope instance for testing."""
    from pyx2cscope.gui.web.scope import WebScope

    return WebScope()


# ============================================================================
# Qt GUI Fixtures (requires pytest-qt)
# ============================================================================

@pytest.fixture
def qt_app(request):
    """Create QApplication instance for Qt testing.

    This fixture handles the QApplication lifecycle and ensures
    only one instance exists during testing.
    """
    # Skip if PyQt5 not available or running headless without display
    pytest.importorskip("PyQt5")

    from PyQt5.QtWidgets import QApplication

    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        # Set offscreen platform for headless testing
        if "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication([])

    yield app

    # Cleanup is handled by pytest-qt or the test itself


@pytest.fixture
def mock_x2cscope(mocker):
    """Create a mock X2CScope instance."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.is_connected.return_value = False
    mock.get_variable_list.return_value = []
    mock.get_device_info.return_value = {
        "processor_id": "test",
        "uc_width": 16,
        "date": "2024-01-01",
        "time": "12:00:00",
        "app_version": "1.0.0",
    }
    return mock


# ============================================================================
# CLI Fixtures
# ============================================================================

@pytest.fixture
def cli_args_default():
    """Default CLI arguments (Qt mode)."""
    return []


@pytest.fixture
def cli_args_web():
    """CLI arguments for web mode."""
    return ["-w"]


@pytest.fixture
def cli_args_web_with_port():
    """CLI arguments for web mode with custom port."""
    return ["-w", "-wp", "8080", "--host", "0.0.0.0"]


@pytest.fixture
def cli_args_with_elf(elf_file_path):
    """CLI arguments with ELF file path."""
    return ["-e", elf_file_path, "-p", "COM1"]


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def headless_env(monkeypatch):
    """Set up headless environment for GUI testing."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    # Disable GUI elements that require display
    monkeypatch.setenv("DISPLAY", "")


@pytest.fixture(autouse=True)
def reset_web_scope():
    """Reset WebScope singleton state between tests."""
    yield
    # Clean up web_scope state after each test
    try:
        from pyx2cscope.gui.web.scope import web_scope

        web_scope.clear_watch_var()
        web_scope.clear_scope_var()
        web_scope.dashboard_vars.clear()
        if web_scope.is_connected():
            web_scope.disconnect()
    except Exception:
        pass  # Ignore if web module not loaded
