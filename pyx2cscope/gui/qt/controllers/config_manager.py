"""Configuration management for saving and loading GUI state."""

import json
import logging
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget


class ConfigManager(QObject):
    """Manages saving and loading of configuration files.

    Handles serialization/deserialization of:
    - Connection settings (port, baud rate, ELF file)
    - WatchPlot variables (Tab1)
    - ScopeView settings (Tab2)
    - WatchView variables (Tab3)

    Signals:
        config_loaded: Emitted when a config is successfully loaded.
            Args: (config: dict)
        config_saved: Emitted when a config is successfully saved.
            Args: (file_path: str)
        error_occurred: Emitted when an error occurs.
            Args: (message: str)
    """

    config_loaded = pyqtSignal(dict)
    config_saved = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the config manager.

        Args:
            parent: Parent widget for dialogs.
        """
        super().__init__(parent)
        self._parent = parent
        self._settings = QSettings("Microchip", "pyX2Cscope")

    def save_config(self, config: Dict[str, Any], file_path: Optional[str] = None) -> bool:
        """Save configuration to a JSON file.

        Args:
            config: Configuration dictionary to save.
            file_path: Optional path to save to. If None, prompts user.

        Returns:
            True if save successful, False otherwise.
        """
        try:
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(
                    self._parent,
                    "Save Configuration",
                    "",
                    "JSON Files (*.json)",
                )

            if not file_path:
                return False

            with open(file_path, "w") as f:
                json.dump(config, f, indent=4)

            logging.info(f"Configuration saved to {file_path}")
            self.config_saved.emit(file_path)
            return True

        except Exception as e:
            error_msg = f"Error saving configuration: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def load_config(self, file_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load configuration from a JSON file.

        Args:
            file_path: Optional path to load from. If None, prompts user.

        Returns:
            Configuration dictionary if successful, None otherwise.
        """
        try:
            if not file_path:
                file_path, _ = QFileDialog.getOpenFileName(
                    self._parent,
                    "Load Configuration",
                    "",
                    "JSON Files (*.json)",
                )

            if not file_path:
                return None

            with open(file_path, "r") as f:
                config = json.load(f)

            logging.info(f"Configuration loaded from {file_path}")
            self.config_loaded.emit(config)
            return config

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error loading configuration: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None

    def validate_elf_file(self, elf_path: str) -> bool:
        """Validate that an ELF file exists.

        Args:
            elf_path: Path to the ELF file.

        Returns:
            True if file exists, False otherwise.
        """
        if not elf_path:
            return False
        return os.path.exists(elf_path)

    def prompt_for_elf_file(self) -> Optional[str]:
        """Prompt user to select an ELF file.

        Returns:
            Selected file path, or None if cancelled.
        """
        # Get last used directory from settings
        last_dir = self._settings.value("last_elf_directory", "", type=str)

        file_path, _ = QFileDialog.getOpenFileName(
            self._parent,
            "Select ELF File",
            last_dir,
            "ELF Files (*.elf);;All Files (*)",
        )

        if file_path:
            # Save the directory for next time
            self._settings.setValue("last_elf_directory", os.path.dirname(file_path))

        return file_path if file_path else None

    def show_file_not_found_warning(self, file_path: str):
        """Show a warning dialog for missing ELF file.

        Args:
            file_path: The path that was not found.
        """
        QMessageBox.warning(
            self._parent,
            "File Not Found",
            f"The ELF file '{file_path}' does not exist.\n\n"
            "Please select a valid ELF file.",
        )

    @staticmethod
    def build_config(
        elf_file: str,
        connection: Dict[str, Any],
        scope_view: Dict[str, Any],
        tab3_view: Dict[str, Any],
        view_mode: str = "Both",
    ) -> Dict[str, Any]:
        """Build a configuration dictionary from component data.

        Args:
            elf_file: Path to the ELF file.
            connection: Connection parameters (interface type, port, etc.).
            scope_view: ScopeView tab configuration.
            tab3_view: WatchView tab configuration.
            view_mode: Monitor view mode (WatchView, ScopeView, Both, None).

        Returns:
            Complete configuration dictionary.
        """
        return {
            "elf_file": elf_file,
            "connection": connection,
            "scope_view": scope_view,
            "tab3_view": tab3_view,
            "view_mode": view_mode,
        }
