"""ScopeView tab (Tab2) - Scope capture and trigger configuration."""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from pyx2cscope.gui.generic_gui.dialogs.variable_selection import VariableSelectionDialog
from pyx2cscope.gui.generic_gui.tabs.base_tab import BaseTab
from pyx2cscope.x2cscope import TriggerConfig

if TYPE_CHECKING:
    from pyx2cscope.gui.generic_gui.models.app_state import AppState


class ScopeViewTab(BaseTab):
    """Tab for oscilloscope-style data capture and visualization.

    Features:
    - 8 scope channels with trigger selection
    - Configurable trigger mode, edge, level, and delay
    - Single-shot and continuous capture modes
    - Real-time plotting with pyqtgraph
    """

    # Signal emitted when scope sampling state changes: (is_sampling, is_single_shot)
    scope_sampling_changed = pyqtSignal(bool, bool)

    MAX_CHANNELS = 8

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the ScopeView tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(app_state, parent)
        self._variable_list: List[str] = []
        self._trigger_variable: Optional[str] = None
        self._sampling_active: bool = False
        self._real_sampletime: float = 0.0

        # Widget lists
        self._var_line_edits: List[QLineEdit] = []
        self._trigger_checkboxes: List[QCheckBox] = []
        self._scaling_edits: List[QLineEdit] = []
        self._offset_edits: List[QLineEdit] = []
        self._color_combos: List[QComboBox] = []
        self._visible_checkboxes: List[QCheckBox] = []

        # Available colors for channels
        self._color_names = ["Blue", "Green", "Red", "Cyan", "Magenta", "Yellow", "Orange", "Purple"]

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Main grid for trigger config and variable selection
        main_grid = QGridLayout()
        layout.addLayout(main_grid)

        # Trigger configuration group
        trigger_group = self._create_trigger_group()
        main_grid.addWidget(trigger_group, 0, 0)

        # Variable selection group
        variable_group = self._create_variable_group()
        main_grid.addWidget(variable_group, 0, 1)

        # Set column stretch
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 3)

        # Plot widget
        self._plot_widget = pg.PlotWidget(title="Scope Plot")
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

    def _create_trigger_group(self) -> QGroupBox:
        """Create the trigger configuration group box."""
        group = QGroupBox("Trigger Configuration")
        layout = QVBoxLayout()
        group.setLayout(layout)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Single shot checkbox
        self._single_shot_checkbox = QCheckBox("Single Shot")
        grid.addWidget(self._single_shot_checkbox, 0, 0, 1, 2)

        # Sample time factor
        grid.addWidget(QLabel("Sample Time Factor"), 1, 0)
        self._sample_time_factor_edit = QLineEdit("1")
        self._sample_time_factor_edit.setValidator(self.decimal_validator)
        grid.addWidget(self._sample_time_factor_edit, 1, 1)

        # Scope sample time
        grid.addWidget(QLabel("Scope Sample Time (us):"), 2, 0)
        self._scope_sampletime_edit = QLineEdit("50")
        self._scope_sampletime_edit.setValidator(self.decimal_validator)
        grid.addWidget(self._scope_sampletime_edit, 2, 1)

        # Total time (read-only)
        grid.addWidget(QLabel("Total Time (ms):"), 3, 0)
        self._total_time_edit = QLineEdit("0")
        self._total_time_edit.setReadOnly(True)
        grid.addWidget(self._total_time_edit, 3, 1)

        # Trigger mode
        grid.addWidget(QLabel("Trigger Mode:"), 4, 0)
        self._trigger_mode_combo = QComboBox()
        self._trigger_mode_combo.addItems(["Auto", "Triggered"])
        grid.addWidget(self._trigger_mode_combo, 4, 1)

        # Trigger edge
        grid.addWidget(QLabel("Trigger Edge:"), 5, 0)
        self._trigger_edge_combo = QComboBox()
        self._trigger_edge_combo.addItems(["Rising", "Falling"])
        grid.addWidget(self._trigger_edge_combo, 5, 1)

        # Trigger level
        grid.addWidget(QLabel("Trigger Level:"), 6, 0)
        self._trigger_level_edit = QLineEdit("0")
        self._trigger_level_edit.setValidator(self.decimal_validator)
        grid.addWidget(self._trigger_level_edit, 6, 1)

        # Trigger delay
        grid.addWidget(QLabel("Trigger Delay:"), 7, 0)
        self._trigger_delay_edit = QLineEdit("0")
        self._trigger_delay_edit.setValidator(self.decimal_validator)
        grid.addWidget(self._trigger_delay_edit, 7, 1)

        # Sample button
        self._sample_button = QPushButton("Sample")
        self._sample_button.setFixedSize(100, 30)
        self._sample_button.clicked.connect(self._on_sample_clicked)
        grid.addWidget(self._sample_button, 8, 0, 1, 2)

        return group

    def _create_variable_group(self) -> QGroupBox:
        """Create the variable selection group box."""
        group = QGroupBox("Variable Selection")
        layout = QVBoxLayout()
        group.setLayout(layout)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Headers
        grid.addWidget(QLabel("Trigger"), 0, 0)
        grid.addWidget(QLabel("Search Variable"), 0, 1)
        grid.addWidget(QLabel("Gain"), 0, 2)
        grid.addWidget(QLabel("Offset"), 0, 3)
        grid.addWidget(QLabel("Color"), 0, 4)
        grid.addWidget(QLabel("Visible"), 0, 5)

        # Channel rows
        for i in range(self.MAX_CHANNELS):
            row = i + 1

            # Trigger checkbox
            trigger_cb = QCheckBox()
            trigger_cb.setMinimumHeight(20)
            trigger_cb.stateChanged.connect(lambda state, idx=i: self._on_trigger_changed(idx, state))
            self._trigger_checkboxes.append(trigger_cb)
            grid.addWidget(trigger_cb, row, 0)

            # Variable line edit
            line_edit = QLineEdit()
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Search Variable")
            line_edit.setMinimumHeight(20)
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            line_edit.installEventFilter(self)
            self._var_line_edits.append(line_edit)
            grid.addWidget(line_edit, row, 1)

            # Scaling edit (Gain)
            scaling_edit = QLineEdit("1")
            scaling_edit.setFixedSize(50, 20)
            scaling_edit.setValidator(self.decimal_validator)
            scaling_edit.editingFinished.connect(self._update_plot)
            self._scaling_edits.append(scaling_edit)
            grid.addWidget(scaling_edit, row, 2)

            # Offset edit
            offset_edit = QLineEdit("0")
            offset_edit.setFixedSize(50, 20)
            offset_edit.setValidator(self.decimal_validator)
            offset_edit.editingFinished.connect(self._update_plot)
            self._offset_edits.append(offset_edit)
            grid.addWidget(offset_edit, row, 3)

            # Color combo
            color_combo = QComboBox()
            color_combo.addItems(self._color_names)
            color_combo.setCurrentIndex(i % len(self._color_names))
            color_combo.setFixedSize(80, 20)
            color_combo.currentIndexChanged.connect(lambda idx: self._update_plot())
            self._color_combos.append(color_combo)
            grid.addWidget(color_combo, row, 4)

            # Visible checkbox
            visible_cb = QCheckBox()
            visible_cb.setChecked(True)
            visible_cb.setMinimumHeight(20)
            visible_cb.stateChanged.connect(lambda state: self._update_plot())
            self._visible_checkboxes.append(visible_cb)
            grid.addWidget(visible_cb, row, 5)

        return group

    def on_connection_changed(self, connected: bool):
        """Handle connection state changes."""
        self._sample_button.setEnabled(connected)
        for line_edit in self._var_line_edits:
            line_edit.setEnabled(connected)

    def on_variable_list_updated(self, variables: list):
        """Handle variable list updates."""
        self._variable_list = variables

    def eventFilter(self, source, event):
        """Event filter to handle line edit click events for variable selection."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if isinstance(source, QLineEdit) and source in self._var_line_edits:
                index = self._var_line_edits.index(source)
                self._on_variable_click(index)
        return super().eventFilter(source, event)

    def _on_variable_click(self, index: int):
        """Handle click on variable field to open selection dialog."""
        if not self._variable_list:
            return

        dialog = VariableSelectionDialog(self._variable_list, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_variable:
            self._var_line_edits[index].setText(dialog.selected_variable)
            self._app_state.update_scope_channel_field(index, "name", dialog.selected_variable)

    def _on_trigger_changed(self, index: int, state: int):
        """Handle trigger checkbox change - only one can be selected."""
        if state == Qt.Checked:
            # Uncheck all other trigger checkboxes
            for i, cb in enumerate(self._trigger_checkboxes):
                if i != index:
                    cb.setChecked(False)
            self._trigger_variable = self._var_line_edits[index].text()
            self._app_state.update_scope_channel_field(index, "trigger", True)
            logging.debug(f"Trigger variable set to: {self._trigger_variable}")
        else:
            self._trigger_variable = None
            self._app_state.update_scope_channel_field(index, "trigger", False)

    def _on_sample_clicked(self):
        """Handle sample button click."""
        if not self._app_state.is_connected():
            return

        if self._sampling_active:
            self._stop_sampling()
        else:
            self._start_sampling()

    def _start_sampling(self):
        """Start scope sampling."""
        try:
            x2cscope = self._app_state.x2cscope
            if not x2cscope:
                return

            # Clear existing channels
            x2cscope.clear_all_scope_channel()

            # Add configured channels
            for line_edit in self._var_line_edits:
                var_name = line_edit.text()
                if var_name and var_name != "None":
                    variable = x2cscope.get_variable(var_name)
                    if variable is not None:
                        x2cscope.add_scope_channel(variable)
                        logging.debug(f"Added scope channel: {var_name}")

            # Set sample time
            sample_time_factor = self.safe_int(self._sample_time_factor_edit.text(), 1)
            x2cscope.set_sample_time(sample_time_factor)

            # Get real sample time
            scope_sample_time_us = self.safe_int(self._scope_sampletime_edit.text(), 50)
            self._real_sampletime = x2cscope.get_scope_sample_time(scope_sample_time_us)
            self._total_time_edit.setText(str(self._real_sampletime))

            # Configure trigger
            self._configure_trigger()

            # Start sampling
            self._sampling_active = True
            self._sample_button.setText("Stop")
            x2cscope.request_scope_data()

            # Emit signal to notify DataPoller
            self.scope_sampling_changed.emit(True, self._single_shot_checkbox.isChecked())

            logging.info("Started scope sampling")

        except Exception as e:
            error_msg = f"Error starting sampling: {e}"
            logging.error(error_msg)

    def _stop_sampling(self):
        """Stop scope sampling."""
        self._sampling_active = False
        self._sample_button.setText("Sample")

        x2cscope = self._app_state.x2cscope
        if x2cscope:
            x2cscope.clear_all_scope_channel()

        # Emit signal to notify DataPoller
        self.scope_sampling_changed.emit(False, False)

        logging.info("Stopped scope sampling")

    def _configure_trigger(self):
        """Configure the scope trigger."""
        try:
            x2cscope = self._app_state.x2cscope
            if not x2cscope:
                return

            trigger_mode = self._trigger_mode_combo.currentText()

            if trigger_mode == "Auto":
                x2cscope.reset_scope_trigger()
                return

            if not self._trigger_variable:
                x2cscope.reset_scope_trigger()
                return

            variable = x2cscope.get_variable(self._trigger_variable)
            if variable is None:
                logging.warning(f"Trigger variable not found: {self._trigger_variable}")
                return

            trigger_level = self.safe_float(self._trigger_level_edit.text())
            trigger_delay = self.safe_int(self._trigger_delay_edit.text())

            # Rising = 0, Falling = 1 (per TriggerConfig spec)
            trigger_edge = 1 if self._trigger_edge_combo.currentText() == "Rising" else 0
            trigger_mode_val = 1  # Triggered mode

            trigger_config = TriggerConfig(
                variable=variable,
                trigger_level=trigger_level,
                trigger_mode=trigger_mode_val,
                trigger_delay=trigger_delay,
                trigger_edge=trigger_edge,
            )
            x2cscope.set_scope_trigger(trigger_config)
            logging.info("Trigger configured")

        except Exception as e:
            logging.error(f"Error configuring trigger: {e}")

    @pyqtSlot(dict)
    def on_scope_data_ready(self, data: Dict[str, List[float]]):
        """Handle scope data ready signal from data poller.

        Args:
            data: Dictionary of channel name to data values.
        """
        if not self._sampling_active:
            return

        self._plot_widget.clear()

        # Map color names to pyqtgraph colors
        color_map = {
            "Blue": "b", "Green": "g", "Red": "r", "Cyan": "c",
            "Magenta": "m", "Yellow": "y", "Orange": (255, 165, 0), "Purple": (128, 0, 128)
        }

        for i, (channel, values) in enumerate(data.items()):
            if i >= self.MAX_CHANNELS:
                break

            if self._visible_checkboxes[i].isChecked():
                scale_factor = self.safe_float(self._scaling_edits[i].text(), 1.0)
                offset = self.safe_float(self._offset_edits[i].text(), 0.0)
                time_values = np.linspace(0, self._real_sampletime, len(values))
                data_scaled = (np.array(values, dtype=float) * scale_factor) + offset

                # Get color from combo box
                color_name = self._color_combos[i].currentText()
                color = color_map.get(color_name, self.PLOT_COLORS[i % len(self.PLOT_COLORS)])

                self._plot_widget.plot(
                    time_values,
                    data_scaled,
                    pen=pg.mkPen(color=color, width=2),
                    name=f"{channel}",
                )

        self._plot_widget.setLabel("left", "Value")
        self._plot_widget.setLabel("bottom", "Time", units="ms")
        self._plot_widget.showGrid(x=True, y=True)

        # Handle single-shot mode - stop sampling after receiving data
        if self._single_shot_checkbox.isChecked():
            self._stop_sampling()
        # Note: In continuous mode, DataPoller handles requesting next data

    def _update_plot(self):
        """Update the plot (called when scale or visibility changes)."""
        # The plot will be updated on next data ready signal
        pass

    @property
    def is_sampling(self) -> bool:
        """Check if currently sampling."""
        return self._sampling_active

    @property
    def is_single_shot(self) -> bool:
        """Check if single-shot mode is enabled."""
        return self._single_shot_checkbox.isChecked()

    def get_config(self) -> dict:
        """Get the current tab configuration."""
        return {
            "variables": [le.text() for le in self._var_line_edits],
            "trigger": [cb.isChecked() for cb in self._trigger_checkboxes],
            "scale": [sc.text() for sc in self._scaling_edits],
            "offset": [off.text() for off in self._offset_edits],
            "color": [cb.currentText() for cb in self._color_combos],
            "show": [cb.isChecked() for cb in self._visible_checkboxes],
            "trigger_variable": self._trigger_variable,
            "trigger_level": self._trigger_level_edit.text(),
            "trigger_delay": self._trigger_delay_edit.text(),
            "trigger_edge": self._trigger_edge_combo.currentText(),
            "trigger_mode": self._trigger_mode_combo.currentText(),
            "sample_time_factor": self._sample_time_factor_edit.text(),
            "single_shot": self._single_shot_checkbox.isChecked(),
        }

    def load_config(self, config: dict):
        """Load configuration into the tab."""
        variables = config.get("variables", [])
        triggers = config.get("trigger", [])
        scales = config.get("scale", [])
        offsets = config.get("offset", [])
        colors = config.get("color", [])
        shows = config.get("show", [])

        for i, (le, var) in enumerate(zip(self._var_line_edits, variables)):
            le.setText(var)
            # Update app state with variable name
            self._app_state.update_scope_channel_field(i, "name", var)
        for i, (cb, trigger) in enumerate(zip(self._trigger_checkboxes, triggers)):
            cb.setChecked(trigger)
            self._app_state.update_scope_channel_field(i, "trigger", trigger)
        for i, (sc, scale) in enumerate(zip(self._scaling_edits, scales)):
            sc.setText(scale)
        for off, offset in zip(self._offset_edits, offsets):
            off.setText(offset)
        for cb, color in zip(self._color_combos, colors):
            cb.setCurrentText(color)
        for i, (cb, show) in enumerate(zip(self._visible_checkboxes, shows)):
            cb.setChecked(show)
            self._app_state.update_scope_channel_field(i, "visible", show)

        self._trigger_variable = config.get("trigger_variable", "")
        self._trigger_level_edit.setText(config.get("trigger_level", "0"))
        self._trigger_delay_edit.setText(config.get("trigger_delay", "0"))
        self._trigger_edge_combo.setCurrentText(config.get("trigger_edge", "Rising"))
        self._trigger_mode_combo.setCurrentText(config.get("trigger_mode", "Auto"))
        self._sample_time_factor_edit.setText(config.get("sample_time_factor", "1"))
        self._single_shot_checkbox.setChecked(config.get("single_shot", False))

    @property
    def save_button(self) -> QPushButton:
        """Get the save button."""
        return self._save_button

    @property
    def load_button(self) -> QPushButton:
        """Get the load button."""
        return self._load_button
