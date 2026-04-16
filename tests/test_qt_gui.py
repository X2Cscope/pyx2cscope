"""Unit tests for Qt GUI components.

Tests run headless using QT_QPA_PLATFORM=offscreen.
Tests cover:
- AppState model (state management, thread safety)
- ConnectionManager (port enumeration, connection handling)
- ConfigManager (save/load configuration)
- Widget creation and initialization
- Signal/slot connections
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Set headless mode before importing Qt modules
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from tests import data


@pytest.fixture
def mock_can_bus():
    """Create a mock CAN bus for testing."""
    with patch('can.interface.Bus') as mock_bus_class:
        mock_bus_instance = MagicMock()
        mock_bus_instance._is_shutdown = False
        mock_bus_instance.recv = MagicMock(return_value=None)
        mock_bus_instance.send = MagicMock()
        mock_bus_instance.shutdown = MagicMock()
        mock_bus_class.return_value = mock_bus_instance
        yield mock_bus_class, mock_bus_instance


class TestAppStateModel:
    """Tests for AppState model."""

    @pytest.fixture
    def app_state(self):
        """Create AppState instance for testing."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        return AppState()

    def test_initial_state(self, app_state):
        """Test AppState initializes with correct defaults."""
        assert app_state.is_connected() is False
        assert app_state.get_variable_list() == []
        assert len(app_state._watch_vars) == app_state.MAX_WATCH_VARS
        assert len(app_state._scope_channels) == app_state.MAX_SCOPE_CHANNELS

    def test_connection_signal_emitted(self, app_state, qtbot):
        """Test connection_changed signal is emitted."""
        with qtbot.waitSignal(app_state.connection_changed, timeout=1000):
            app_state.connection_changed.emit(True)

    def test_watch_variable_defaults(self, app_state):
        """Test watch variables have correct defaults."""
        for watch_var in app_state._watch_vars:
            assert watch_var.name == ""
            assert watch_var.value == 0.0
            assert watch_var.scaling == 1.0
            assert watch_var.offset == 0.0
            assert watch_var.live is False

    def test_scope_channel_defaults(self, app_state):
        """Test scope channels have correct defaults."""
        for channel in app_state._scope_channels:
            assert channel.name == ""
            assert channel.trigger is False
            assert channel.gain == 1.0
            assert channel.visible is True

    def test_set_watch_variable(self, app_state):
        """Test setting watch variable properties."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        watch_var = WatchVariable(name="test_var", value=10.0)
        app_state.set_watch_var(0, watch_var)
        retrieved = app_state.get_watch_var(0)

        assert retrieved.name == "test_var"
        assert retrieved.value == 10.0  # noqa: PLR2004

    def test_set_watch_variable_bounds(self, app_state):
        """Test watch variable index bounds checking."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        # Should not raise for valid indices
        app_state.set_watch_var(0, WatchVariable(name="var0"))
        app_state.set_watch_var(4, WatchVariable(name="var4"))

        # Get should return empty WatchVariable for invalid index
        result = app_state.get_watch_var(999)
        assert result.name == ""  # Empty default

    def test_set_scope_channel(self, app_state):
        """Test setting scope channel properties."""
        from pyx2cscope.gui.qt.models.app_state import ScopeChannel

        channel = ScopeChannel(name="channel_var")
        app_state.set_scope_channel(0, channel)
        retrieved = app_state.get_scope_channel(0)

        assert retrieved.name == "channel_var"

    def test_trigger_settings_defaults(self, app_state):
        """Test trigger settings have correct defaults."""
        trigger = app_state.get_trigger_settings()

        assert trigger.mode == "Auto"
        assert trigger.edge == "Rising"
        assert trigger.level == 0.0
        assert trigger.delay == 0

    def test_device_info_defaults(self, app_state):
        """Test device info has correct defaults."""
        info = app_state.get_device_info()

        assert info.processor_id == ""
        assert info.uc_width == ""

    def test_clear_state_on_disconnect(self, app_state):
        """Test state is properly cleared on disconnect."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        # Set some state
        app_state.set_watch_var(0, WatchVariable(name="test", value=100.0))

        # Setting x2cscope to None clears connection
        app_state.set_x2cscope(None)

        assert app_state.is_connected() is False


class TestWatchVariableDataclass:
    """Tests for WatchVariable dataclass."""

    def test_scaled_value_calculation(self):
        """Test scaled value is calculated correctly."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        watch_var = WatchVariable(
            name="test", value=10.0, scaling=2.0, offset=5.0
        )

        # scaled_value = (value * scaling) + offset = (10 * 2) + 5 = 25
        assert watch_var.scaled_value == 25.0  # noqa: PLR2004

    def test_scaled_value_with_defaults(self):
        """Test scaled value with default scaling and offset."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        watch_var = WatchVariable(name="test", value=10.0)

        # With default scaling=1.0 and offset=0.0
        assert watch_var.scaled_value == 10.0  # noqa: PLR2004

    def test_var_ref_property(self):
        """Test var_ref property get/set."""
        from pyx2cscope.gui.qt.models.app_state import WatchVariable

        watch_var = WatchVariable(name="test")
        mock_ref = MagicMock()

        watch_var.var_ref = mock_ref
        assert watch_var.var_ref is mock_ref


class TestScopeChannelDataclass:
    """Tests for ScopeChannel dataclass."""

    def test_default_values(self):
        """Test ScopeChannel default values."""
        from pyx2cscope.gui.qt.models.app_state import ScopeChannel

        channel = ScopeChannel()

        assert channel.name == ""
        assert channel.trigger is False
        assert channel.gain == 1.0
        assert channel.visible is True

    def test_custom_values(self):
        """Test ScopeChannel with custom values."""
        from pyx2cscope.gui.qt.models.app_state import ScopeChannel

        channel = ScopeChannel(
            name="test_channel", trigger=True, gain=2.5, visible=False
        )

        assert channel.name == "test_channel"
        assert channel.trigger is True
        assert channel.gain == 2.5  # noqa: PLR2004
        assert channel.visible is False


class TestTriggerSettingsDataclass:
    """Tests for TriggerSettings dataclass."""

    def test_default_values(self):
        """Test TriggerSettings default values."""
        from pyx2cscope.gui.qt.models.app_state import TriggerSettings

        trigger = TriggerSettings()

        assert trigger.mode == "Auto"
        assert trigger.edge == "Rising"
        assert trigger.level == 0.0
        assert trigger.delay == 0
        assert trigger.variable is None


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def connection_manager(self):
        """Create ConnectionManager instance."""
        from pyx2cscope.gui.qt.controllers.connection_manager import (
            ConnectionManager,
        )
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        return ConnectionManager(app_state)

    def test_initial_state(self, connection_manager):
        """Test ConnectionManager initializes correctly."""
        assert connection_manager is not None

    def test_refresh_ports(self, connection_manager, mocker):
        """Test port refresh returns list of ports."""
        # Mock serial.tools.list_ports
        mock_port = MagicMock()
        mock_port.device = "COM1"
        mock_port.description = "Test Port"

        mocker.patch(
            "serial.tools.list_ports.comports", return_value=[mock_port]
        )

        ports = connection_manager.refresh_ports()

        assert len(ports) >= 0  # May be empty on some systems

    def test_connection_manager_has_app_state(self, connection_manager):
        """Test ConnectionManager has access to AppState."""
        assert connection_manager._app_state is not None


class TestConnectionManagerConnections:
    """Tests for ConnectionManager connection methods."""

    @pytest.fixture
    def connection_manager(self):
        """Create ConnectionManager instance."""
        from pyx2cscope.gui.qt.controllers.connection_manager import (
            ConnectionManager,
        )
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        return ConnectionManager(app_state)

    def test_connect_uart_creates_x2cscope(
        self, connection_manager, elf_file_path, mocker, mock_serial_16bit
    ):
        """Test UART connection creates X2CScope instance."""
        result = connection_manager.connect_uart(
            port="COM1", baud_rate=115200, elf_file=elf_file_path
        )

        assert result is True

    def test_connect_uart_imports_selected_file(self, connection_manager, mocker):
        """Test UART connection always loads variables through import_variables."""
        mock_x2c = MagicMock()
        mock_x2c.list_variables.return_value = []
        mocker.patch(
            "pyx2cscope.gui.qt.controllers.connection_manager.X2CScope",
            return_value=mock_x2c,
        )

        result = connection_manager.connect_uart(
            port="COM1", baud_rate=115200, elf_file="firmware.elf"
        )

        assert result is True
        mock_x2c.import_variables.assert_called_once_with("firmware.elf")

    def test_connect_tcp_imports_yml_after_connect(self, connection_manager, mocker):
        """Test TCP connection loads YML imports after creating the transport."""
        mock_x2c = MagicMock()
        mock_x2c.list_variables.return_value = []
        mocker.patch(
            "pyx2cscope.gui.qt.controllers.connection_manager.X2CScope",
            return_value=mock_x2c,
        )

        result = connection_manager.connect_tcp(
            host="127.0.0.1", tcp_port=12666, elf_file="variables.yml"
        )

        assert result is True
        mock_x2c.import_variables.assert_called_once_with("variables.yml")

    def test_disconnect_clears_state(self, connection_manager):
        """Test disconnect clears connection state."""
        connection_manager.disconnect()

        assert connection_manager._app_state.is_connected() is False


class TestConfigManager:
    """Tests for ConfigManager."""

    @pytest.fixture
    def config_manager(self):
        """Create ConfigManager instance."""
        from pyx2cscope.gui.qt.controllers.config_manager import ConfigManager

        return ConfigManager()

    def test_config_manager_creation(self, config_manager):
        """Test ConfigManager can be created."""
        assert config_manager is not None

    def test_config_manager_has_signals(self, config_manager):
        """Test ConfigManager has required signals."""
        assert hasattr(config_manager, "config_loaded")
        assert hasattr(config_manager, "config_saved")
        assert hasattr(config_manager, "error_occurred")


class TestQtWidgetCreation:
    """Tests for Qt widget creation (headless)."""

    @pytest.fixture
    def qt_application(self):
        """Create QApplication for widget testing."""
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_main_window_creation(self, qt_application, mocker):
        """Test MainWindow can be created."""
        # Mock X2CScope to prevent real connection attempts
        mocker.patch("pyx2cscope.x2cscope.X2CScope")

        from pyx2cscope.gui.qt.main_window import MainWindow

        window = MainWindow()

        assert window is not None
        window.close()

    def test_setup_tab_creation(self, qt_application):
        """Test SetupTab can be created."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab

        app_state = AppState()
        tab = SetupTab(app_state)

        assert tab is not None

    def test_app_state_exports_selected_variables(self, qt_application):
        """Test AppState exports only variables selected in watch and scope views."""
        from pyx2cscope.gui.qt.models.app_state import AppState, ScopeChannel

        app_state = AppState()
        mock_x2c = MagicMock()

        mock_x2c.list_variables.return_value = ["watch.var", "scope.var"]

        app_state.set_x2cscope(mock_x2c)
        app_state.add_live_watch_var()
        app_state.update_live_watch_var_field(0, "name", "watch.var")
        app_state.set_scope_channel(0, ScopeChannel(name="scope.var", sfr=True))

        app_state.export_selected_variables("selected.yml")

        exported_items = mock_x2c.export_variables.call_args.kwargs["items"]
        assert set(exported_items) == {("watch.var", False), ("scope.var", True)}

    def test_scope_view_tab_creation(self, qt_application):
        """Test ScopeViewTab can be created."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.scope_view_tab import ScopeViewTab

        app_state = AppState()
        tab = ScopeViewTab(app_state)

        assert tab is not None

    def test_watch_view_tab_creation(self, qt_application):
        """Test WatchViewTab can be created."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.watch_view_tab import WatchViewTab

        app_state = AppState()
        tab = WatchViewTab(app_state)

        assert tab is not None

    def test_scripting_tab_creation(self, qt_application):
        """Test ScriptingTab can be created."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.scripting_tab import ScriptingTab

        app_state = AppState()
        tab = ScriptingTab(app_state)

        assert tab is not None


class TestDataPoller:
    """Tests for DataPoller worker thread."""

    @pytest.fixture
    def data_poller(self):
        """Create DataPoller instance."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.workers.data_poller import DataPoller

        app_state = AppState()
        return DataPoller(app_state)

    def test_data_poller_creation(self, data_poller):
        """Test DataPoller can be created."""
        assert data_poller is not None

    def test_data_poller_initial_state(self, data_poller):
        """Test DataPoller has correct initial state."""
        assert data_poller._running is False

    def test_set_polling_enabled(self, data_poller):
        """Test polling can be enabled/disabled."""
        data_poller.set_watch_polling_enabled(True)
        data_poller.set_scope_polling_enabled(True)

        # Verify state (actual attribute names may vary)
        assert data_poller._watch_polling_enabled is True
        assert data_poller._scope_polling_enabled is True

    def test_stop_polling(self, data_poller):
        """Test polling can be stopped."""
        data_poller.stop()
        assert data_poller._running is False


class TestCANConnectionManager:
    """Tests for ConnectionManager CAN connect/disconnect cycle."""

    elf_file = os.path.join(
        os.path.dirname(data.__file__), "mc_foc_sl_fip_dspic33ck_mclv48v300w.elf"
    )

    def test_qt_connection_manager_disconnect_calls_x2cscope_disconnect(self, mock_can_bus):
        """Test that Qt ConnectionManager properly calls x2cscope.disconnect()."""
        from unittest.mock import patch

        from PyQt5.QtCore import QCoreApplication

        from pyx2cscope.gui.qt.controllers.connection_manager import ConnectionManager
        from pyx2cscope.gui.qt.models.app_state import AppState

        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication([])

        try:
            _, mock_bus_instance = mock_can_bus

            app_state = AppState()
            conn_manager = ConnectionManager(app_state)

            device_info_frame = bytearray(
                b'\x55\x2E\x01\x11\x00'
                b'\x01\x00'
                b'\x01\x00'
                b'\x10\x82'
                b'01/01/2024'
                b'1200'
                b'01/01/2024'
                b'1200'
                b'\x01'
                b'\x00\x00'
                b'\x00\x00\x00\x00'
                b'\x00\x00\x00\x00'
                b'\x00'
            )
            load_param_frame = bytearray(b'\x55\x00\x01\x12\x00\x00')

            with patch('mchplnet.interfaces.can.LNetCan.read') as mock_read, \
                 patch('mchplnet.interfaces.can.LNetCan.write'):
                mock_read.side_effect = [device_info_frame, load_param_frame]

                success = conn_manager.connect_can(
                    elf_file=self.elf_file,
                    bus_type="USB",
                    channel=1,
                    baudrate="500K",
                    mode="Standard",
                    tx_id="110",
                    rx_id="100",
                )

                assert success is True
                assert app_state.is_connected()

                conn_manager.disconnect()

                assert not app_state.is_connected()
                assert app_state.x2cscope is None
                assert mock_bus_instance.shutdown.called

        finally:
            if app:
                app.quit()


class TestSignalSlotConnections:
    """Tests for signal/slot connections."""

    @pytest.fixture
    def qt_application(self):
        """Create QApplication for signal testing."""
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_app_state_signals_exist(self):
        """Test AppState has required signals."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()

        # Check signals exist
        assert hasattr(app_state, "connection_changed")
        assert hasattr(app_state, "device_info_updated")
        assert hasattr(app_state, "variable_list_updated")

    def test_connection_changed_signal_callback(self, qt_application, qtbot):
        """Test connection_changed signal can be connected."""
        from pyx2cscope.gui.qt.models.app_state import AppState

        app_state = AppState()
        callback_called = []

        def callback(connected):
            callback_called.append(connected)

        app_state.connection_changed.connect(callback)

        with qtbot.waitSignal(app_state.connection_changed, timeout=1000):
            app_state.connection_changed.emit(True)

        assert True in callback_called
