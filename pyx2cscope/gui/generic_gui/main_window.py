"""Main window for the generic GUI application."""

import logging
import os

from PyQt5 import QtGui
from PyQt5.QtCore import QFileInfo, QSettings, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyleFactory,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui import img as img_src
from pyx2cscope.gui.generic_gui.controllers.config_manager import ConfigManager
from pyx2cscope.gui.generic_gui.controllers.connection_manager import ConnectionManager
from pyx2cscope.gui.generic_gui.models.app_state import AppState
from pyx2cscope.gui.generic_gui.tabs.scope_view_tab import ScopeViewTab
from pyx2cscope.gui.generic_gui.tabs.watch_plot_tab import WatchPlotTab
from pyx2cscope.gui.generic_gui.tabs.watch_view_tab import WatchViewTab
from pyx2cscope.gui.generic_gui.workers.data_poller import DataPoller


class MainWindow(QMainWindow):
    """Main application window for pyX2Cscope GUI.

    Orchestrates all components:
    - Connection management
    - Data polling worker
    - Tab widgets for different views
    - Configuration save/load
    """

    def __init__(self, parent=None):
        """Initialize the main window."""
        super().__init__(parent)

        # Initialize settings
        self._settings = QSettings("Microchip", "pyX2Cscope")

        # Initialize app state
        self._app_state = AppState(self)

        # Initialize controllers
        self._connection_manager = ConnectionManager(self._app_state, self)
        self._config_manager = ConfigManager(self)

        # Initialize data poller (but don't start yet)
        self._data_poller = DataPoller(self._app_state, self)

        # Device info labels
        self._device_info_labels = {}

        # Setup UI
        self._setup_ui()
        self._setup_connections()

        # Start data poller thread
        self._data_poller.start()

        # Refresh ports on startup
        self._refresh_ports()

    def _setup_ui(self):
        """Set up the user interface."""
        QApplication.setStyle(QStyleFactory.create("Fusion"))

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tabs
        self._tab_widget = QTabWidget()
        main_layout.addWidget(self._tab_widget)

        # Tab 1: Setup (formerly WatchPlot)
        self._watch_plot_tab = WatchPlotTab(self._app_state, self)
        self._tab_widget.addTab(self._watch_plot_tab, "Setup")

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

        top_bar_layout.addStretch()

        # Save/Load buttons
        self._save_button = QPushButton("Save Config")
        self._save_button.setFixedSize(100, 28)
        self._save_button.clicked.connect(self._save_config)
        self._load_button = QPushButton("Load Config")
        self._load_button.setFixedSize(100, 28)
        self._load_button.clicked.connect(self._load_config)
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

        # Set initial view (Both selected)
        self._on_view_toggle_changed()

        # Add connection controls to Setup tab (top of layout)
        self._add_connection_controls()

        # Window properties
        self.setWindowTitle("pyX2Cscope")
        icon_path = os.path.join(os.path.dirname(img_src.__file__), "pyx2cscope.jpg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Restore window state from settings
        self._restore_window_state()

    def _add_connection_controls(self):
        """Add connection controls to the top of the WatchPlot tab."""
        # Get the WatchPlot tab's layout
        watch_layout = self._watch_plot_tab.layout()

        # Create connection controls widget
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Device info section (left)
        device_info_layout = QGridLayout()
        self._device_info_labels = {
            "processor_id": QLabel("Loading Processor ID..."),
            "uc_width": QLabel("Loading UC Width..."),
            "date": QLabel("Loading Date..."),
            "time": QLabel("Loading Time..."),
            "appVer": QLabel("Loading App Version..."),
            "dsp_state": QLabel("Loading DSP State..."),
        }

        for i, (key, label) in enumerate(self._device_info_labels.items()):
            info_label = QLabel(key.replace("_", " ").capitalize() + ":")
            info_label.setAlignment(Qt.AlignLeft)
            device_info_layout.addWidget(info_label, i, 0, Qt.AlignRight)
            device_info_layout.addWidget(label, i, 1, Qt.AlignLeft)

        controls_layout.addLayout(device_info_layout)

        # Connection settings section (right)
        settings_layout = QGridLayout()

        # Port selection
        settings_layout.addWidget(QLabel("Select Port:"), 0, 0, Qt.AlignRight)
        self._port_combo = QComboBox()
        self._port_combo.setFixedSize(100, 25)
        settings_layout.addWidget(self._port_combo, 0, 1)

        # Refresh button
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(25, 25)
        refresh_icon = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        if os.path.exists(refresh_icon):
            refresh_btn.setIcon(QIcon(refresh_icon))
        refresh_btn.clicked.connect(self._refresh_ports)
        settings_layout.addWidget(refresh_btn, 0, 2)

        # Baud rate selection
        settings_layout.addWidget(QLabel("Select Baud Rate:"), 1, 0, Qt.AlignRight)
        self._baud_combo = QComboBox()
        self._baud_combo.setFixedSize(100, 25)
        self._baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        self._baud_combo.setCurrentText("115200")
        settings_layout.addWidget(self._baud_combo, 1, 1)

        # Sample time for WatchPlot
        settings_layout.addWidget(QLabel("Sample Time WatchPlot:"), 2, 0, Qt.AlignRight)
        self._sampletime_edit = QLineEdit("500")
        self._sampletime_edit.setFixedSize(100, 30)
        self._sampletime_edit.editingFinished.connect(self._on_sampletime_changed)
        settings_layout.addWidget(self._sampletime_edit, 2, 1)
        settings_layout.addWidget(QLabel("ms"), 2, 2)

        # Connect button
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedSize(100, 30)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        settings_layout.addWidget(self._connect_btn, 3, 1)

        controls_layout.addLayout(settings_layout)

        # ELF file selection
        elf_layout = QHBoxLayout()
        self._elf_button = QPushButton("Select elf file")
        self._elf_button.clicked.connect(self._on_select_elf)
        elf_layout.addWidget(self._elf_button)

        # Insert controls at the top of WatchPlot tab
        watch_layout.insertWidget(0, controls_widget)
        watch_layout.insertLayout(1, elf_layout)

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
        self._data_poller.watch_var_updated.connect(self._watch_plot_tab.on_watch_var_updated)
        self._data_poller.plot_data_ready.connect(self._watch_plot_tab.on_plot_data_ready)
        self._data_poller.scope_data_ready.connect(self._scope_view_tab.on_scope_data_ready)
        self._data_poller.live_var_updated.connect(self._watch_view_tab.on_live_var_updated)
        self._data_poller.error_occurred.connect(self._show_error)

        # Config manager signals
        self._config_manager.error_occurred.connect(self._show_error)

        # Tab polling control signals -> DataPoller
        self._watch_plot_tab.live_polling_changed.connect(self._on_watch_live_changed)
        self._scope_view_tab.scope_sampling_changed.connect(self._on_scope_sampling_changed)
        self._watch_view_tab.live_polling_changed.connect(self._on_live_watch_changed)

    def _refresh_ports(self):
        """Refresh available COM ports."""
        self._connection_manager.refresh_ports()

    def _on_ports_refreshed(self, ports: list):
        """Handle ports refreshed signal."""
        self._port_combo.clear()
        self._port_combo.addItems(ports)

    def _on_select_elf(self):
        """Handle ELF file selection."""
        file_path = self._config_manager.prompt_for_elf_file()
        if file_path:
            self._elf_file_path = file_path
            self._elf_button.setText(QFileInfo(file_path).fileName())
            self._settings.setValue("elf_file_path", file_path)

    def _on_connect_clicked(self):
        """Handle connect button click."""
        if not hasattr(self, "_elf_file_path") or not self._elf_file_path:
            # Try to load from settings
            self._elf_file_path = self._settings.value("elf_file_path", "", type=str)

        if not self._elf_file_path:
            self._show_error("Please select an ELF file first.")
            return

        port = self._port_combo.currentText()
        baud_rate = int(self._baud_combo.currentText())

        connected = self._connection_manager.toggle_connection(
            port, baud_rate, self._elf_file_path
        )

        if connected:
            self._connect_btn.setText("Disconnect")
            self._update_device_info()
        else:
            self._connect_btn.setText("Connect")

    def _on_connection_changed(self, connected: bool):
        """Handle connection state change."""
        self._connect_btn.setText("Disconnect" if connected else "Connect")

        # Update tabs
        self._watch_plot_tab.on_connection_changed(connected)
        self._scope_view_tab.on_connection_changed(connected)
        self._watch_view_tab.on_connection_changed(connected)

        if connected:
            self._update_device_info()
        else:
            self._clear_device_info()

    def _on_variable_list_updated(self, variables: list):
        """Handle variable list update."""
        self._watch_plot_tab.on_variable_list_updated(variables)
        self._scope_view_tab.on_variable_list_updated(variables)
        self._watch_view_tab.on_variable_list_updated(variables)

    def _on_sampletime_changed(self):
        """Handle sample time change."""
        try:
            interval = int(self._sampletime_edit.text())
            self._data_poller.set_watch_interval(interval)
            self._data_poller.set_live_interval(interval)
        except ValueError:
            pass

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

    def _on_watch_live_changed(self, index: int, is_live: bool):
        """Handle watch variable live polling state change (Tab1)."""
        if is_live:
            self._data_poller.add_active_watch_index(index)
        else:
            self._data_poller.remove_active_watch_index(index)

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
        if device_info:
            self._device_info_labels["processor_id"].setText(device_info.processor_id)
            self._device_info_labels["uc_width"].setText(device_info.uc_width)
            self._device_info_labels["date"].setText(device_info.date)
            self._device_info_labels["time"].setText(device_info.time)
            self._device_info_labels["appVer"].setText(device_info.app_ver)
            self._device_info_labels["dsp_state"].setText(device_info.dsp_state)

    def _clear_device_info(self):
        """Clear device info labels."""
        for label in self._device_info_labels.values():
            label.setText("Not connected")

    def _save_config(self):
        """Save current configuration."""
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

        config = ConfigManager.build_config(
            elf_file=getattr(self, "_elf_file_path", ""),
            com_port=self._port_combo.currentText(),
            baud_rate=self._baud_combo.currentText(),
            watch_view=self._watch_plot_tab.get_config(),
            scope_view=self._scope_view_tab.get_config(),
            tab3_view=self._watch_view_tab.get_config(),
            view_mode=view_mode,
        )
        self._config_manager.save_config(config)

    def _load_config(self):
        """Load configuration from file."""
        config = self._config_manager.load_config()
        if not config:
            return

        # Load ELF file
        elf_path = config.get("elf_file", "")
        if elf_path:
            if self._config_manager.validate_elf_file(elf_path):
                self._elf_file_path = elf_path
                self._elf_button.setText(QFileInfo(elf_path).fileName())
            else:
                self._config_manager.show_file_not_found_warning(elf_path)
                new_path = self._config_manager.prompt_for_elf_file()
                if new_path:
                    self._elf_file_path = new_path
                    self._elf_button.setText(QFileInfo(new_path).fileName())

        # Load connection settings
        self._baud_combo.setCurrentText(config.get("baud_rate", "115200"))

        # Try to connect (only if not already connected)
        com_port = config.get("com_port", "")
        if com_port and com_port in [self._port_combo.itemText(i) for i in range(self._port_combo.count())]:
            self._port_combo.setCurrentText(com_port)
            if hasattr(self, "_elf_file_path") and self._elf_file_path:
                # Only connect if not already connected to avoid toggle disconnect
                if not self._app_state.is_connected():
                    self._on_connect_clicked()

        # Load tab configurations
        self._watch_plot_tab.load_config(config.get("watch_view", {}))
        self._scope_view_tab.load_config(config.get("scope_view", {}))
        self._watch_view_tab.load_config(config.get("tab3_view", {}))

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
            self._watch_plot_tab.on_connection_changed(True)
            self._scope_view_tab.on_connection_changed(True)
            self._watch_view_tab.on_connection_changed(True)

            # Also ensure variable list is populated in tabs
            variables = self._app_state.get_variable_list()
            if variables:
                self._watch_plot_tab.on_variable_list_updated(variables)
                self._scope_view_tab.on_variable_list_updated(variables)
                self._watch_view_tab.on_variable_list_updated(variables)

        # Activate polling for any live checkboxes that were loaded as checked
        self._activate_loaded_polling()

    def _activate_loaded_polling(self):
        """Activate polling for any live checkboxes that were loaded as checked."""
        # WatchPlot tab (Tab1) - check live checkboxes
        for i, cb in enumerate(self._watch_plot_tab._live_checkboxes):
            if cb.isChecked():
                self._data_poller.add_active_watch_index(i)

        # WatchView tab (Tab3) - check live checkboxes
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

        # Restore current tab
        current_tab = self._settings.value("window/current_tab", 0, type=int)
        self._tab_widget.setCurrentIndex(current_tab)

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state before closing
        self._save_window_state()

        # Stop data poller
        self._data_poller.stop()

        # Disconnect if connected
        if self._connection_manager.is_connected():
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
