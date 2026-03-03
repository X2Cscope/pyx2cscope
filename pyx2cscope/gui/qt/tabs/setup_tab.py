"""Setup tab - Connection and device configuration."""

import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import QRegExp, QSettings, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator, QRegExpValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    - UART settings (Port, Baud Rate)
    - TCP/IP settings (IP Address, Port)
    - CAN settings (Bus Type, Channel, Baudrate, Mode, Tx-ID, Rx-ID)
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
        self._settings = QSettings("Microchip", "pyX2Cscope")

        # Device info labels
        self._device_info_labels = {}

        self._setup_ui()
        self._restore_connection_settings()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setLayout(main_layout)

        # Left side: Connection settings
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        # === Connection Settings Group (ELF file + Interface selection) ===
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

        # Connect button and loading indicator row
        connect_layout = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedSize(100, 30)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        connect_layout.addWidget(self._connect_btn)

        # Loading indicator (simple text label)
        self._loading_label = QLabel("Loading...")
        self._loading_label.setStyleSheet("color: #666; font-style: italic;")
        self._loading_label.hide()
        connect_layout.addWidget(self._loading_label)
        connect_layout.addStretch()

        connection_layout.addLayout(connect_layout, row, 1, 1, 2)

        self._connection_group = connection_group
        left_layout.addWidget(connection_group)

        # === UART Settings Group ===
        self._uart_group = QGroupBox("UART Settings")
        uart_layout = QGridLayout()
        uart_layout.setSpacing(8)
        uart_layout.setContentsMargins(10, 15, 10, 10)
        self._uart_group.setLayout(uart_layout)
        self._uart_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        uart_row = 0

        # Port
        uart_layout.addWidget(QLabel("Port:"), uart_row, 0, Qt.AlignRight)
        self._port_combo = QComboBox()
        self._port_combo.setFixedWidth(120)
        uart_layout.addWidget(self._port_combo, uart_row, 1)

        # Refresh button
        self._refresh_btn = QPushButton()
        self._refresh_btn.setFixedSize(25, 25)
        refresh_icon = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        if os.path.exists(refresh_icon):
            self._refresh_btn.setIcon(QIcon(refresh_icon))
        uart_layout.addWidget(self._refresh_btn, uart_row, 2)
        uart_row += 1

        # Baud Rate
        uart_layout.addWidget(QLabel("Baud Rate:"), uart_row, 0, Qt.AlignRight)
        self._baud_combo = QComboBox()
        self._baud_combo.setFixedWidth(120)
        self._baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        self._baud_combo.setCurrentText("115200")
        uart_layout.addWidget(self._baud_combo, uart_row, 1)

        left_layout.addWidget(self._uart_group)

        # === TCP/IP Settings Group ===
        self._tcp_group = QGroupBox("TCP/IP Settings")
        tcp_layout = QGridLayout()
        tcp_layout.setSpacing(8)
        tcp_layout.setContentsMargins(10, 15, 10, 10)
        self._tcp_group.setLayout(tcp_layout)
        self._tcp_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        tcp_row = 0

        # Host (IP address or hostname)
        tcp_layout.addWidget(QLabel("Host:"), tcp_row, 0, Qt.AlignRight)
        self._ip_edit = QLineEdit("192.168.0.100")
        self._ip_edit.setFixedWidth(120)
        self._ip_edit.setPlaceholderText("IP or hostname")
        # Validator for IP address or hostname (alphanumeric, dots, hyphens)
        host_regex = QRegExp(r"^[a-zA-Z0-9][a-zA-Z0-9.\-]*$")
        self._ip_edit.setValidator(QRegExpValidator(host_regex))
        tcp_layout.addWidget(self._ip_edit, tcp_row, 1)
        tcp_row += 1

        # Port (numbers only, 1-65535)
        tcp_layout.addWidget(QLabel("Port:"), tcp_row, 0, Qt.AlignRight)
        self._tcp_port_edit = QLineEdit("12666")
        self._tcp_port_edit.setFixedWidth(120)
        self._tcp_port_edit.setValidator(QIntValidator(1, 65535))
        tcp_layout.addWidget(self._tcp_port_edit, tcp_row, 1)

        left_layout.addWidget(self._tcp_group)

        # === CAN Settings Group ===
        self._can_group = QGroupBox("CAN Settings")
        can_layout = QGridLayout()
        can_layout.setSpacing(8)
        can_layout.setContentsMargins(10, 15, 10, 10)
        self._can_group.setLayout(can_layout)
        self._can_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        can_row = 0

        # Bus Type
        can_layout.addWidget(QLabel("Bus Type:"), can_row, 0, Qt.AlignRight)
        self._can_bus_type_combo = QComboBox()
        self._can_bus_type_combo.addItems(["USB", "LAN"])
        self._can_bus_type_combo.setFixedWidth(120)
        can_layout.addWidget(self._can_bus_type_combo, can_row, 1)
        can_row += 1

        # Channel (numbers only)
        can_layout.addWidget(QLabel("Channel:"), can_row, 0, Qt.AlignRight)
        self._can_channel_edit = QLineEdit("1")
        self._can_channel_edit.setFixedWidth(120)
        self._can_channel_edit.setValidator(QIntValidator(0, 255))
        can_layout.addWidget(self._can_channel_edit, can_row, 1)
        can_row += 1

        # Baudrate
        can_layout.addWidget(QLabel("Baudrate:"), can_row, 0, Qt.AlignRight)
        self._can_baudrate_combo = QComboBox()
        self._can_baudrate_combo.addItems(["125K", "250K", "500K", "1M"])
        self._can_baudrate_combo.setCurrentText("125K")
        self._can_baudrate_combo.setFixedWidth(120)
        can_layout.addWidget(self._can_baudrate_combo, can_row, 1)
        can_row += 1

        # Mode
        can_layout.addWidget(QLabel("Mode:"), can_row, 0, Qt.AlignRight)
        self._can_mode_combo = QComboBox()
        self._can_mode_combo.addItems(["Standard", "Extended"])
        self._can_mode_combo.setFixedWidth(120)
        can_layout.addWidget(self._can_mode_combo, can_row, 1)
        can_row += 1

        # Tx-ID (hex)
        can_layout.addWidget(QLabel("Tx-ID (hex):"), can_row, 0, Qt.AlignRight)
        self._can_tx_id_edit = QLineEdit("7F1")
        self._can_tx_id_edit.setFixedWidth(120)
        can_layout.addWidget(self._can_tx_id_edit, can_row, 1)
        can_row += 1

        # Rx-ID (hex)
        can_layout.addWidget(QLabel("Rx-ID (hex):"), can_row, 0, Qt.AlignRight)
        self._can_rx_id_edit = QLineEdit("7F0")
        self._can_rx_id_edit.setFixedWidth(120)
        can_layout.addWidget(self._can_rx_id_edit, can_row, 1)

        left_layout.addWidget(self._can_group)
        left_layout.addStretch()

        main_layout.addLayout(left_layout)

        # Add spacing between groups
        main_layout.addSpacing(20)

        # Right side: Device info (aligned to top)
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)

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

        right_layout.addWidget(device_group)
        right_layout.addStretch()

        main_layout.addLayout(right_layout)

        # Add stretch to push everything to the left
        main_layout.addStretch()

        # Set initial interface visibility
        self._on_interface_changed("UART")

    def _on_interface_changed(self, interface: str):
        """Handle interface selection change."""
        # Hide all interface settings groups
        self._uart_group.hide()
        self._tcp_group.hide()
        self._can_group.hide()

        # Show relevant group based on interface
        if interface == "UART":
            self._uart_group.show()
        elif interface == "TCP/IP":
            self._tcp_group.show()
        elif interface == "CAN":
            self._can_group.show()

    def _on_select_elf(self):
        """Handle ELF file selection."""
        # Get last directory from settings
        last_dir = self._settings.value("elf_file_dir", "", type=str)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ELF File",
            last_dir,
            "ELF Files (*.elf);;All Files (*.*)",
        )
        if file_path:
            self._elf_file_path = file_path
            # Save the directory for next time
            self._settings.setValue("elf_file_dir", os.path.dirname(file_path))
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
        # Hide loading label
        self._loading_label.hide()
        self._connect_btn.setEnabled(True)

        self._connect_btn.setText("Disconnect" if connected else "Connect")

        # Disable/enable interface selection and ELF button
        self._interface_combo.setEnabled(not connected)
        self._elf_button.setEnabled(not connected)

        # Disable/enable interface settings groups when connected
        self._uart_group.setEnabled(not connected)
        self._tcp_group.setEnabled(not connected)
        self._can_group.setEnabled(not connected)

    def set_loading(self, loading: bool):
        """Show or hide the loading indicator."""
        if loading:
            self._loading_label.show()
            self._connect_btn.setEnabled(False)
        else:
            self._loading_label.hide()
            self._connect_btn.setEnabled(True)

    def _on_connect_clicked(self):
        """Handle connect button click - show loading and emit signal."""
        self.set_loading(True)
        self.connect_requested.emit()

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
            params["tcp_port"] = self.tcp_port
        elif interface == "CAN":
            params["bus_type"] = self._can_bus_type_combo.currentText()
            params["channel"] = int(self._can_channel_edit.text())
            params["baudrate"] = self._can_baudrate_combo.currentText()
            params["mode"] = self._can_mode_combo.currentText()
            params["tx_id"] = self._can_tx_id_edit.text()
            params["rx_id"] = self._can_rx_id_edit.text()

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
            if "bus_type" in params:
                self._can_bus_type_combo.setCurrentText(params["bus_type"])
            if "channel" in params:
                self._can_channel_edit.setText(str(params["channel"]))
            if "baudrate" in params:
                self._can_baudrate_combo.setCurrentText(params["baudrate"])
            if "mode" in params:
                self._can_mode_combo.setCurrentText(params["mode"])
            if "tx_id" in params:
                self._can_tx_id_edit.setText(params["tx_id"])
            if "rx_id" in params:
                self._can_rx_id_edit.setText(params["rx_id"])

    def save_connection_settings(self):
        """Save current connection settings to persistent storage."""
        self._settings.setValue("connection/interface", self._interface_combo.currentText())

        # UART settings
        self._settings.setValue("connection/uart_baud", self._baud_combo.currentText())

        # TCP/IP settings
        self._settings.setValue("connection/tcp_host", self._ip_edit.text())
        self._settings.setValue("connection/tcp_port", self._tcp_port_edit.text())

        # CAN settings
        self._settings.setValue("connection/can_bus_type", self._can_bus_type_combo.currentText())
        self._settings.setValue("connection/can_channel", self._can_channel_edit.text())
        self._settings.setValue("connection/can_baudrate", self._can_baudrate_combo.currentText())
        self._settings.setValue("connection/can_mode", self._can_mode_combo.currentText())
        self._settings.setValue("connection/can_tx_id", self._can_tx_id_edit.text())
        self._settings.setValue("connection/can_rx_id", self._can_rx_id_edit.text())

    def _restore_connection_settings(self):
        """Restore connection settings from persistent storage."""
        # Restore interface type
        interface = self._settings.value("connection/interface", "UART", type=str)
        self.set_interface(interface)

        # Restore UART settings
        baud = self._settings.value("connection/uart_baud", "115200", type=str)
        self._baud_combo.setCurrentText(baud)

        # Restore TCP/IP settings
        host = self._settings.value("connection/tcp_host", "192.168.0.100", type=str)
        self._ip_edit.setText(host)
        tcp_port = self._settings.value("connection/tcp_port", "12666", type=str)
        self._tcp_port_edit.setText(tcp_port)

        # Restore CAN settings
        bus_type = self._settings.value("connection/can_bus_type", "USB", type=str)
        self._can_bus_type_combo.setCurrentText(bus_type)
        channel = self._settings.value("connection/can_channel", "1", type=str)
        self._can_channel_edit.setText(channel)
        baudrate = self._settings.value("connection/can_baudrate", "125K", type=str)
        self._can_baudrate_combo.setCurrentText(baudrate)
        mode = self._settings.value("connection/can_mode", "Standard", type=str)
        self._can_mode_combo.setCurrentText(mode)
        tx_id = self._settings.value("connection/can_tx_id", "7F1", type=str)
        self._can_tx_id_edit.setText(tx_id)
        rx_id = self._settings.value("connection/can_rx_id", "7F0", type=str)
        self._can_rx_id_edit.setText(rx_id)
