"""Base tab class for the Qt GUI tabs."""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QWidget

if TYPE_CHECKING:
    from pyx2cscope.gui.qt.models.app_state import AppState


class BaseTab(QWidget):
    """Base class for all tab widgets.

    Provides common functionality and access to shared resources.
    """

    # Common colors for plots
    PLOT_COLORS = ["b", "g", "r", "c", "m", "y", "k"]

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the base tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._setup_validators()

    def _setup_validators(self):
        """Set up input validators."""
        decimal_regex = QRegExp(r"-?[0-9]+(\.[0-9]+)?")
        self._decimal_validator = QRegExpValidator(decimal_regex)

    @property
    def app_state(self) -> "AppState":
        """Get the application state."""
        return self._app_state

    @property
    def decimal_validator(self) -> QRegExpValidator:
        """Get the decimal number validator."""
        return self._decimal_validator

    def on_connection_changed(self, connected: bool):
        """Handle connection state changes.

        Override in subclasses to update UI based on connection state.

        Args:
            connected: True if connected, False otherwise.
        """
        pass

    def on_variable_list_updated(self, variables: list):
        """Handle variable list updates.

        Override in subclasses to update UI when variables change.

        Args:
            variables: List of available variable names.
        """
        pass

    def calculate_scaled_value(
        self, value: float, scaling: float, offset: float
    ) -> float:
        """Calculate a scaled value.

        Args:
            value: The raw value.
            scaling: The scaling factor.
            offset: The offset to add.

        Returns:
            The scaled value: (value * scaling) + offset
        """
        return (value * scaling) + offset

    def safe_float(self, text: str, default: float = 0.0) -> float:
        """Safely convert text to float.

        Args:
            text: The text to convert.
            default: Default value if conversion fails.

        Returns:
            The converted float or default value.
        """
        try:
            return float(text) if text else default
        except ValueError:
            return default

    def safe_int(self, text: str, default: int = 0) -> int:
        """Safely convert text to int.

        Args:
            text: The text to convert.
            default: Default value if conversion fails.

        Returns:
            The converted int or default value.
        """
        try:
            return int(text) if text else default
        except ValueError:
            return default
