"""Connection management for the X2CScope device."""

import logging

import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal

from pyx2cscope.x2cscope import X2CScope


class ConnectionManager(QObject):
    """Manages X2CScope connection to the device.

    Handles connecting/disconnecting, port enumeration, and
    X2CScope initialization. The serial connection is managed
    internally by X2CScope.

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

    def connect(self, port: str, baud_rate: int, elf_file: str) -> bool:
        """Connect to the device.

        Args:
            port: COM port name.
            baud_rate: Baud rate for serial communication.
            elf_file: Path to the ELF file for variable information.

        Returns:
            True if connection successful, False otherwise.
        """
        if self._app_state.is_connected():
            logging.warning("Already connected. Disconnect first.")
            return False

        if not elf_file:
            self.error_occurred.emit("No ELF file selected.")
            return False

        try:
            # Initialize X2CScope (handles serial connection internally)
            x2cscope = X2CScope(
                port=port,
                elf_file=elf_file,
                baud_rate=baud_rate,
            )

            # Update app state
            self._app_state.port = port
            self._app_state.baud_rate = baud_rate
            self._app_state.elf_file = elf_file
            self._app_state.set_x2cscope(x2cscope)

            logging.info(f"Connected to {port} at {baud_rate} baud")
            self.connection_changed.emit(True)
            return True

        except Exception as e:
            error_msg = f"Connection error: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._app_state.set_x2cscope(None)
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

    def toggle_connection(
        self, port: str, baud_rate: int, elf_file: str
    ) -> bool:
        """Toggle the connection state.

        Args:
            port: COM port name.
            baud_rate: Baud rate for serial communication.
            elf_file: Path to the ELF file.

        Returns:
            True if now connected, False if now disconnected.
        """
        if self.is_connected():
            self.disconnect()
            return False
        else:
            return self.connect(port, baud_rate, elf_file)
