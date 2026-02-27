"""WatchView tab (Tab3) - Dynamic watch variables without plotting."""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui.generic_gui.dialogs.variable_selection import VariableSelectionDialog
from pyx2cscope.gui.generic_gui.tabs.base_tab import BaseTab

if TYPE_CHECKING:
    from pyx2cscope.gui.generic_gui.models.app_state import AppState


class WatchViewTab(BaseTab):
    """Tab for dynamically adding/removing watch variables.

    Features:
    - Dynamic row addition/removal
    - Live polling for checked variables
    - Scaling and offset calculations
    - Scrollable interface for many variables
    """

    # Signal emitted when live polling state changes: (index, is_live)
    live_polling_changed = pyqtSignal(int, bool)

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the WatchView tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(app_state, parent)
        self._variable_list: List[str] = []
        self._current_row = 1

        # Widget lists for each row
        self._row_widgets: List[Tuple] = []
        self._live_checkboxes: List[QCheckBox] = []
        self._variable_edits: List[QLineEdit] = []
        self._value_edits: List[QLineEdit] = []
        self._scaling_edits: List[QLineEdit] = []
        self._offset_edits: List[QLineEdit] = []
        self._scaled_value_edits: List[QLineEdit] = []
        self._unit_edits: List[QLineEdit] = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Grid layout for variable rows
        self._grid_layout = QGridLayout()
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setVerticalSpacing(2)
        self._grid_layout.setHorizontalSpacing(5)
        scroll_layout.addLayout(self._grid_layout)

        # Headers
        headers = ["Live", "Variable", "Value", "Scaling", "Offset", "Scaled Value", "Unit", "Remove"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setAlignment(Qt.AlignCenter)
            label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self._grid_layout.addWidget(label, 0, col)

        # Set column stretch
        self._grid_layout.setColumnStretch(1, 5)  # Variable
        self._grid_layout.setColumnStretch(2, 2)  # Value
        self._grid_layout.setColumnStretch(3, 1)  # Scaling
        self._grid_layout.setColumnStretch(4, 1)  # Offset
        self._grid_layout.setColumnStretch(5, 1)  # Scaled Value
        self._grid_layout.setColumnStretch(6, 1)  # Unit

        # Add Variable button
        self._add_button = QPushButton("Add Variable")
        self._add_button.clicked.connect(self._add_variable_row)
        scroll_layout.addWidget(self._add_button)

        # Save/Load buttons
        button_layout = QHBoxLayout()
        self._save_button = QPushButton("Save Config")
        self._save_button.setFixedSize(100, 30)
        self._load_button = QPushButton("Load Config")
        self._load_button.setFixedSize(100, 30)
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(self._load_button)
        scroll_layout.addLayout(button_layout)

        # Add stretch to push content to top
        scroll_layout.addStretch()

        scroll_layout.setContentsMargins(0, 0, 0, 0)

    def on_connection_changed(self, connected: bool):
        """Handle connection state changes."""
        self._add_button.setEnabled(connected)
        for var_edit in self._variable_edits:
            var_edit.setEnabled(connected)

    def on_variable_list_updated(self, variables: list):
        """Handle variable list updates."""
        self._variable_list = variables

    def eventFilter(self, source, event):
        """Event filter to handle line edit click events for variable selection."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if isinstance(source, QLineEdit) and source in self._variable_edits:
                index = self._variable_edits.index(source)
                self._on_variable_click(index)
        return super().eventFilter(source, event)

    def _add_variable_row(self):
        """Add a new variable row to the grid."""
        row = self._current_row
        index = len(self._row_widgets)

        # Create widgets
        live_cb = QCheckBox()
        live_cb.stateChanged.connect(lambda state, idx=index: self._on_live_changed(idx, state))

        var_edit = QLineEdit()
        var_edit.setPlaceholderText("Search Variable")
        var_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        var_edit.installEventFilter(self)

        value_edit = QLineEdit()
        value_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_edit.editingFinished.connect(lambda idx=index: self._on_value_changed(idx))

        scaling_edit = QLineEdit("1")
        scaling_edit.editingFinished.connect(lambda idx=index: self._update_scaled_value(idx))

        offset_edit = QLineEdit("0")
        offset_edit.editingFinished.connect(lambda idx=index: self._update_scaled_value(idx))

        scaled_value_edit = QLineEdit()
        scaled_value_edit.setReadOnly(True)

        unit_edit = QLineEdit()

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, idx=index: self._remove_variable_row(idx))

        # Add to grid
        self._grid_layout.addWidget(live_cb, row, 0)
        self._grid_layout.addWidget(var_edit, row, 1)
        self._grid_layout.addWidget(value_edit, row, 2)
        self._grid_layout.addWidget(scaling_edit, row, 3)
        self._grid_layout.addWidget(offset_edit, row, 4)
        self._grid_layout.addWidget(scaled_value_edit, row, 5)
        self._grid_layout.addWidget(unit_edit, row, 6)
        self._grid_layout.addWidget(remove_btn, row, 7)

        # Track widgets
        widgets = (live_cb, var_edit, value_edit, scaling_edit, offset_edit, scaled_value_edit, unit_edit, remove_btn)
        self._row_widgets.append(widgets)
        self._live_checkboxes.append(live_cb)
        self._variable_edits.append(var_edit)
        self._value_edits.append(value_edit)
        self._scaling_edits.append(scaling_edit)
        self._offset_edits.append(offset_edit)
        self._scaled_value_edits.append(scaled_value_edit)
        self._unit_edits.append(unit_edit)

        # Add to app state
        self._app_state.add_live_watch_var()

        self._current_row += 1

        # Calculate initial scaled value
        self._update_scaled_value(index)

    def _remove_variable_row(self, index: int):
        """Remove a variable row from the grid."""
        if index >= len(self._row_widgets):
            return

        # Get widgets to remove
        widgets = self._row_widgets[index]

        # Remove from grid and delete
        for widget in widgets:
            self._grid_layout.removeWidget(widget)
            widget.deleteLater()

        # Remove from tracking lists
        self._row_widgets.pop(index)
        self._live_checkboxes.pop(index)
        self._variable_edits.pop(index)
        self._value_edits.pop(index)
        self._scaling_edits.pop(index)
        self._offset_edits.pop(index)
        self._scaled_value_edits.pop(index)
        self._unit_edits.pop(index)

        # Remove from app state
        self._app_state.remove_live_watch_var(index)

        self._current_row -= 1

        # Rearrange grid
        self._rearrange_grid()

    def _rearrange_grid(self):
        """Rearrange the grid after row removal."""
        # Remove all widgets from grid
        for i in reversed(range(self._grid_layout.count())):
            widget = self._grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Re-add headers
        headers = ["Live", "Variable", "Value", "Scaling", "Offset", "Scaled Value", "Unit", "Remove"]
        for col, header in enumerate(headers):
            self._grid_layout.addWidget(QLabel(header), 0, col)

        # Re-add rows
        for row, widgets in enumerate(self._row_widgets, start=1):
            for col, widget in enumerate(widgets):
                self._grid_layout.addWidget(widget, row, col)

        # Update remove button connections
        for i, widgets in enumerate(self._row_widgets):
            remove_btn = widgets[7]
            remove_btn.clicked.disconnect()
            remove_btn.clicked.connect(lambda checked, idx=i: self._remove_variable_row(idx))

    def _on_variable_click(self, index: int):
        """Handle click on variable field to open selection dialog."""
        if not self._variable_list or index >= len(self._variable_edits):
            return

        dialog = VariableSelectionDialog(self._variable_list, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_variable:
            self._variable_edits[index].setText(dialog.selected_variable)
            self._app_state.update_live_watch_var_field(index, "name", dialog.selected_variable)

            # Read initial value
            value = self._app_state.read_variable(dialog.selected_variable)
            if value is not None:
                self._value_edits[index].setText(str(value))
                self._app_state.update_live_watch_var_field(index, "value", value)
                self._update_scaled_value(index)

    def _on_live_changed(self, index: int, state: int):
        """Handle live checkbox state change."""
        if index >= len(self._live_checkboxes):
            return
        is_live = state == Qt.Checked
        self._app_state.update_live_watch_var_field(index, "live", is_live)
        # Emit signal to notify DataPoller
        self.live_polling_changed.emit(index, is_live)

    def _on_value_changed(self, index: int):
        """Handle value edit finished - write to device."""
        if index >= len(self._variable_edits):
            return

        var_name = self._variable_edits[index].text()
        if var_name and var_name != "None":
            try:
                value = float(self._value_edits[index].text())
                self._app_state.write_variable(var_name, value)
            except ValueError:
                pass

    def _update_scaled_value(self, index: int):
        """Update the scaled value for a variable."""
        if index >= len(self._value_edits):
            return

        try:
            value = self.safe_float(self._value_edits[index].text())
            scaling = self.safe_float(self._scaling_edits[index].text(), 1.0)
            offset = self.safe_float(self._offset_edits[index].text())
            scaled = self.calculate_scaled_value(value, scaling, offset)
            self._scaled_value_edits[index].setText(f"{scaled:.2f}")
        except Exception as e:
            logging.error(f"Error updating scaled value: {e}")
            self._scaled_value_edits[index].setText("0.00")

    @pyqtSlot(int, str, float)
    def on_live_var_updated(self, index: int, name: str, value: float):
        """Handle live variable update from data poller.

        Args:
            index: Variable index.
            name: Variable name.
            value: New value.
        """
        if index < len(self._value_edits):
            self._value_edits[index].setText(str(value))
            self._update_scaled_value(index)

    def clear_all_rows(self):
        """Clear all variable rows."""
        while self._row_widgets:
            self._remove_variable_row(0)

    def get_config(self) -> dict:
        """Get the current tab configuration."""
        return {
            "variables": [le.text() for le in self._variable_edits],
            "values": [ve.text() for ve in self._value_edits],
            "scaling": [sc.text() for sc in self._scaling_edits],
            "offsets": [off.text() for off in self._offset_edits],
            "scaled_values": [sv.text() for sv in self._scaled_value_edits],
            "live": [cb.isChecked() for cb in self._live_checkboxes],
        }

    def load_config(self, config: dict):
        """Load configuration into the tab."""
        # Clear existing rows
        self.clear_all_rows()

        # Add rows for each variable
        variables = config.get("variables", [])
        values = config.get("values", [])
        scalings = config.get("scaling", [])
        offsets = config.get("offsets", [])
        scaled_values = config.get("scaled_values", [])
        lives = config.get("live", [])

        for i, var in enumerate(variables):
            self._add_variable_row()
            if i < len(self._variable_edits):
                self._variable_edits[i].setText(var)
                # Update app state with variable name
                self._app_state.update_live_watch_var_field(i, "name", var)
            if i < len(values) and i < len(self._value_edits):
                self._value_edits[i].setText(values[i])
            if i < len(scalings) and i < len(self._scaling_edits):
                self._scaling_edits[i].setText(scalings[i])
            if i < len(offsets) and i < len(self._offset_edits):
                self._offset_edits[i].setText(offsets[i])
            if i < len(scaled_values) and i < len(self._scaled_value_edits):
                self._scaled_value_edits[i].setText(scaled_values[i])
            if i < len(lives) and i < len(self._live_checkboxes):
                self._live_checkboxes[i].setChecked(lives[i])
                # Update app state with live state
                self._app_state.update_live_watch_var_field(i, "live", lives[i])

    @property
    def save_button(self) -> QPushButton:
        """Get the save button."""
        return self._save_button

    @property
    def load_button(self) -> QPushButton:
        """Get the load button."""
        return self._load_button

    @property
    def row_count(self) -> int:
        """Get the number of variable rows."""
        return len(self._row_widgets)
