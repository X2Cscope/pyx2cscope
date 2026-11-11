"""Main window for the Qt GUI application."""

import logging
import os

from PyQt5 import QtGui
from PyQt5.QtCore import QSettings, Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyleFactory,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import pyx2cscope
from pyx2cscope.gui import img as img_src
from pyx2cscope.gui.qt.controllers.config_manager import ConfigManager
from pyx2cscope.gui.qt.controllers.connection_manager import ConnectionManager
from pyx2cscope.gui.qt.controllers.session_store import RecentSessions
from pyx2cscope.gui.qt.dashboard.main_window import DashboardWindow
from pyx2cscope.gui.qt.models.app_state import AppState
from pyx2cscope.gui.qt.tabs.help_tab import HelpTab
from pyx2cscope.gui.qt.tabs.scope_view_tab import ScopeViewTab
from pyx2cscope.gui.qt.tabs.scripting_tab import ScriptingTab, ScriptRunControl, same_path
from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab
from pyx2cscope.gui.qt.tabs.watch_view_tab import WatchViewTab
from pyx2cscope.gui.qt.workers.data_poller import DataPoller
from pyx2cscope.utils import get_project_name


def _to_float(text, default: float) -> float:
    """Convert a text field to float, or return default if it is empty or not a number.

    Args:
        text: The text, e.g. "1.5", "" or an array value "[1, 2]".
        default: The value used when the text is not a number.

    Returns:
        float: The number.
    """
    try:
        return float(text) if text not in ("", None) else default
    except (TypeError, ValueError):
        return default


class MainWindow(QMainWindow):
    """Main application window for pyX2Cscope GUI.

    Orchestrates all components:
    - Connection management
    - Data polling worker
    - Tab widgets for different views
    - Configuration save/load
    """

    def __init__(self, parent=None, **kwargs):
        """Initialize the main window.

        Args:
            parent: Optional parent widget.
            **kwargs: Optional CLI arguments forwarded from the command line.
                      Relevant keys: ``elf`` (path to ELF file) and
                      ``port`` (COM port), which trigger an automatic
                      connection attempt after the window is displayed.
                      ``sessions_file`` sets the recent sessions file
                      (default: the user configuration folder).
        """
        super().__init__(parent)

        # Store CLI arguments for deferred auto-connect
        self._cli_elf = kwargs.get("elf")
        self._cli_port = kwargs.get("port")

        # Initialize settings
        self._settings = QSettings("Microchip", "pyX2Cscope")
        self._recent_sessions = RecentSessions(kwargs.get("sessions_file"))

        # Initialize app state
        self._app_state = AppState(self)

        # Initialize controllers
        self._connection_manager = ConnectionManager(self._app_state, self)
        self._config_manager = ConfigManager(self)

        # Initialize data poller (but don't start yet)
        self._data_poller = DataPoller(self._app_state, self)

        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._refresh_recent_sessions()

        # Start data poller thread
        self._data_poller.start()

        # Refresh ports on startup
        self._refresh_ports()

        # If CLI provided elf + port, schedule auto-connect after event loop starts
        if self._cli_elf and self._cli_port:
            QTimer.singleShot(0, self._auto_connect)

    def _setup_ui(self):  # noqa: PLR0915
        """Set up the user interface."""
        QApplication.setStyle(QStyleFactory.create("Fusion"))

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tabs
        self._tab_widget = QTabWidget()
        main_layout.addWidget(self._tab_widget)

        # Tab 1: Setup
        self._setup_tab = SetupTab(self._app_state, self)
        self._tab_widget.addTab(self._setup_tab, "Setup")

        # The Scripting tab is created here because the Data Views tab has a button that runs its script.
        # It is added to the tab widget after Data Views.
        self._scripting_tab = ScriptingTab(self._app_state, self)

        # Tab 2: Data Views (contains WatchView and/or ScopeView)
        self._data_views_tab = QWidget()
        data_views_layout = QVBoxLayout(self._data_views_tab)
        data_views_layout.setContentsMargins(5, 5, 5, 5)  # left, top, right, bottom

        # Top bar: Toggle buttons and Save/Load buttons
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(10, 10, 10, 10)  # Add bottom padding

        # Toggle button style
        toggle_style = """
            QPushButton {
                border: 1px solid #999;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #0078d4;
                color: white;
                border: 1px solid #0078d4;
            }
            QPushButton:hover {
                border: 1px solid #0078d4;
            }
        """

        # WatchView toggle button
        self._watch_view_btn = QPushButton("WatchView")
        self._watch_view_btn.setCheckable(True)
        self._watch_view_btn.setChecked(False)  # Start disabled
        self._watch_view_btn.setFixedSize(100, 28)
        self._watch_view_btn.setStyleSheet(toggle_style)
        self._watch_view_btn.clicked.connect(self._on_view_toggle_changed)
        top_bar_layout.addWidget(self._watch_view_btn)

        # ScopeView toggle button
        self._scope_view_btn = QPushButton("ScopeView")
        self._scope_view_btn.setCheckable(True)
        self._scope_view_btn.setChecked(False)  # Start disabled
        self._scope_view_btn.setFixedSize(100, 28)
        self._scope_view_btn.setStyleSheet(toggle_style)
        self._scope_view_btn.clicked.connect(self._on_view_toggle_changed)
        top_bar_layout.addWidget(self._scope_view_btn)

        # Run/Stop the script loaded in the Scripting tab while watching the views
        top_bar_layout.addSpacing(20)
        self._run_script_control = ScriptRunControl(self._scripting_tab, self)
        top_bar_layout.addWidget(self._run_script_control)

        top_bar_layout.addStretch()

        # Save/Load/Export buttons
        self._export_variables_button = QPushButton("Export Variables")
        self._export_variables_button.setFixedSize(120, 28)
        self._export_variables_button.setEnabled(False)
        self._export_variables_button.clicked.connect(self._export_selected_variables)
        self._save_button = QPushButton("Save Config")
        self._save_button.setFixedSize(100, 28)
        self._save_button.clicked.connect(self._save_config)
        self._load_button = QPushButton("Load Config")
        self._load_button.setFixedSize(100, 28)
        self._load_button.clicked.connect(self._load_config)
        top_bar_layout.addWidget(self._export_variables_button)
        top_bar_layout.addWidget(self._save_button)
        top_bar_layout.addWidget(self._load_button)
        data_views_layout.addLayout(top_bar_layout)

        # Create the views
        self._watch_view_tab = WatchViewTab(self._app_state, self)
        self._scope_view_tab = ScopeViewTab(self._app_state, self)

        # Instruction screen (shown when no view is selected)
        self._instruction_widget = QWidget()
        instruction_layout = QVBoxLayout(self._instruction_widget)
        instruction_layout.setAlignment(Qt.AlignCenter)
        instruction_label = QLabel(
            "<h2>Select a View</h2>"
            "<p>Use the toggle buttons above to select which views to display:</p>"
            "<p><b>WatchView:</b> Monitor and modify variable values in real-time.<br>"
            "Add variables, set scaling/offset, and write values directly.</p>"
            "<p><b>ScopeView:</b> Capture and visualize variable waveforms.<br>"
            "Configure trigger settings and sample multiple channels.</p>"
            "<p><i>Select both buttons to display a split view.</i></p>"
        )
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: #666; padding: 40px;")
        instruction_layout.addWidget(instruction_label)

        # Splitter for combined view (horizontal for better usability)
        self._view_splitter = QSplitter(Qt.Horizontal)
        self._view_splitter.addWidget(self._watch_view_tab)
        self._view_splitter.addWidget(self._scope_view_tab)
        self._view_splitter.setStretchFactor(0, 1)  # 50/50 split
        self._view_splitter.setStretchFactor(1, 1)

        data_views_layout.addWidget(self._instruction_widget)
        data_views_layout.addWidget(self._view_splitter)

        self._tab_widget.addTab(self._data_views_tab, "Data Views")

        # Tab 3: Dashboard (widgets whose data sources can be variables of the ELF file)
        self._dashboard_tab = DashboardWindow(self._app_state, self)
        self._tab_widget.addTab(self._dashboard_tab, "Dashboard")

        # Tab 4: Scripting
        self._tab_widget.addTab(self._scripting_tab, "Scripting")

        # Tab 5: Help
        self._help_tab = HelpTab(self)
        self._tab_widget.addTab(self._help_tab, "Help")

        # Set initial view (Both selected)
        self._on_view_toggle_changed()

        # Window properties
        self._update_window_title()
        icon_path = os.path.join(os.path.dirname(img_src.__file__), "pyx2cscope.jpg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Restore window state from settings
        self._restore_window_state()

    def _setup_connections(self):
        """Set up signal/slot connections."""
        # Connection manager signals
        self._connection_manager.connection_changed.connect(self._on_connection_changed)
        self._connection_manager.error_occurred.connect(self._show_error)
        self._connection_manager.ports_refreshed.connect(self._on_ports_refreshed)

        # App state signals
        self._app_state.connection_changed.connect(self._on_connection_changed)
        self._app_state.variable_list_updated.connect(self._on_variable_list_updated)

        # Data poller signals
        self._data_poller.scope_data_ready.connect(self._scope_view_tab.on_scope_data_ready)
        self._data_poller.live_var_updated.connect(self._watch_view_tab.on_live_var_updated)
        self._data_poller.error_occurred.connect(self._show_error)

        # Config manager signals
        self._config_manager.error_occurred.connect(self._show_error)

        # Setup tab signals
        self._setup_tab.connect_requested.connect(self._on_connect_clicked)
        self._setup_tab.elf_file_selected.connect(self._on_elf_file_selected)
        self._setup_tab.elf_file_changed.connect(self._update_window_title)
        self._setup_tab.refresh_btn.clicked.connect(self._refresh_ports)
        self._setup_tab.recent_session_load_requested.connect(self._open_recent_session)
        self._setup_tab.recent_session_remove_requested.connect(self._remove_recent_session)
        self._setup_tab.save_session_requested.connect(self._save_config)
        self._setup_tab.load_session_requested.connect(self._load_config)

        # Tab polling control signals -> DataPoller
        self._scope_view_tab.scope_sampling_changed.connect(self._on_scope_sampling_changed)
        self._watch_view_tab.live_polling_changed.connect(self._on_live_watch_changed)
        self._watch_view_tab.live_interval_changed.connect(self._data_poller.set_live_interval)

    def _refresh_ports(self):
        """Refresh available COM ports."""
        self._connection_manager.refresh_ports()

    def _auto_connect(self):
        """Attempt automatic connection using CLI-supplied elf and port arguments.

        Called once (via QTimer) after the window is shown.  On success the
        UI switches directly to the Data Views tab so the user can start
        monitoring right away.
        """
        if not self._cli_elf or not self._cli_port:
            return

        # Populate the Setup tab fields so the user can see what was used
        self._setup_tab.elf_file_path = self._cli_elf
        port_combo = self._setup_tab.port_combo
        if self._cli_port in [port_combo.itemText(i) for i in range(port_combo.count())]:
            port_combo.setCurrentText(self._cli_port)

        conn_params = self._setup_tab.get_connection_params()
        # Override with the CLI port in case it was not found in the combo box
        if conn_params.get("interface", "UART") == "UART":
            conn_params["port"] = self._cli_port

        QApplication.processEvents()

        connected = self._connection_manager.connect(self._cli_elf, **conn_params)

        if connected:
            self._setup_tab.set_connected(True)
            self._setup_tab.save_connection_settings()
            self._update_device_info()
            self._record_session(keep_views=True)
            # Activate WatchView and switch to Data Views tab
            self._watch_view_btn.setChecked(True)
            self._on_view_toggle_changed()
            self._tab_widget.setCurrentIndex(1)
        else:
            self._setup_tab.set_connected(False)

    def _on_ports_refreshed(self, ports: list):
        """Handle ports refreshed signal."""
        self._setup_tab.set_ports(ports)

    def _update_window_title(self, *_args):
        """Show the version and the project name of the selected ELF file in the window title.

        Several pyX2Cscope windows running in parallel can then be told apart, e.g.
        ``pyX2Cscope - v0.7.2 - my_project``.
        """
        title = f"pyX2Cscope - v{pyx2cscope.__version__}"
        project_name = get_project_name(self._setup_tab.elf_file_path)
        if project_name:
            title += f" - {project_name}"
        self.setWindowTitle(title)

    def _on_elf_file_selected(self, file_path: str):
        """Handle variable file selection from setup tab."""
        self._settings.setValue("elf_file_path", file_path)

    def _on_connect_clicked(self):
        """Handle connect button click."""
        elf_path = self._setup_tab.elf_file_path
        if not elf_path:
            # Try to load from settings
            elf_path = self._settings.value("elf_file_path", "", type=str)
            if elf_path:
                self._setup_tab.elf_file_path = elf_path

        if not elf_path:
            self._setup_tab.set_loading(False)
            self._show_error("Please select an ELF file or import first.")
            return

        # Get connection parameters based on selected interface
        conn_params = self._setup_tab.get_connection_params()

        # Disconnecting: store the session while the views still show it
        if self._app_state.is_connected():
            self._record_session()

        # Process events to show loading indicator before blocking operation
        QApplication.processEvents()

        connected = self._connection_manager.toggle_connection(
            elf_path, **conn_params
        )

        if connected:
            self._setup_tab.set_connected(True)
            self._setup_tab.save_connection_settings()
            self._update_device_info()
            self._record_session(keep_views=True)
        else:
            self._setup_tab.set_connected(False)

    # === Sessions (recent list, Save/Load Session) ===

    def _record_session(self, keep_views: bool = False):
        """Store the current session in the recent sessions list.

        Args:
            keep_views: Keep the WatchView/ScopeView settings already stored for this file. Used right
                after connecting, when the views may still show another project.
        """
        try:
            config = self._build_config()
        except Exception as e:  # never block connect, disconnect or closing the window
            logging.warning(f"Could not store the session: {e}")
            return
        if config.get("elf_file"):
            self._recent_sessions.save_session(config, keep_views=keep_views)
            self._refresh_recent_sessions()

    def _refresh_recent_sessions(self):
        """Show the recent sessions in the Setup tab."""
        sessions = [(RecentSessions.describe(e), e["config"]["elf_file"]) for e in self._recent_sessions.entries()]
        self._setup_tab.set_recent_sessions(sessions, current_file=self._setup_tab.elf_file_path)

    def _open_recent_session(self, elf_file: str):
        """Open a recent session: fill in file, connection and script, connect, restore the views.

        Args:
            elf_file: The ELF/YML/PKL file of the session.
        """
        if self._app_state.is_connected():
            return
        config = self._recent_sessions.get(elf_file)
        if config is None:
            return
        if not os.path.exists(elf_file):
            self._show_error(
                f"The file of this session was not found:\n{elf_file}\n\n"
                "Rebuild the project or remove the session from the list."
            )
            self._refresh_recent_sessions()
            return
        self._apply_config(config)

    def _remove_recent_session(self, elf_file: str):
        """Remove a session from the recent sessions list.

        Args:
            elf_file: The ELF/YML/PKL file of the session.
        """
        self._recent_sessions.remove(elf_file)
        self._refresh_recent_sessions()

    def _on_connection_changed(self, connected: bool):
        """Handle connection state change."""
        self._setup_tab.set_connected(connected)
        self._export_variables_button.setEnabled(connected)

        # Update tabs
        self._scope_view_tab.on_connection_changed(connected)
        self._watch_view_tab.on_connection_changed(connected)
        self._scripting_tab.on_connection_changed(connected)

        if connected:
            self._update_device_info()
        else:
            self._clear_device_info()

    def _on_variable_list_updated(self, variables: list):
        """Handle variable list update."""
        self._scope_view_tab.on_variable_list_updated(variables)
        self._watch_view_tab.on_variable_list_updated(variables)

    def _on_view_toggle_changed(self):
        """Handle view toggle button changes."""
        watch_selected = self._watch_view_btn.isChecked()
        scope_selected = self._scope_view_btn.isChecked()

        if watch_selected and scope_selected:
            # Both views - show splitter with both
            self._instruction_widget.hide()
            self._view_splitter.show()
            self._watch_view_tab.show()
            self._scope_view_tab.show()
        elif watch_selected:
            # Only WatchView
            self._instruction_widget.hide()
            self._view_splitter.show()
            self._watch_view_tab.show()
            self._scope_view_tab.hide()
        elif scope_selected:
            # Only ScopeView
            self._instruction_widget.hide()
            self._view_splitter.show()
            self._watch_view_tab.hide()
            self._scope_view_tab.show()
        else:
            # No view selected - show instruction screen
            self._view_splitter.hide()
            self._instruction_widget.show()

    def _on_scope_sampling_changed(self, is_sampling: bool, is_single_shot: bool):
        """Handle scope sampling state change (Tab2)."""
        self._data_poller.set_scope_polling_enabled(is_sampling, is_single_shot)

    def _on_live_watch_changed(self, index: int, is_live: bool):
        """Handle live watch variable polling state change (Tab3)."""
        if is_live:
            self._data_poller.add_active_live_index(index)
        else:
            self._data_poller.remove_active_live_index(index)

    def _update_device_info(self):
        """Update device info labels."""
        device_info = self._app_state.update_device_info()
        self._setup_tab.update_device_info(device_info)

    def _clear_device_info(self):
        """Clear device info labels."""
        self._setup_tab.clear_device_info()

    def _save_config(self):
        """Save the current session (file, connection, views and script) to a JSON file."""
        self._config_manager.save_config(self._build_config())

    def _build_config(self) -> dict:
        """Return the current session as a configuration dict.

        The format is shared with the web GUI (watch_view, scope_view, sample_control,
        trigger_control). The Qt GUI adds elf_file, connection, script and script_folder, which the
        web GUI ignores.

        Returns:
            dict: The configuration.
        """
        # Determine view mode from toggle buttons
        watch_on = self._watch_view_btn.isChecked()
        scope_on = self._scope_view_btn.isChecked()
        if watch_on and scope_on:
            view_mode = "Both"
        elif watch_on:
            view_mode = "WatchView"
        elif scope_on:
            view_mode = "ScopeView"
        else:
            view_mode = "None"

        scope_qt = self._scope_view_tab.get_config()
        watch_qt = self._watch_view_tab.get_config()

        # Build shared list-of-dicts format (compatible with web GUI)
        scope_shared = [
            {
                "variable": scope_qt["variables"][i],
                "sfr": scope_qt["sfr"][i] if i < len(scope_qt.get("sfr", [])) else False,
                "trigger": scope_qt["trigger"][i] if i < len(scope_qt.get("trigger", [])) else False,
                "enable": scope_qt["show"][i] if i < len(scope_qt.get("show", [])) else True,
                "color": scope_qt["color"][i] if i < len(scope_qt.get("color", [])) else "#ff0000",
                "gain": scope_qt["scale"][i] if i < len(scope_qt.get("scale", [])) else "1.0",
                "offset": scope_qt["offset"][i] if i < len(scope_qt.get("offset", [])) else "0.0",
            }
            for i, v in enumerate(scope_qt.get("variables", []))
            if v
        ]
        watch_shared = []
        for i, v in enumerate(watch_qt.get("variables", [])):
            if not v:
                continue
            live_var = self._app_state.get_live_watch_var(i)
            var_ref = live_var.var_ref if live_var else None
            primitive = var_ref.__class__.__name__.lower().replace("variable", "") if var_ref else ""
            if not primitive:
                primitive = watch_qt["types"][i] if i < len(watch_qt.get("types", [])) else ""
            watch_shared.append({
                "variable": v,
                "type": primitive,
                "sfr": watch_qt["sfr"][i] if i < len(watch_qt.get("sfr", [])) else False,
                "live": watch_qt["live"][i] if i < len(watch_qt.get("live", [])) else False,
                # Array values ("[1, 2, ...]") or partly typed numbers are stored with the default
                "value": _to_float(watch_qt["values"][i] if i < len(watch_qt.get("values", [])) else "", 0.0),
                "scaling": _to_float(watch_qt["scaling"][i] if i < len(watch_qt.get("scaling", [])) else "", 1.0),
                "offset": _to_float(watch_qt["offsets"][i] if i < len(watch_qt.get("offsets", [])) else "", 0.0),
                "unit": watch_qt["units"][i] if i < len(watch_qt.get("units", [])) else "",
            })

        # Build sample_control and trigger_control from scope tab Qt format
        name_to_hex = {
            "Red": "#FF0000", "Green": "#00FF00", "Blue": "#0000FF",
            "Yellow": "#FFFF00", "Cyan": "#00FFFF", "Magenta": "#FF00FF",
            "Purple": "#800080", "White": "#CCCCCC", "Black": "#000000",
        }
        trigger_edge_map = {"Rising": 1, "Falling": 0}
        trigger_mode_map = {"Enable": 1, "Disable": 0}
        sample_control = {
            "triggerAction": "shot" if scope_qt.get("single_shot") else "off",
            "sampleTime": int(scope_qt.get("sample_time_factor", 1) or 1),
            "sampleFreq": 20.0,
        }
        trigger_control = {
            "trigger_mode": trigger_mode_map.get(scope_qt.get("trigger_mode", "Disable"), 0),
            "trigger_edge": trigger_edge_map.get(scope_qt.get("trigger_edge", "Rising"), 1),
            "trigger_level": float(scope_qt.get("trigger_level", 0) or 0),
            "trigger_delay": int(scope_qt.get("trigger_delay", 0) or 0),
        }
        # Convert Qt color names to hex in the scope shared list
        for entry in scope_shared:
            entry["color"] = name_to_hex.get(entry.get("color", ""), entry.get("color", "#FF0000"))

        config = ConfigManager.build_config(
            scope_view=scope_shared,
            watch_view=watch_shared,
            view_mode=view_mode,
            sample_control=sample_control,
            trigger_control=trigger_control,
        )
        elf_file = self._setup_tab.elf_file_path
        if elf_file:
            config["elf_file"] = os.path.abspath(elf_file)
        try:
            config["connection"] = self._setup_tab.get_connection_params()
        except ValueError:
            # e.g. an empty CAN channel field; keep at least the interface
            config["connection"] = {"interface": self._setup_tab.interface_type}
        config.update(self._script_config())
        return config

    def _script_config(self) -> dict:
        """Return the script and script folder of the Scripting tab for the configuration.

        Returns:
            dict: ``script`` and ``script_folder``, each only when set.
        """
        config = {}
        if self._scripting_tab.script_path:
            config["script"] = os.path.abspath(self._scripting_tab.script_path)
        if self._scripting_tab.script_folder:
            config["script_folder"] = self._scripting_tab.script_folder
        return config

    def _export_selected_variables(self):
        """Export variables currently selected in WatchView and ScopeView."""
        source_path = self._setup_tab.elf_file_path or self._settings.value("elf_file_path", "", type=str)
        default_name = os.path.splitext(os.path.basename(source_path))[0] if source_path else "variables_list"
        export_dir = self._settings.value("variable_export_dir", "", type=str)
        default_path = os.path.join(export_dir, default_name + ".yml") if export_dir else default_name + ".yml"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Selected Variables",
            default_path,
            "YAML Files (*.yml);;Pickle Files (*.pkl)",
        )
        if not file_path:
            return

        self._settings.setValue("variable_export_dir", os.path.dirname(file_path))
        try:
            self._app_state.export_selected_variables(file_path)
            QMessageBox.information(self, "Export Complete", f"Variables exported to:\n{file_path}")
        except Exception as e:
            self._show_error(str(e))

    def _load_config(self):
        """Load a session or configuration from a JSON file and apply it."""
        config = self._config_manager.load_config()
        if config:
            self._apply_config(config)

    def _apply_config(self, config: dict):  # noqa: PLR0912, PLR0915
        """Apply a session or configuration: file, connection, script, connect, then the views.

        While connected, the file and connection are kept and only the views and script are loaded.

        Args:
            config: The configuration, as written by :meth:`_build_config` or by the web GUI.
        """
        warnings = []
        connected_before = self._app_state.is_connected()

        # Load ELF file
        elf_path = "" if connected_before else config.get("elf_file", "")
        if elf_path:
            if self._config_manager.validate_elf_file(elf_path):
                self._setup_tab.elf_file_path = elf_path
            else:
                self._config_manager.show_file_not_found_warning(elf_path)
                new_path = self._config_manager.prompt_for_elf_file()
                if new_path:
                    self._setup_tab.elf_file_path = new_path

        # Load connection settings (new format with interface support)
        conn_params = config.get("connection", {})
        if connected_before:
            pass  # keep the current connection
        elif conn_params:
            # Includes the UART port; a port that is not available falls back to AUTO
            self._setup_tab.set_connection_params(conn_params)
        elif "baud_rate" in config or "com_port" in config:
            # Legacy config format support
            baud_rate = config.get("baud_rate", "115200")
            self._setup_tab.baud_combo.setCurrentText(baud_rate)
            com_port = config.get("com_port", "")
            port_combo = self._setup_tab.port_combo
            if com_port and com_port in [port_combo.itemText(i) for i in range(port_combo.count())]:
                port_combo.setCurrentText(com_port)

        # Load the script of the session into the Scripting tab
        script = config.get("script", "")
        if script:
            if os.path.exists(script):
                self._scripting_tab.set_script(script)
            else:
                warnings.append(f"Script not found: {script}")

        # Then the script folder: it can differ from the script's folder, so it is set after the script
        script_folder = config.get("script_folder", "")
        if script_folder:
            if not os.path.isdir(script_folder):
                warnings.append(f"Script folder not found: {script_folder}")
            elif not same_path(script_folder, self._scripting_tab.script_folder):
                self._scripting_tab.set_script_folder(script_folder)

        # Try to connect (only if not already connected)
        if self._setup_tab.elf_file_path and not self._app_state.is_connected():
            self._on_connect_clicked()

        # Load tab configurations — support both Qt format (dicts-of-arrays) and
        # shared web format (list-of-dicts with "watch_view"/"scope_view" keys).
        raw_scope = config.get("scope_view", {})
        raw_watch = config.get("watch_view", {})

        # Convert shared list-of-dicts format → Qt dicts-of-arrays format
        if isinstance(raw_scope, list):
            sample_ctrl = config.get("sample_control", {})
            trigger_ctrl = config.get("trigger_control", {})
            trigger_edge_map = {0: "Falling", 1: "Rising"}
            trigger_mode_map = {0: "Disable", 1: "Enable"}
            # Map web hex colors to Qt color names
            hex_to_name = {
                "#FF0000": "Red", "#00FF00": "Green", "#0000FF": "Blue",
                "#FFFF00": "Yellow", "#00FFFF": "Cyan", "#FF00FF": "Magenta",
                "#800080": "Purple", "#CCCCCC": "White",  "#000000": "Black",
            }
            raw_scope = {
                "variables": [v.get("variable", "") for v in raw_scope],
                "trigger": [bool(v.get("trigger", False)) for v in raw_scope],
                "scale": [str(v.get("gain", v.get("scale", 1.0))) for v in raw_scope],
                "offset": [str(v.get("offset", 0.0)) for v in raw_scope],
                "color": [hex_to_name.get(v.get("color", "").upper(), v.get("color", "Red")) for v in raw_scope],
                "show": [bool(v.get("enable", True)) for v in raw_scope],
                "sfr": [bool(v.get("sfr", False)) for v in raw_scope],
                "sample_time_factor": str(sample_ctrl.get("sampleTime", 1)),
                "single_shot": sample_ctrl.get("triggerAction", "off") == "shot",
                "trigger_level": str(trigger_ctrl.get("trigger_level", 0)),
                "trigger_delay": str(int(trigger_ctrl.get("trigger_delay", 0))),
                "trigger_edge": trigger_edge_map.get(int(trigger_ctrl.get("trigger_edge", 1)), "Rising"),
                "trigger_mode": trigger_mode_map.get(int(trigger_ctrl.get("trigger_mode", 0)), "Disable"),
            }
        if isinstance(raw_watch, list):
            raw_watch = {
                "variables": [v.get("variable", "") for v in raw_watch],
                "types": [v.get("type", "") for v in raw_watch],
                "values": [str(v.get("value", "")) for v in raw_watch],
                "scaling": [str(v.get("scaling", 1.0)) for v in raw_watch],
                "offsets": [str(v.get("offset", 0.0)) for v in raw_watch],
                "units": [v.get("unit", "") for v in raw_watch],
                "live": [bool(v.get("live", False)) for v in raw_watch],
                "sfr": [bool(v.get("sfr", False)) for v in raw_watch],
            }

        self._scope_view_tab.load_config(raw_scope)
        self._watch_view_tab.load_config(raw_watch)

        # Load view mode and set toggle buttons
        view_mode = config.get("view_mode", "Both")
        if view_mode == "Both":
            self._watch_view_btn.setChecked(True)
            self._scope_view_btn.setChecked(True)
        elif view_mode == "WatchView":
            self._watch_view_btn.setChecked(True)
            self._scope_view_btn.setChecked(False)
        elif view_mode == "ScopeView":
            self._watch_view_btn.setChecked(False)
            self._scope_view_btn.setChecked(True)
        else:  # None
            self._watch_view_btn.setChecked(False)
            self._scope_view_btn.setChecked(False)
        self._on_view_toggle_changed()

        # Re-enable widgets after loading config (for dynamically created widgets)
        is_connected = self._app_state.is_connected()
        if is_connected:
            self._scope_view_tab.on_connection_changed(True)
            self._watch_view_tab.on_connection_changed(True)

            # Also ensure variable list is populated in tabs
            variables = self._app_state.get_variable_list()
            if variables:
                self._scope_view_tab.on_variable_list_updated(variables)
                self._watch_view_tab.on_variable_list_updated(variables)

        # Activate polling for any live checkboxes that were loaded as checked
        self._activate_loaded_polling()

        if is_connected:
            missing = self._find_missing_variables(raw_watch, raw_scope)
            if missing:
                warnings.append("Variables not found in the ELF file: " + ", ".join(missing))
            # The views now show this session: store it completely
            self._record_session()
        if warnings:
            self._show_warning("\n\n".join(warnings))

    def _find_missing_variables(self, watch_config: dict, scope_config: dict) -> list:
        """Return the loaded WatchView/ScopeView variables that the connected ELF file does not contain.

        Args:
            watch_config: WatchView configuration (dict of lists).
            scope_config: ScopeView configuration (dict of lists).

        Returns:
            list: The missing variable names, in load order, without duplicates.
        """
        known = set(self._app_state.get_variable_list() or [])
        missing = []
        for config in (watch_config, scope_config):
            sfrs = config.get("sfr", [])
            for i, name in enumerate(config.get("variables", [])):
                is_sfr = sfrs[i] if i < len(sfrs) else False
                # SFRs are not in the variable list; they are checked when they are read
                if name and not is_sfr and name not in known and name not in missing:
                    missing.append(name)
        return missing

    def _show_warning(self, message: str):
        """Show a warning message to the user."""
        logging.warning(message)
        QMessageBox.warning(self, "Warning", message)

    def _activate_loaded_polling(self):
        """Activate polling for any live checkboxes that were loaded as checked."""
        # WatchView tab - check live checkboxes
        for i, cb in enumerate(self._watch_view_tab._live_checkboxes):
            if cb.isChecked():
                self._data_poller.add_active_live_index(i)

    def _show_error(self, message: str):
        """Show error message to user."""
        logging.error(message)
        QMessageBox.critical(self, "Error", message)

    def _save_window_state(self):
        """Save window geometry and state to settings."""
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.setValue("window/splitter_sizes", self._view_splitter.sizes())
        self._settings.setValue("window/watch_view_checked", self._watch_view_btn.isChecked())
        self._settings.setValue("window/scope_view_checked", self._scope_view_btn.isChecked())
        self._settings.setValue("window/current_tab", self._tab_widget.currentIndex())

    def _restore_window_state(self):
        """Restore window geometry and state from settings."""
        # Restore window geometry
        geometry = self._settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Restore window state
        state = self._settings.value("window/state")
        if state:
            self.restoreState(state)

        # Restore splitter sizes
        splitter_sizes = self._settings.value("window/splitter_sizes")
        if splitter_sizes:
            # Convert to list of ints if needed
            if isinstance(splitter_sizes, list):
                sizes = [int(s) for s in splitter_sizes]
                self._view_splitter.setSizes(sizes)

        # Restore toggle button states
        watch_checked = self._settings.value("window/watch_view_checked", False, type=bool)
        scope_checked = self._settings.value("window/scope_view_checked", False, type=bool)
        self._watch_view_btn.setChecked(watch_checked)
        self._scope_view_btn.setChecked(scope_checked)
        self._on_view_toggle_changed()

        # Always start on Setup tab
        self._tab_widget.setCurrentIndex(0)

    def closeEvent(self, event):  # noqa: N802
        """Handle window close event."""
        # Offer to save the dashboard first; the user can cancel closing
        if not self._dashboard_tab.confirm_close():
            event.ignore()
            return

        # Save window state before closing
        self._save_window_state()

        # Stop data poller
        self._data_poller.stop()

        # Disconnect if connected, after storing the session
        if self._connection_manager.is_connected():
            self._record_session()
            self._connection_manager.disconnect()

        event.accept()


def execute_qt():
    """Entry point for the Qt application."""
    import sys

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    execute_qt()
