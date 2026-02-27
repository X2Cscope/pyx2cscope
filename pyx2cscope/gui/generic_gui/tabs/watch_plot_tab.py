"""WatchPlot tab (Tab1) - Watch variables with plotting capability."""

import logging
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
)

from pyx2cscope.gui.generic_gui.dialogs.variable_selection import VariableSelectionDialog
from pyx2cscope.gui.generic_gui.tabs.base_tab import BaseTab

if TYPE_CHECKING:
    from pyx2cscope.gui.generic_gui.models.app_state import AppState


class WatchPlotTab(BaseTab):
    """Tab for watching variables and plotting their values over time.

    Features:
    - 5 watch variable slots with live polling
    - Scaling and offset for each variable
    - Real-time plotting with pyqtgraph
    - Slider control for first variable
    """

    # Signal emitted when live polling state changes: (index, is_live)
    live_polling_changed = pyqtSignal(int, bool)

    MAX_VARS = 5
    PLOT_DATA_MAXLEN = 250

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the WatchPlot tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(app_state, parent)
        self._variable_list: List[str] = []
        self._plot_data: deque = deque(maxlen=self.PLOT_DATA_MAXLEN)

        # Widget lists
        self._live_checkboxes: List[QCheckBox] = []
        self._line_edits: List[QLineEdit] = []
        self._value_edits: List[QLineEdit] = []
        self._scaling_edits: List[QLineEdit] = []
        self._offset_edits: List[QLineEdit] = []
        self._scaled_value_edits: List[QLineEdit] = []
        self._unit_edits: List[QLineEdit] = []
        self._plot_checkboxes: List[QCheckBox] = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Grid layout for variables
        grid_layout = QGridLayout()
        layout.addLayout(grid_layout)

        # Add header labels
        headers = ["Live", "Variable", "Value", "Scaling", "Offset", "Scaled Value", "Unit", "Plot"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setAlignment(Qt.AlignCenter)
            grid_layout.addWidget(label, 0, col)

        # Slider for first variable
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(-32768)
        self._slider.setMaximum(32767)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self._on_slider_changed)

        # Create variable rows
        for i in range(self.MAX_VARS):
            row = i + 1
            display_row = row if row == 1 else row + 1  # Leave space for slider after row 1

            # Live checkbox
            live_cb = QCheckBox()
            live_cb.setEnabled(False)
            live_cb.stateChanged.connect(lambda state, idx=i: self._on_live_changed(idx, state))
            self._live_checkboxes.append(live_cb)
            grid_layout.addWidget(live_cb, display_row, 0)

            # Variable name (read-only line edit for search dialog)
            line_edit = QLineEdit()
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Search Variable")
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            line_edit.setEnabled(False)
            line_edit.installEventFilter(self)
            self._line_edits.append(line_edit)
            grid_layout.addWidget(line_edit, display_row, 1)

            # Value edit
            value_edit = QLineEdit("0")
            value_edit.setValidator(self.decimal_validator)
            value_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            value_edit.editingFinished.connect(lambda idx=i: self._on_value_changed(idx))
            value_edit.textChanged.connect(lambda text, idx=i: self._update_scaled_value(idx))
            self._value_edits.append(value_edit)
            grid_layout.addWidget(value_edit, display_row, 2)

            # Scaling edit
            scaling_edit = QLineEdit("1")
            scaling_edit.editingFinished.connect(lambda idx=i: self._update_scaled_value(idx))
            self._scaling_edits.append(scaling_edit)
            grid_layout.addWidget(scaling_edit, display_row, 3)

            # Offset edit
            offset_edit = QLineEdit("0")
            offset_edit.setValidator(self.decimal_validator)
            offset_edit.editingFinished.connect(lambda idx=i: self._update_scaled_value(idx))
            self._offset_edits.append(offset_edit)
            grid_layout.addWidget(offset_edit, display_row, 4)

            # Scaled value edit (calculated)
            scaled_value_edit = QLineEdit("0")
            scaled_value_edit.setValidator(self.decimal_validator)
            self._scaled_value_edits.append(scaled_value_edit)
            grid_layout.addWidget(scaled_value_edit, display_row, 5)

            # Unit edit
            unit_edit = QLineEdit()
            self._unit_edits.append(unit_edit)
            grid_layout.addWidget(unit_edit, display_row, 6)

            # Plot checkbox
            plot_cb = QCheckBox()
            plot_cb.stateChanged.connect(lambda state: self.update_plot())
            self._plot_checkboxes.append(plot_cb)
            grid_layout.addWidget(plot_cb, display_row, 7)

            # Add slider after first row
            if row == 1:
                grid_layout.addWidget(self._slider, row + 1, 0, 1, 8)

        # Set column stretch
        grid_layout.setColumnStretch(1, 5)  # Variable
        grid_layout.setColumnStretch(2, 2)  # Value
        grid_layout.setColumnStretch(3, 1)  # Scaling
        grid_layout.setColumnStretch(4, 1)  # Offset
        grid_layout.setColumnStretch(5, 2)  # Scaled Value
        grid_layout.setColumnStretch(6, 1)  # Unit

        # Plot widget
        self._plot_widget = pg.PlotWidget(title="Watch Plot")
        self._plot_widget.setBackground("w")
        self._plot_widget.addLegend()
        self._plot_widget.showGrid(x=True, y=True)
        self._plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        layout.addWidget(self._plot_widget)

        # Save/Load buttons
        button_layout = QHBoxLayout()
        self._save_button = QPushButton("Save Config")
        self._save_button.setFixedSize(100, 30)
        self._load_button = QPushButton("Load Config")
        self._load_button.setFixedSize(100, 30)
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(self._load_button)
        layout.addLayout(button_layout)

    def on_connection_changed(self, connected: bool):
        """Handle connection state changes."""
        for i in range(self.MAX_VARS):
            self._live_checkboxes[i].setEnabled(connected)
            self._line_edits[i].setEnabled(connected)
        self._slider.setEnabled(connected and bool(self._line_edits[0].text()))

    def on_variable_list_updated(self, variables: list):
        """Handle variable list updates."""
        self._variable_list = variables

    def eventFilter(self, source, event):
        """Event filter to handle line edit click events for variable selection."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if isinstance(source, QLineEdit) and source in self._line_edits:
                index = self._line_edits.index(source)
                self._on_variable_click(index)
        return super().eventFilter(source, event)

    def _on_variable_click(self, index: int):
        """Handle click on variable field to open selection dialog."""
        if not self._variable_list:
            return

        dialog = VariableSelectionDialog(self._variable_list, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_variable:
            self._line_edits[index].setText(dialog.selected_variable)
            self._app_state.update_watch_var_field(index, "name", dialog.selected_variable)

            # Read initial value
            value = self._app_state.read_variable(dialog.selected_variable)
            if value is not None:
                self._value_edits[index].setText(str(value))
                self._app_state.update_watch_var_field(index, "value", value)

            # Enable slider for first variable
            if index == 0:
                self._slider.setEnabled(True)

    def _on_live_changed(self, index: int, state: int):
        """Handle live checkbox state change."""
        is_live = state == Qt.Checked
        self._app_state.update_watch_var_field(index, "live", is_live)
        # Emit signal to notify DataPoller
        self.live_polling_changed.emit(index, is_live)

    def _on_value_changed(self, index: int):
        """Handle value edit finished - write to device."""
        var_name = self._line_edits[index].text()
        if var_name and var_name != "None":
            try:
                value = float(self._value_edits[index].text())
                self._app_state.write_variable(var_name, value)
            except ValueError:
                pass

    def _update_scaled_value(self, index: int):
        """Update the scaled value for a variable."""
        try:
            value = self.safe_float(self._value_edits[index].text())
            scaling = self.safe_float(self._scaling_edits[index].text(), 1.0)
            offset = self.safe_float(self._offset_edits[index].text())
            scaled = self.calculate_scaled_value(value, scaling, offset)
            self._scaled_value_edits[index].setText(f"{scaled:.2f}")
        except Exception as e:
            logging.error(f"Error updating scaled value: {e}")

    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        var_name = self._line_edits[0].text()
        if var_name and var_name != "None":
            self._value_edits[0].setText(str(value))
            self._app_state.write_variable(var_name, float(value))

    @pyqtSlot(int, str, float)
    def on_watch_var_updated(self, index: int, name: str, value: float):
        """Handle watch variable update from data poller.

        Args:
            index: Variable index.
            name: Variable name.
            value: New value.
        """
        if 0 <= index < self.MAX_VARS:
            self._value_edits[index].setText(str(value))
            self._update_scaled_value(index)

    @pyqtSlot()
    def on_plot_data_ready(self):
        """Handle plot data ready signal - collect data point."""
        timestamp = datetime.now()

        if len(self._plot_data) > 0:
            last_timestamp = self._plot_data[-1][0]
            time_diff = (timestamp - last_timestamp).total_seconds() * 1000
        else:
            time_diff = 0

        data_point = [timestamp, time_diff]
        for edit in self._scaled_value_edits:
            data_point.append(self.safe_float(edit.text()))

        self._plot_data.append(tuple(data_point))
        self.update_plot()

    def update_plot(self):
        """Update the plot with current data."""
        try:
            if not self._plot_data:
                return

            self._plot_widget.clear()

            data = np.array(list(self._plot_data), dtype=object).T
            time_diffs = np.array(data[1], dtype=float)
            time_cumsum = np.cumsum(time_diffs)

            for i in range(self.MAX_VARS):
                if self._plot_checkboxes[i].isChecked() and self._line_edits[i].text():
                    values = np.array(data[i + 2], dtype=float)
                    self._plot_widget.plot(
                        time_cumsum,
                        values,
                        pen=pg.mkPen(color=self.PLOT_COLORS[i], width=2),
                        name=self._line_edits[i].text(),
                    )

            self._plot_widget.setLabel("left", "Value")
            self._plot_widget.setLabel("bottom", "Time", units="ms")
            self._plot_widget.showGrid(x=True, y=True)
        except Exception as e:
            logging.error(f"Error updating plot: {e}")

    def clear_plot_data(self):
        """Clear the plot data buffer."""
        self._plot_data.clear()

    def get_config(self) -> dict:
        """Get the current tab configuration."""
        return {
            "variables": [le.text() for le in self._line_edits],
            "values": [ve.text() for ve in self._value_edits],
            "scaling": [sc.text() for sc in self._scaling_edits],
            "offsets": [off.text() for off in self._offset_edits],
            "visible": [cb.isChecked() for cb in self._plot_checkboxes],
            "live": [cb.isChecked() for cb in self._live_checkboxes],
        }

    def load_config(self, config: dict):
        """Load configuration into the tab."""
        variables = config.get("variables", [])
        values = config.get("values", [])
        scalings = config.get("scaling", [])
        offsets = config.get("offsets", [])
        visibles = config.get("visible", [])
        lives = config.get("live", [])

        for i, (le, var) in enumerate(zip(self._line_edits, variables)):
            le.setText(var)
            # Update app state with variable name
            self._app_state.update_watch_var_field(i, "name", var)
        for ve, val in zip(self._value_edits, values):
            ve.setText(val)
        for sc, scale in zip(self._scaling_edits, scalings):
            sc.setText(scale)
        for off, offset in zip(self._offset_edits, offsets):
            off.setText(offset)
        for cb, visible in zip(self._plot_checkboxes, visibles):
            cb.setChecked(visible)
        for i, (cb, live) in enumerate(zip(self._live_checkboxes, lives)):
            cb.setChecked(live)
            # Update app state with live state
            self._app_state.update_watch_var_field(i, "live", live)

    @property
    def save_button(self) -> QPushButton:
        """Get the save button."""
        return self._save_button

    @property
    def load_button(self) -> QPushButton:
        """Get the load button."""
        return self._load_button
