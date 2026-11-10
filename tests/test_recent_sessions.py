"""Tests for recent sessions and Save/Load Session in the Qt GUI (issue #126).

Tests cover:
- RecentSessions store: add, update, order, limit, keep views, remove, damaged file, text
- MainWindow: a session is recorded on connect and disconnect, a recent session reopens
  file, connection, script and WatchView variables, Save Config contains file, connection
  and script, missing variables are reported
- SetupTab: Recent list, Remove button and enabled state while connected

The serial port is mocked with tests/utils/serial_stub.py and QSettings is redirected to a
temporary INI file, so the tests do not touch hardware or the user's settings.
"""

import json
import os

import pytest
from PyQt5.QtCore import QSettings

from pyx2cscope.gui.qt.controllers.session_store import (
    VIEW_KEYS,
    RecentSessions,
)

# Set headless mode before Qt windows are created
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

MAX_ENTRIES = 3
PORT = "COM1"
COMBO_ITEMS_WITH_ONE_SESSION = 2  # placeholder + one session
TCP_PORT = 5555


def _config(elf_file, **extra):
    """Return a minimal session configuration."""
    config = {"elf_file": elf_file, "connection": {"interface": "UART", "port": PORT}}
    config.update(extra)
    return config


class TestRecentSessionsStore:
    """Tests for the RecentSessions store."""

    def test_empty_without_file(self, tmp_path):
        """Test a missing sessions file gives an empty list."""
        assert RecentSessions(str(tmp_path / "sessions.json")).entries() == []

    def test_save_and_reload(self, tmp_path):
        """Test a saved session is written to disk and read back by a new store."""
        path = str(tmp_path / "sub" / "sessions.json")
        RecentSessions(path).save_session(_config("a.elf", script="s.py"))

        reloaded = RecentSessions(path)

        assert reloaded.get("a.elf")["script"] == "s.py"
        assert json.loads(open(path, encoding="utf-8").read())["version"] == 1

    def test_most_recent_first_and_one_entry_per_file(self, tmp_path):
        """Test saving an existing file updates it and moves it to the top."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session(_config("a.elf"))
        store.save_session(_config("b.elf"))
        store.save_session(_config("a.elf", script="new.py"))

        files = [e["config"]["elf_file"] for e in store.entries()]
        assert files == ["a.elf", "b.elf"]
        assert store.get("a.elf")["script"] == "new.py"

    def test_limit(self, tmp_path):
        """Test only the most recent sessions are kept."""
        store = RecentSessions(str(tmp_path / "s.json"), max_entries=MAX_ENTRIES)
        for name in ["a", "b", "c", "d"]:
            store.save_session(_config(f"{name}.elf"))

        assert [e["config"]["elf_file"] for e in store.entries()] == ["d.elf", "c.elf", "b.elf"]

    def test_keep_views(self, tmp_path):
        """Test keep_views keeps the stored views and updates the connection."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session(_config("a.elf", watch_view=[{"variable": "x"}], view_mode="Both"))

        store.save_session(
            _config("a.elf", watch_view=[{"variable": "other_project_var"}], connection={"interface": "TCP/IP"}),
            keep_views=True,
        )

        config = store.get("a.elf")
        assert config["watch_view"] == [{"variable": "x"}]
        assert config["view_mode"] == "Both"
        assert config["connection"] == {"interface": "TCP/IP"}

    def test_keep_views_for_new_file(self, tmp_path):
        """Test keep_views on a new file stores no views from the previous project."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session(
            _config("new.elf", watch_view=[{"variable": "old"}], scope_view=[], view_mode="Both"),
            keep_views=True,
        )

        config = store.get("new.elf")
        assert not any(key in config for key in VIEW_KEYS)

    def test_ignores_config_without_file(self, tmp_path):
        """Test a configuration without elf_file is not stored."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session({"watch_view": []})

        assert store.entries() == []

    def test_remove(self, tmp_path):
        """Test a session can be removed."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session(_config("a.elf"))
        store.remove("a.elf")

        assert store.get("a.elf") is None

    def test_damaged_file(self, tmp_path):
        """Test a damaged sessions file is ignored instead of breaking the GUI."""
        path = tmp_path / "s.json"
        path.write_text("{ not json", encoding="utf-8")

        assert RecentSessions(str(path)).entries() == []

    def test_describe(self, tmp_path, elf_file_path):
        """Test the list text shows the project name and marks missing files."""
        store = RecentSessions(str(tmp_path / "s.json"))
        store.save_session(_config(elf_file_path))
        store.save_session(_config(str(tmp_path / "gone.elf")))

        texts = [RecentSessions.describe(e) for e in store.entries()]

        assert texts[0].startswith("gone - ") and texts[0].endswith("(file not found)")
        assert texts[1].startswith("mc_foc_sl_fip_dspic33ck_mclv48v300w - ")
        assert "file not found" not in texts[1]


@pytest.fixture
def temp_qsettings(tmp_path, mocker):
    """Redirect every QSettings("Microchip", "pyX2Cscope") of the Qt GUI to a temporary INI file."""
    ini = str(tmp_path / "settings.ini")

    def make_settings(*_args, **_kwargs):
        return QSettings(ini, QSettings.IniFormat)

    for module in (
        "pyx2cscope.gui.qt.main_window",
        "pyx2cscope.gui.qt.tabs.setup_tab",
        "pyx2cscope.gui.qt.tabs.scripting_tab",
        "pyx2cscope.gui.qt.controllers.config_manager",
    ):
        mocker.patch(f"{module}.QSettings", side_effect=make_settings)
    return ini


@pytest.fixture
def window(qtbot, tmp_path, temp_qsettings, mock_serial_16bit, mocker):
    """Create a MainWindow with a temporary sessions file and a mocked serial port."""
    from pyx2cscope.gui.qt.main_window import MainWindow

    win = MainWindow(sessions_file=str(tmp_path / "recent_sessions.json"))
    qtbot.addWidget(win)
    win._setup_tab.set_ports([PORT])
    win._setup_tab.port_combo.setCurrentText(PORT)
    win._show_error = mocker.MagicMock()
    win._show_warning = mocker.MagicMock()
    yield win
    win.close()


def _connect(win, elf_file):
    """Select the file in the Setup tab and connect."""
    win._setup_tab.elf_file_path = elf_file
    win._on_connect_clicked()
    assert win._app_state.is_connected(), win._show_error.call_args


def _disconnect(win):
    """Disconnect with the Setup tab's Connect/Disconnect button."""
    win._on_connect_clicked()
    assert not win._app_state.is_connected()


class TestMainWindowSessions:
    """Tests for recording and reopening sessions in the main window."""

    def test_connect_records_session(self, window, elf_file_path):
        """Test connecting adds the file and connection to the recent sessions."""
        _connect(window, elf_file_path)

        config = window._recent_sessions.get(elf_file_path)
        assert config["elf_file"] == os.path.abspath(elf_file_path)
        assert config["connection"]["port"] == PORT
        assert window._setup_tab.recent_combo.count() == COMBO_ITEMS_WITH_ONE_SESSION

    def test_disconnect_records_views_and_script(self, window, elf_file_path, tmp_path):
        """Test disconnecting stores the WatchView variables and the loaded script."""
        script = tmp_path / "my_script.py"
        script.write_text("print('hi')\n", encoding="utf-8")
        _connect(window, elf_file_path)
        variable = window._app_state.get_variable_list()[0]
        window._apply_config({"watch_view": [{"variable": variable}], "script": str(script)})

        _disconnect(window)

        config = window._recent_sessions.get(elf_file_path)
        assert [v["variable"] for v in config["watch_view"]] == [variable]
        assert config["script"] == str(script)
        assert config["script_folder"] == str(tmp_path)

    def test_selecting_entry_does_not_connect(self, window, elf_file_path):
        """Test choosing an entry in the Recent list only selects it; nothing is loaded or connected."""
        _connect(window, elf_file_path)
        _disconnect(window)
        window._setup_tab.elf_file_path = ""

        window._setup_tab.recent_combo.setCurrentIndex(1)

        assert not window._app_state.is_connected()
        assert window._setup_tab.elf_file_path == ""
        assert window._setup_tab._load_recent_btn.isEnabled()

    def test_open_recent_session_restores_everything(self, window, elf_file_path, tmp_path):
        """Test Load Session fills in file, connection and script, connects and restores variables."""
        script = tmp_path / "my_script.py"
        script.write_text("print('hi')\n", encoding="utf-8")
        _connect(window, elf_file_path)
        variable = window._app_state.get_variable_list()[0]
        window._apply_config({"watch_view": [{"variable": variable}], "script": str(script)})
        _disconnect(window)

        # Start from a clean window state
        window._watch_view_tab.clear_all_rows()
        window._setup_tab.elf_file_path = ""
        window._scripting_tab._script_path = ""
        window._scripting_tab.set_script_folder("")

        window._setup_tab.recent_combo.setCurrentIndex(1)
        window._setup_tab._load_recent_btn.click()

        assert window._app_state.is_connected()
        assert window._setup_tab.elf_file_path == os.path.abspath(elf_file_path)
        assert window._scripting_tab.script_path == str(script)
        assert window._scripting_tab.script_folder == str(tmp_path)
        assert window._watch_view_tab.get_config()["variables"] == [variable]
        window._show_warning.assert_not_called()

    def test_open_session_with_missing_file(self, window, tmp_path):
        """Test a session whose file no longer exists shows an error and does not connect."""
        missing = str(tmp_path / "gone.elf")
        window._recent_sessions.save_session(_config(missing))

        window._open_recent_session(missing)

        assert not window._app_state.is_connected()
        assert "not found" in window._show_error.call_args.args[0]

    def test_missing_variables_are_reported(self, window, elf_file_path):
        """Test variables that are not in the ELF file are reported after loading."""
        _connect(window, elf_file_path)

        window._apply_config({"watch_view": [{"variable": "no_such_variable"}]})

        assert "no_such_variable" in window._show_warning.call_args.args[0]

    def test_missing_script_is_reported(self, window, elf_file_path, tmp_path):
        """Test a script that no longer exists is reported."""
        _connect(window, elf_file_path)

        window._apply_config({"script": str(tmp_path / "gone.py")})

        assert "Script not found" in window._show_warning.call_args.args[0]

    def test_script_folder_restored_when_not_the_scripts_folder(self, window, tmp_path):
        """Test a script folder that differs from the script's folder is restored after the script."""
        script_dir = tmp_path / "project"
        script_dir.mkdir()
        script = script_dir / "my_script.py"
        script.write_text("", encoding="utf-8")
        folder = tmp_path / "library"
        folder.mkdir()
        (folder / "other.py").write_text("", encoding="utf-8")

        window._apply_config({"script": str(script), "script_folder": str(folder)})

        assert window._scripting_tab.script_path == str(script)
        assert window._scripting_tab.script_folder == str(folder)
        assert window._scripting_tab.script_model.rowCount() == 1
        window._show_warning.assert_not_called()

    def test_script_folder_without_script(self, window, tmp_path):
        """Test a session with only a script folder lists its scripts and loads none."""
        (tmp_path / "a.py").write_text("", encoding="utf-8")

        window._apply_config({"script_folder": str(tmp_path)})

        assert window._scripting_tab.script_folder == str(tmp_path)
        assert window._scripting_tab.script_path == ""

    def test_session_without_script_folder_uses_scripts_folder(self, window, tmp_path):
        """Test an older session without script_folder still lists the scripts next to the script."""
        script = tmp_path / "my_script.py"
        script.write_text("", encoding="utf-8")

        window._apply_config({"script": str(script)})

        assert window._scripting_tab.script_folder == str(tmp_path)

    def test_missing_script_folder_is_reported(self, window, elf_file_path, tmp_path):
        """Test a script folder that no longer exists is reported."""
        _connect(window, elf_file_path)

        window._apply_config({"script_folder": str(tmp_path / "gone")})

        assert "Script folder not found" in window._show_warning.call_args.args[0]

    def test_load_while_connected_keeps_file(self, window, elf_file_path, elf_file_path_32bit):
        """Test loading a session while connected keeps the current file and connection."""
        _connect(window, elf_file_path)

        window._apply_config(_config(elf_file_path_32bit))

        assert window._setup_tab.elf_file_path == elf_file_path

    def test_save_config_contains_session(self, window, elf_file_path, tmp_path):
        """Test Save Config/Save Session writes file, connection and script with the views."""
        script = tmp_path / "my_script.py"
        script.write_text("", encoding="utf-8")
        window._setup_tab.elf_file_path = elf_file_path
        window._scripting_tab.set_script(str(script))

        config = window._build_config()

        assert config["elf_file"] == os.path.abspath(elf_file_path)
        assert config["connection"]["interface"] == "UART"
        assert config["script"] == str(script)
        assert config["script_folder"] == str(tmp_path)
        assert {"watch_view", "scope_view", "view_mode"} <= config.keys()

    def test_save_config_contains_selected_script_folder(self, window, tmp_path):
        """Test the script folder is saved even when no script is loaded."""
        window._scripting_tab.set_script_folder(str(tmp_path))

        config = window._build_config()

        assert config["script_folder"] == str(tmp_path)
        assert "script" not in config

    def test_save_config_with_array_value(self, window, elf_file_path):
        """Test Save Config works when a WatchView row shows an array value (it used to raise ValueError)."""
        _connect(window, elf_file_path)
        window._apply_config({"watch_view": [{"variable": "x"}]})
        window._watch_view_tab._value_edits[0].setText("[0, 1, 2]")

        config = window._build_config()

        assert config["watch_view"][0]["value"] == 0.0

    def test_remove_recent_session(self, window, elf_file_path):
        """Test the Remove button removes the selected session."""
        _connect(window, elf_file_path)
        _disconnect(window)
        window._setup_tab.recent_combo.setCurrentIndex(1)

        window._setup_tab._remove_recent_btn.click()

        assert window._recent_sessions.entries() == []
        assert window._setup_tab.recent_combo.count() == 1


class TestSetupTabSessions:
    """Tests for the Sessions group of the Setup tab."""

    @pytest.fixture
    def setup_tab(self, qtbot, temp_qsettings):
        """Create a SetupTab."""
        from pyx2cscope.gui.qt.models.app_state import AppState
        from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab

        tab = SetupTab(AppState())
        qtbot.addWidget(tab)
        return tab

    def test_placeholder_and_entries(self, setup_tab):
        """Test the list starts with a placeholder and selects the current file."""
        setup_tab.set_recent_sessions([("A - date", "a.elf"), ("B - date", "b.elf")], current_file="b.elf")

        assert setup_tab.recent_combo.itemText(0) == setup_tab.RECENT_PLACEHOLDER
        assert setup_tab.selected_recent_session == "b.elf"
        assert setup_tab._remove_recent_btn.isEnabled()

    def test_load_session_needs_selection(self, setup_tab):
        """Test Load Session and Remove are disabled while the placeholder is selected."""
        setup_tab.set_recent_sessions([("A - date", "a.elf")])

        assert setup_tab.selected_recent_session == ""
        assert not setup_tab._load_recent_btn.isEnabled()
        assert not setup_tab._remove_recent_btn.isEnabled()

    def test_choosing_entry_emits_nothing(self, setup_tab, qtbot):
        """Test choosing an entry in the list does not request loading it."""
        setup_tab.set_recent_sessions([("A - date", "a.elf")])

        with qtbot.assertNotEmitted(setup_tab.recent_session_load_requested):
            setup_tab.recent_combo.setCurrentIndex(1)
            setup_tab.recent_combo.activated.emit(1)

    def test_load_session_emits_file(self, setup_tab, qtbot):
        """Test Load Session requests the selected session."""
        setup_tab.set_recent_sessions([("A - date", "a.elf")])
        setup_tab.recent_combo.setCurrentIndex(1)

        with qtbot.waitSignal(setup_tab.recent_session_load_requested, timeout=1000) as blocker:
            setup_tab._load_recent_btn.click()

        assert blocker.args == ["a.elf"]

    def test_disabled_while_connected(self, setup_tab):
        """Test another session cannot be opened while connected; saving stays possible."""
        setup_tab.set_recent_sessions([("A - date", "a.elf")], current_file="a.elf")

        setup_tab.set_connected(True)

        assert not setup_tab.recent_combo.isEnabled()
        assert not setup_tab._load_recent_btn.isEnabled()
        assert not setup_tab._remove_recent_btn.isEnabled()
        assert not setup_tab._load_session_btn.isEnabled()
        assert setup_tab._save_session_btn.isEnabled()

    def test_restores_uart_port_and_tcp_port(self, setup_tab):
        """Test set_connection_params restores the UART port and the TCP port written by get_connection_params."""
        setup_tab.set_ports(["COM7"])
        setup_tab.set_connection_params({"interface": "UART", "port": "COM7"})
        assert setup_tab.port_combo.currentText() == "COM7"

        setup_tab.set_connection_params({"interface": "UART", "port": "COM99"})
        assert setup_tab.port_combo.currentText() == "AUTO"

        setup_tab.set_connection_params({"interface": "TCP/IP", "host": "10.0.0.2", "tcp_port": TCP_PORT})
        params = setup_tab.get_connection_params()
        assert params["host"] == "10.0.0.2"
        assert params["tcp_port"] == TCP_PORT
