"""Connection management for the X2CScope device."""

import logging

import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal

from pyx2cscope.x2cscope import X2CScope


class ConnectionManager(QObject):
    """Manages X2CScope connection to the device.

    Handles connecting/disconnecting, port enumeration, and
    X2CScope initialization. Supports multiple interface types:
    - UART (Serial)
    - TCP/IP
    - CAN

    Signals:
        connection_changed: Emitted when connection state changes.
            Args: (connected: bool)
        error_occurred: Emitted when a connection error occurs.
            Args: (message: str)
        ports_refreshed: Emitted when available ports are updated.
            Args: (ports: list)
    """

    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    ports_refreshed = pyqtSignal(list)

    def __init__(self, app_state, parent=None):
        """Initialize the connection manager.

        Args:
            app_state: The centralized AppState instance.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._app_state = app_state

    def refresh_ports(self) -> list:
        """Refresh and return list of available COM ports."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.ports_refreshed.emit(ports)
        return ports

    def connect_uart(self, port: str, baud_rate: int, elf_file: str) -> bool:
        """Connect to the device via UART.

        Args:
            port: COM port name.
            baud_rate: Baud rate for serial communication.
            elf_file: Path to the ELF file for variable information.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            x2cscope = X2CScope(
                port=port,
                elf_file=elf_file,
                baud_rate=baud_rate,
            )

            self._app_state.port = port
            self._app_state.baud_rate = baud_rate
            self._app_state.elf_file = elf_file
            self._app_state.set_x2cscope(x2cscope)

            logging.info(f"Connected via UART to {port} at {baud_rate} baud")
            self.connection_changed.emit(True)
            return True

        except Exception as e:
            error_msg = f"UART connection error: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._app_state.set_x2cscope(None)
            return False

    def connect_tcp(self, host: str, port: int, elf_file: str) -> bool:
        """Connect to the device via TCP/IP.

        Args:
            host: IP address of the target.
            port: TCP port number.
            elf_file: Path to the ELF file for variable information.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            x2cscope = X2CScope(
                host=host,
                port=port,
                elf_file=elf_file,
            )

            self._app_state.elf_file = elf_file
            self._app_state.set_x2cscope(x2cscope)

            logging.info(f"Connected via TCP/IP to {host}:{port}")
            self.connection_changed.emit(True)
            return True

        except Exception as e:
            error_msg = f"TCP/IP connection error: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._app_state.set_x2cscope(None)
            return False

    def connect_can(self, bus: str, elf_file: str) -> bool:
        """Connect to the device via CAN.

        Args:
            bus: CAN bus identifier.
            elf_file: Path to the ELF file for variable information.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            x2cscope = X2CScope(
                bus=bus,
                elf_file=elf_file,
            )

            self._app_state.elf_file = elf_file
            self._app_state.set_x2cscope(x2cscope)

            logging.info(f"Connected via CAN on bus {bus}")
            self.connection_changed.emit(True)
            return True

        except Exception as e:
            error_msg = f"CAN connection error: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._app_state.set_x2cscope(None)
            return False

    def connect(self, elf_file: str, **params) -> bool:
        """Connect to the device using specified interface parameters.

        Args:
            elf_file: Path to the ELF file for variable information.
            **params: Interface-specific parameters:
                - interface: "UART", "TCP/IP", or "CAN"
                - UART: port, baud_rate
                - TCP/IP: host, port
                - CAN: bus

        Returns:
            True if connection successful, False otherwise.
        """
        if self._app_state.is_connected():
            logging.warning("Already connected. Disconnect first.")
            return False

        if not elf_file:
            self.error_occurred.emit("No ELF file selected.")
            return False

        interface = params.get("interface", "UART")

        if interface == "UART":
            port = params.get("port", "")
            baud_rate = params.get("baud_rate", 115200)
            return self.connect_uart(port, baud_rate, elf_file)
        elif interface == "TCP/IP":
            host = params.get("host", "localhost")
            port = params.get("port", 12666)
            return self.connect_tcp(host, port, elf_file)
        elif interface == "CAN":
            bus = params.get("bus", "0")
            return self.connect_can(bus, elf_file)
        else:
            self.error_occurred.emit(f"Unknown interface type: {interface}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the device.

        Returns:
            True if disconnection successful, False otherwise.
        """
        try:
            # X2CScope handles closing the serial connection
            self._app_state.set_x2cscope(None)
            logging.info("Disconnected from device")
            self.connection_changed.emit(False)
            return True
        except Exception as e:
            error_msg = f"Disconnection error: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to device."""
        return self._app_state.is_connected()

    def toggle_connection(self, elf_file: str, **params) -> bool:
        """Toggle the connection state.

        Args:
            elf_file: Path to the ELF file.
            **params: Interface-specific connection parameters.

        Returns:
            True if now connected, False if now disconnected.
        """
        if self.is_connected():
            self.disconnect()
            return False
        else:
            return self.connect(elf_file, **params)
