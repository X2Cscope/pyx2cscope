"""Setup tab - Connection and device configuration."""

import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui import img as img_src

if TYPE_CHECKING:
    from pyx2cscope.gui.qt.models.app_state import AppState


class SetupTab(QWidget):
    """Tab for connection and device setup.

    Features:
    - Interface selection (UART, TCP/IP, CAN)
    - COM port selection (UART)
    - IP address and port (TCP/IP)
    - Bus ID (CAN)
    - ELF file selection
    - Device info display
    """

    # Signals
    connect_requested = pyqtSignal()
    elf_file_selected = pyqtSignal(str)

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the Setup tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._elf_file_path = ""

        # Device info labels
        self._device_info_labels = {}

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setLayout(main_layout)

        # Left side: Connection settings
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QGridLayout()
        connection_layout.setSpacing(8)
        connection_layout.setContentsMargins(10, 15, 10, 10)
        connection_group.setLayout(connection_layout)
        connection_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        row = 0

        # ELF file selection
        connection_layout.addWidget(QLabel("ELF File:"), row, 0, Qt.AlignRight)
        self._elf_button = QPushButton("Select ELF file")
        self._elf_button.setFixedWidth(200)
        self._elf_button.clicked.connect(self._on_select_elf)
        connection_layout.addWidget(self._elf_button, row, 1, 1, 2)
        row += 1

        # Interface selection
        connection_layout.addWidget(QLabel("Interface:"), row, 0, Qt.AlignRight)
        self._interface_combo = QComboBox()
        self._interface_combo.addItems(["UART", "TCP/IP", "CAN"])
        self._interface_combo.setFixedWidth(120)
        self._interface_combo.currentTextChanged.connect(self._on_interface_changed)
        connection_layout.addWidget(self._interface_combo, row, 1)
        row += 1

        # === Connection parameter row (changes based on interface) ===
        # Label for connection param 1
        self._param1_label = QLabel("Port:")
        connection_layout.addWidget(self._param1_label, row, 0, Qt.AlignRight)

        # UART: Port combo
        self._port_combo = QComboBox()
        self._port_combo.setFixedWidth(120)
        connection_layout.addWidget(self._port_combo, row, 1)

        # TCP/IP: IP Address
        self._ip_edit = QLineEdit("192.168.1.100")
        self._ip_edit.setFixedWidth(120)
        self._ip_edit.setPlaceholderText("e.g., 192.168.1.100")
        connection_layout.addWidget(self._ip_edit, row, 1)

        # CAN: Bus ID
        self._can_bus_edit = QLineEdit("0")
        self._can_bus_edit.setFixedWidth(120)
        connection_layout.addWidget(self._can_bus_edit, row, 1)

        # Refresh button (UART only)
        self._refresh_btn = QPushButton()
        self._refresh_btn.setFixedSize(25, 25)
        refresh_icon = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        if os.path.exists(refresh_icon):
            self._refresh_btn.setIcon(QIcon(refresh_icon))
        connection_layout.addWidget(self._refresh_btn, row, 2)
        row += 1

        # === Connection parameter row 2 (for interfaces that need it) ===
        # Label for connection param 2
        self._param2_label = QLabel("Baud Rate:")
        connection_layout.addWidget(self._param2_label, row, 0, Qt.AlignRight)

        # UART: Baud rate combo
        self._baud_combo = QComboBox()
        self._baud_combo.setFixedWidth(120)
        self._baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        self._baud_combo.setCurrentText("115200")
        connection_layout.addWidget(self._baud_combo, row, 1)

        # TCP/IP: Port
        self._tcp_port_edit = QLineEdit("12666")
        self._tcp_port_edit.setFixedWidth(120)
        connection_layout.addWidget(self._tcp_port_edit, row, 1)
        row += 1

        # Connect button
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedSize(100, 30)
        self._connect_btn.clicked.connect(self.connect_requested.emit)
        connection_layout.addWidget(self._connect_btn, row, 1)

        main_layout.addWidget(connection_group)

        # Add spacing between groups
        main_layout.addSpacing(20)

        # Right side: Device info
        device_group = QGroupBox("Device Information")
        device_layout = QGridLayout()
        device_layout.setSpacing(5)
        device_layout.setContentsMargins(10, 15, 10, 10)
        device_group.setLayout(device_layout)
        device_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._device_info_labels = {
            "processor_id": QLabel("Not connected"),
            "uc_width": QLabel("Not connected"),
            "date": QLabel("Not connected"),
            "time": QLabel("Not connected"),
            "appVer": QLabel("Not connected"),
            "dsp_state": QLabel("Not connected"),
        }

        info_titles = {
            "processor_id": "Processor ID:",
            "uc_width": "UC Width:",
            "date": "Date:",
            "time": "Time:",
            "appVer": "App Version:",
            "dsp_state": "DSP State:",
        }

        for i, (key, label) in enumerate(self._device_info_labels.items()):
            title_label = QLabel(info_titles[key])
            title_label.setAlignment(Qt.AlignRight)
            device_layout.addWidget(title_label, i, 0, Qt.AlignRight)
            label.setMinimumWidth(150)
            device_layout.addWidget(label, i, 1, Qt.AlignLeft)

        main_layout.addWidget(device_group)

        # Add stretch to push everything to the left
        main_layout.addStretch()

        # Set initial interface visibility
        self._on_interface_changed("UART")

    def _on_interface_changed(self, interface: str):
        """Handle interface selection change."""
        # Hide all interface-specific widgets
        self._port_combo.hide()
        self._ip_edit.hide()
        self._can_bus_edit.hide()
        self._refresh_btn.hide()
        self._baud_combo.hide()
        self._tcp_port_edit.hide()
        self._param2_label.hide()

        # Show relevant widgets based on interface
        if interface == "UART":
            self._param1_label.setText("Port:")
            self._port_combo.show()
            self._refresh_btn.show()
            self._param2_label.setText("Baud Rate:")
            self._param2_label.show()
            self._baud_combo.show()
        elif interface == "TCP/IP":
            self._param1_label.setText("IP Address:")
            self._ip_edit.show()
            self._param2_label.setText("Port:")
            self._param2_label.show()
            self._tcp_port_edit.show()
        elif interface == "CAN":
            self._param1_label.setText("Bus ID:")
            self._can_bus_edit.show()
            # CAN has no second parameter

    def _on_select_elf(self):
        """Handle ELF file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ELF File",
            "",
            "ELF Files (*.elf);;All Files (*.*)",
        )
        if file_path:
            self._elf_file_path = file_path
            # Show shortened filename
            basename = os.path.basename(file_path)
            if len(basename) > 25:
                basename = basename[:22] + "..."
            self._elf_button.setText(basename)
            self._elf_button.setToolTip(file_path)
            self.elf_file_selected.emit(file_path)

    # Public properties and methods

    @property
    def interface_type(self) -> str:
        """Get the selected interface type."""
        return self._interface_combo.currentText()

    @property
    def port_combo(self) -> QComboBox:
        """Get the port combo box."""
        return self._port_combo

    @property
    def baud_combo(self) -> QComboBox:
        """Get the baud rate combo box."""
        return self._baud_combo

    @property
    def ip_address(self) -> str:
        """Get the IP address."""
        return self._ip_edit.text()

    @property
    def tcp_port(self) -> int:
        """Get the TCP port."""
        try:
            return int(self._tcp_port_edit.text())
        except ValueError:
            return 12666

    @property
    def can_bus_id(self) -> str:
        """Get the CAN bus ID."""
        return self._can_bus_edit.text()

    @property
    def connect_btn(self) -> QPushButton:
        """Get the connect button."""
        return self._connect_btn

    @property
    def refresh_btn(self) -> QPushButton:
        """Get the refresh button."""
        return self._refresh_btn

    @property
    def elf_file_path(self) -> str:
        """Get the selected ELF file path."""
        return self._elf_file_path

    @elf_file_path.setter
    def elf_file_path(self, path: str):
        """Set the ELF file path."""
        self._elf_file_path = path
        if path:
            basename = os.path.basename(path)
            if len(basename) > 25:
                basename = basename[:22] + "..."
            self._elf_button.setText(basename)
            self._elf_button.setToolTip(path)

    def set_ports(self, ports: list):
        """Set available COM ports."""
        self._port_combo.clear()
        self._port_combo.addItems(ports)

    def set_connected(self, connected: bool):
        """Update UI for connection state."""
        self._connect_btn.setText("Disconnect" if connected else "Connect")
        # Disable interface selection when connected
        self._interface_combo.setEnabled(not connected)
        self._elf_button.setEnabled(not connected)

    def update_device_info(self, device_info):
        """Update device info labels."""
        if device_info:
            self._device_info_labels["processor_id"].setText(device_info.processor_id)
            self._device_info_labels["uc_width"].setText(device_info.uc_width)
            self._device_info_labels["date"].setText(device_info.date)
            self._device_info_labels["time"].setText(device_info.time)
            self._device_info_labels["appVer"].setText(device_info.app_ver)
            self._device_info_labels["dsp_state"].setText(device_info.dsp_state)

    def clear_device_info(self):
        """Clear device info labels."""
        for label in self._device_info_labels.values():
            label.setText("Not connected")

    def get_connection_params(self) -> dict:
        """Get connection parameters based on selected interface."""
        interface = self.interface_type
        params = {"interface": interface}

        if interface == "UART":
            params["port"] = self._port_combo.currentText()
            params["baud_rate"] = int(self._baud_combo.currentText())
        elif interface == "TCP/IP":
            params["host"] = self._ip_edit.text()
            params["port"] = self.tcp_port
        elif interface == "CAN":
            params["bus"] = self._can_bus_edit.text()

        return params

    def set_interface(self, interface: str):
        """Set the interface type."""
        index = self._interface_combo.findText(interface)
        if index >= 0:
            self._interface_combo.setCurrentIndex(index)

    def set_connection_params(self, params: dict):
        """Set connection parameters from config."""
        interface = params.get("interface", "UART")
        self.set_interface(interface)

        if interface == "UART":
            if "baud_rate" in params:
                self._baud_combo.setCurrentText(str(params["baud_rate"]))
        elif interface == "TCP/IP":
            if "host" in params:
                self._ip_edit.setText(params["host"])
            if "port" in params:
                self._tcp_port_edit.setText(str(params["port"]))
        elif interface == "CAN":
            if "bus" in params:
                self._can_bus_edit.setText(params["bus"])
