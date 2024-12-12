"""replicate of X2Cscpope."""

import logging

logging.basicConfig(level=logging.DEBUG)
import json
import os
import sys
import time
from collections import deque
from datetime import datetime

import matplotlib
import numpy as np
import pyqtgraph as pg  # Added pyqtgraph for interactive plotting
import serial.tools.list_ports  # Import the serial module to fix the NameError
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QFileInfo, QMutex, QRegExp, QSettings, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStyleFactory,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui import img as img_src
from pyx2cscope.x2cscope import TriggerConfig, X2CScope

logging.basicConfig(level=logging.DEBUG)

matplotlib.use("QtAgg")  # This sets the backend to Qt for Matplotlib


class VariableSelectionDialog(QDialog):
    """Initialize the variable selection dialog.

    Args:
        variables (list): A list of available variables to select from.
        parent (QWidget): The parent widget.
    """

    def __init__(self, variables, parent=None):
        """Set up the user interface components for the variable selection dialog."""
        super().__init__(parent)
        self.variables = variables
        self.selected_variable = None

        self.init_ui()

    def init_ui(self):
        """Initializing UI component."""
        self.setWindowTitle("Search Variable")
        self.setMinimumSize(300, 400)

        self.layout = QVBoxLayout()

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_variables)
        self.layout.addWidget(self.search_bar)

        self.variable_list = QListWidget(self)
        self.variable_list.addItems(self.variables)
        self.variable_list.itemDoubleClicked.connect(self.accept_selection)
        self.layout.addWidget(self.variable_list)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.button_box.accepted.connect(self.accept_selection)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def filter_variables(self, text):
        """Filter the variables based on user input in the search bar.

        Args:
            text (str): The input text to filter variables.
        """
        self.variable_list.clear()
        filtered_variables = [
            var for var in self.variables if text.lower() in var.lower()
        ]
        self.variable_list.addItems(filtered_variables)

    def accept_selection(self):
        """Accept the selection when a variable is chosen from the list.

        The selected variable is set as the `selected_variable` and the dialog is accepted.
        """
        selected_items = self.variable_list.selectedItems()
        if selected_items:
            self.selected_variable = selected_items[0].text()
            self.accept()


class X2cscopeGui(QMainWindow):
    """Main GUI class for the pyX2Cscope application."""

    def __init__(self, *args, **kwargs):
        """Initializing all the elements required."""
        super().__init__()
        self.x2cscope = None  # Ensures it is initialized to None at start
        self.x2cscope_initialized = (
            False  # Flag to ensure error message is shown only once
        )
        self.last_error_time = (
            None  # Attribute to track the last time an error was shown
        )
        self.triggerVariable = None
        self.elf_file_loaded = False
        self.config_file_loaded = False
        self.device_info_labels = {}  # Dictionary to hold the device information labels
        self.initialize_variables()
        self.init_ui()

    def initialize_variables(self):
        """Initialize instance variables."""
        self.timeout = 5
        self.sampling_active = False
        self.scaling_edits_tab3 = []  # Track scaling fields for Tab 3
        self.offset_edits_tab3 = []  # Track offset fields for Tab 3
        self.scaled_value_edits_tab3 = []  # Track scaled value fields for Tab 3
        self.offset_boxes = None
        self.plot_checkboxes = None
        self.scaled_value_boxes = None
        self.scaling_boxes = None
        self.Value_var_boxes = None
        self.line_edit_boxes = None
        self.live_checkboxes = None
        self.timer_list = None
        self.VariableList = []
        self.old_Variable_list = []
        self.var_factory = None
        self.ser = None
        self.timerValue = 500
        self.port_combo = QComboBox()
        self.layout = None
        self.slider_var1 = QSlider(Qt.Horizontal)
        self.plot_button = QPushButton("Plot")
        self.mutex = QMutex()
        self.grid_layout = QGridLayout()
        self.box_layout = QHBoxLayout()
        self.timer1 = QTimer()
        self.timer2 = QTimer()
        self.timer3 = QTimer()
        self.timer4 = QTimer()
        self.timer5 = QTimer()
        self.plot_update_timer = QTimer()  # Timer for continuous plot update
        self.timer()
        self.offset_var()
        self.plot_var_check()
        self.scaling_var()
        self.value_var()
        self.live_var()
        self.scaled_value()
        self.line_edit()
        self.sampletime = QLineEdit()
        self.unit_var()
        self.Connect_button = QPushButton("Connect")
        self.baud_combo = QComboBox()
        self.select_file_button = QPushButton("Select elf file")
        self.error_shown = False
        self.plot_window_open = False
        self.settings = QSettings("MyCompany", "MyApp")
        self.file_path: str = self.settings.value("file_path", "", type=str)
        self.initi_variables()

    def initi_variables(self):
        """Some variable initialisation."""
        self.device_info_labels = {
            "processor_id": QLabel("Loading Processor ID ..."),
            "uc_width": QLabel("Loading UC Width..."),
            "date": QLabel("Loading Date..."),
            "time": QLabel("Loading Time..."),
            "appVer": QLabel("Loading App Version..."),
            "dsp_state": QLabel("Loading DSP State..."),
        }
        self.selected_var_indices = [
            0,
            0,
            0,
            0,
            0,
        ]  # List to store selected variable indices
        self.selected_variables = []  # List to store selected variables
        self.previous_selected_variables = {}  # Dictionary to store previous selections
        decimal_regex = QRegExp("-?[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

        self.plot_data = deque(maxlen=250)  # Store plot data for all variables
        self.plot_colors = [
            "b",
            "g",
            "r",
            "c",
            "m",
            "y",
            "k",
        ]  # colours for different plot
        # Add self.labels on top
        self.labels = [
            "Live",
            "Variable",
            "Value",
            "Scaling",
            "Offset",
            "Scaled Value",
            "Unit",
            "Plot",
        ]

    def init_ui(self):
        """Initialize the user interface."""
        self.setup_application_style()
        self.create_central_widget()
        self.create_tabs()
        self.setup_tabs()
        self.setup_window_properties()
        #        self.setup_device_info_ui()  # Set up the device information section
        self.refresh_ports()

    def setup_application_style(self):
        """Set the application style."""
        QApplication.setStyle(QStyleFactory.create("Fusion"))

    def create_central_widget(self):
        """Create the central widget."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

    def update_device_info(self):
        """Fetch device information from the connected device and update the labels."""
        try:
            device_info = self.x2cscope.get_device_info()
            self.device_info_labels["processor_id"].setText(
                f" {device_info['processor_id']}"
            )
            self.device_info_labels["uc_width"].setText(f"{device_info['uc_width']}")
            self.device_info_labels["date"].setText(f"{device_info['date']}")
            self.device_info_labels["time"].setText(f"{device_info['time']}")
            self.device_info_labels["appVer"].setText(f"{device_info['AppVer']}")
            self.device_info_labels["dsp_state"].setText(f"{device_info['dsp_state']}")
        except Exception as e:
            self.handle_error(f"Error fetching device info: {e}")

    def create_tabs(self):
        """Create tabs for the main window."""
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()  # New tab for WatchView Only
        self.tab_widget.addTab(self.tab1, "WatchPlot")
        self.tab_widget.addTab(self.tab2, "ScopeView")
        self.tab_widget.addTab(self.tab3, "WatchView")  # Add third tab

    def setup_tabs(self):
        """Set up the contents of each tab."""
        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()  # Setup for the third tab

    def setup_window_properties(self):
        """Set up the main window properties."""
        self.setWindowTitle("pyX2Cscope")
        mchp_img = os.path.join(os.path.dirname(img_src.__file__), "pyx2cscope.jpg")
        self.setWindowIcon(QtGui.QIcon(mchp_img))

    def line_edit(self):
        """Initializing line edits."""
        self.line_edit5 = QLineEdit()
        self.line_edit4 = QLineEdit()
        self.line_edit3 = QLineEdit()
        self.line_edit2 = QLineEdit()
        self.line_edit1 = QLineEdit()

        for line_edit in [
            self.line_edit1,
            self.line_edit2,
            self.line_edit3,
            self.line_edit4,
            self.line_edit5,
        ]:
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Search Variable")
            line_edit.installEventFilter(self)

    def scaled_value(self):
        """Initializing Scaled variable."""
        self.ScaledValue_var1 = QLineEdit(self)
        self.ScaledValue_var2 = QLineEdit(self)
        self.ScaledValue_var3 = QLineEdit(self)
        self.ScaledValue_var4 = QLineEdit(self)
        self.ScaledValue_var5 = QLineEdit(self)

    def live_var(self):
        """Initializing live variable."""
        self.Live_var1 = QCheckBox(self)
        self.Live_var2 = QCheckBox(self)
        self.Live_var3 = QCheckBox(self)
        self.Live_var4 = QCheckBox(self)
        self.Live_var5 = QCheckBox(self)

    def value_var(self):
        """Initializing value variable."""
        self.Value_var1 = QLineEdit(self)
        self.Value_var2 = QLineEdit(self)
        self.Value_var3 = QLineEdit(self)
        self.Value_var4 = QLineEdit(self)
        self.Value_var5 = QLineEdit(self)

    def timer(self):
        """Initializing timers."""
        self.timers = [QTimer() for _ in range(5)]

    def offset_var(self):
        """Initializing Offset Variable."""
        self.offset_var1 = QLineEdit()
        self.offset_var2 = QLineEdit()
        self.offset_var3 = QLineEdit()
        self.offset_var4 = QLineEdit()
        self.offset_var5 = QLineEdit()

    def plot_var_check(self):
        """Initializing plot variable check boxes."""
        self.plot_var5_checkbox = QCheckBox()
        self.plot_var2_checkbox = QCheckBox()
        self.plot_var4_checkbox = QCheckBox()
        self.plot_var3_checkbox = QCheckBox()
        self.plot_var1_checkbox = QCheckBox()

    def scaling_var(self):
        """Initializing Scaling variable."""
        self.Scaling_var1 = QLineEdit(self)
        self.Scaling_var2 = QLineEdit(self)
        self.Scaling_var3 = QLineEdit(self)
        self.Scaling_var4 = QLineEdit(self)
        self.Scaling_var5 = QLineEdit(self)

    def unit_var(self):
        """Initializing unit variable."""
        self.Unit_var1 = QLineEdit(self)
        self.Unit_var2 = QLineEdit(self)
        self.Unit_var3 = QLineEdit(self)
        self.Unit_var4 = QLineEdit(self)
        self.Unit_var5 = QLineEdit(self)

    # noinspection PyUnresolvedReferences
    def setup_tab1(self):
        """Set up the first tab with the original functionality."""
        self.tab1.layout = QVBoxLayout()
        self.tab1.setLayout(self.tab1.layout)

        grid_layout = QGridLayout()
        self.tab1.layout.addLayout(grid_layout)

        self.setup_port_layout(grid_layout)
        #        self.setup_baud_layout(grid_layout)
        self.setup_sampletime_layout(grid_layout)
        self.setup_variable_layout(grid_layout)
        self.setup_connections()

        # Add Save and Load buttons
        self.save_button_watch = QPushButton("Save Config")
        self.load_button_watch = QPushButton("Load Config")
        self.save_button_watch.setFixedSize(100, 30)
        self.load_button_watch.setFixedSize(100, 30)
        self.save_button_watch.clicked.connect(self.save_config)
        self.load_button_watch.clicked.connect(self.load_config)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button_watch)
        button_layout.addWidget(self.load_button_watch)
        self.tab1.layout.addLayout(button_layout)

    def setup_tab2(self):
        """Set up the second tab with the scope functionality."""
        self.tab2.layout = QVBoxLayout()
        self.tab2.setLayout(self.tab2.layout)

        main_grid_layout = QGridLayout()
        self.tab2.layout.addLayout(main_grid_layout)

        # Set up individual components
        trigger_group = self.create_trigger_configuration_group()
        variable_group = self.create_variable_selection_group()
        self.scope_plot_widget = self.create_scope_plot_widget()
        button_layout = self.create_save_load_buttons()

        # Add the group boxes to the main layout with stretch factors
        main_grid_layout.addWidget(trigger_group, 0, 0)
        main_grid_layout.addWidget(variable_group, 0, 1)

        # Set the column stretch factors to make the variable group larger
        main_grid_layout.setColumnStretch(0, 1)  # Trigger configuration box
        main_grid_layout.setColumnStretch(1, 3)  # Variable selection box

        # Add the plot widget for scope view
        self.tab2.layout.addWidget(self.scope_plot_widget)

        # Add Save and Load buttons
        self.tab2.layout.addLayout(button_layout)

    def create_trigger_configuration_group(self):
        """Create the trigger configuration group box."""
        trigger_group = QGroupBox("Trigger Configuration")
        trigger_layout = QVBoxLayout()
        trigger_group.setLayout(trigger_layout)

        grid_layout_trigger = QGridLayout()
        trigger_layout.addLayout(grid_layout_trigger)

        self.single_shot_checkbox = QCheckBox("Single Shot")
        self.sample_time_factor = QLineEdit("1")
        self.sample_time_factor.setValidator(self.decimal_validator)
        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems(["Auto", "Triggered"])
        self.trigger_edge_combo = QComboBox()
        self.trigger_edge_combo.addItems(["Rising", "Falling"])
        self.trigger_level_edit = QLineEdit("0")
        self.trigger_level_edit.setValidator(self.decimal_validator)
        self.trigger_delay_edit = QLineEdit("0")
        self.trigger_delay_edit.setValidator(self.decimal_validator)

        self.scope_sampletime_edit = QLineEdit(
            "50"
        )  # Default sample time in microseconds
        self.scope_sampletime_edit.setValidator(self.decimal_validator)

        # Total Time
        self.total_time_label = QLabel("Total Time (ms):")
        self.total_time_value = QLineEdit("0")
        self.total_time_value.setReadOnly(True)

        self.scope_sample_button = QPushButton("Sample")
        self.scope_sample_button.setFixedSize(100, 30)
        self.scope_sample_button.clicked.connect(self.start_sampling)

        # Arrange widgets in grid layout
        grid_layout_trigger.addWidget(self.single_shot_checkbox, 0, 0, 1, 2)
        grid_layout_trigger.addWidget(QLabel("Sample Time Factor"), 1, 0)
        grid_layout_trigger.addWidget(self.sample_time_factor, 1, 1)
        grid_layout_trigger.addWidget(QLabel("Scope Sample Time (µs):"), 2, 0)
        grid_layout_trigger.addWidget(self.scope_sampletime_edit, 2, 1)
        grid_layout_trigger.addWidget(self.total_time_label, 3, 0)
        grid_layout_trigger.addWidget(self.total_time_value, 3, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Mode:"), 4, 0)
        grid_layout_trigger.addWidget(self.trigger_mode_combo, 4, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Edge:"), 5, 0)
        grid_layout_trigger.addWidget(self.trigger_edge_combo, 5, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Level:"), 6, 0)
        grid_layout_trigger.addWidget(self.trigger_level_edit, 6, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Delay:"), 7, 0)
        grid_layout_trigger.addWidget(self.trigger_delay_edit, 7, 1)
        grid_layout_trigger.addWidget(self.scope_sample_button, 8, 0, 1, 2)

        return trigger_group

    def create_variable_selection_group(self):
        """Create the variable selection group box."""
        variable_group = QGroupBox("Variable Selection")
        variable_layout = QVBoxLayout()
        variable_group.setLayout(variable_layout)

        grid_layout_variable = QGridLayout()
        variable_layout.addLayout(grid_layout_variable)

        self.scope_var_lines = [QLineEdit() for _ in range(7)]
        self.trigger_var_checkbox = [QCheckBox() for _ in range(7)]
        self.scope_channel_checkboxes = [QCheckBox() for _ in range(7)]
        self.scope_scaling_boxes = [QLineEdit("1") for _ in range(7)]

        for checkbox in self.scope_channel_checkboxes:
            checkbox.setChecked(True)

        for line_edit in self.scope_var_lines:
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Search Variable")
            line_edit.installEventFilter(self)

        # Add "Search Variable" label
        grid_layout_variable.addWidget(QLabel("Search Variable"), 0, 1)
        grid_layout_variable.addWidget(QLabel("Trigger"), 0, 0)
        grid_layout_variable.addWidget(QLabel("Gain"), 0, 2)
        grid_layout_variable.addWidget(QLabel("Visible"), 0, 3)

        for i, (line_edit, trigger_checkbox, scale_box, show_checkbox) in enumerate(
            zip(
                self.scope_var_lines,
                self.trigger_var_checkbox,
                self.scope_scaling_boxes,
                self.scope_channel_checkboxes,
            )
        ):
            line_edit.setMinimumHeight(20)
            trigger_checkbox.setMinimumHeight(20)
            show_checkbox.setMinimumHeight(20)
            scale_box.setMinimumHeight(20)
            scale_box.setFixedSize(50, 20)
            scale_box.setValidator(self.decimal_validator)

            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            grid_layout_variable.addWidget(trigger_checkbox, i + 1, 0)
            grid_layout_variable.addWidget(line_edit, i + 1, 1)
            grid_layout_variable.addWidget(scale_box, i + 1, 2)
            grid_layout_variable.addWidget(show_checkbox, i + 1, 3)

            trigger_checkbox.stateChanged.connect(
                lambda state, x=i: self.handle_scope_checkbox_change(state, x)
            )
            scale_box.editingFinished.connect(self.update_scope_plot)
            show_checkbox.stateChanged.connect(self.update_scope_plot)

        return variable_group

    def create_scope_plot_widget(self):
        """Create the scope plot widget."""
        scope_plot_widget = pg.PlotWidget(title="Scope Plot")
        scope_plot_widget.setBackground("w")
        scope_plot_widget.addLegend()
        scope_plot_widget.showGrid(x=True, y=True)
        scope_plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)

        return scope_plot_widget

    def create_save_load_buttons(self):
        """Create the save and load buttons."""
        self.save_button_scope = QPushButton("Save Config")
        self.load_button_scope = QPushButton("Load Config")
        self.save_button_scope.setFixedSize(100, 30)
        self.load_button_scope.setFixedSize(100, 30)
        self.save_button_scope.clicked.connect(self.save_config)
        self.load_button_scope.clicked.connect(self.load_config)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button_scope)
        button_layout.addWidget(self.load_button_scope)

        return button_layout

    def handle_scope_checkbox_change(self, state, index):
        """Handle the change in the state of the scope view checkboxes."""
        if state == Qt.Checked:
            for i, checkbox in enumerate(self.trigger_var_checkbox):
                if i != index:
                    checkbox.setChecked(False)
            self.triggerVariable = self.scope_var_lines[index].text()
            print(f"Checked variable: {self.scope_var_lines[index].text()}")
        else:
            self.triggerVariable = None

    def setup_port_layout(self, layout):
        """Set up the port selection, baud rate, and device information layout in two sections."""
        # Create the left layout for device information (QVBoxLayout)
        left_layout = QGridLayout()

        # Add device information labels to the left side
        for label_key, label in self.device_info_labels.items():
            info_label = QLabel(label_key.replace("_", " ").capitalize() + ":")
            info_label.setAlignment(Qt.AlignLeft)

            row = list(self.device_info_labels.keys()).index(
                label_key
            )  # Get the row index
            device_info_layout = (
                QGridLayout()
            )  # Create a row layout for label and its value
            device_info_layout.addWidget(info_label, row, 0, Qt.AlignRight)
            device_info_layout.addWidget(label, row, 1, alignment=Qt.AlignRight)
            left_layout.addLayout(device_info_layout, row, 0, Qt.AlignLeft)

        # Create the right layout for COM port and settings (QGridLayout)
        right_layout = QGridLayout()

        # COM Port Selection
        port_label = QLabel("Select Port:")
        self.port_combo.setFixedSize(100, 25)  # Set fixed size for the port combo box
        refresh_button = QPushButton()
        refresh_button.setFixedSize(25, 25)
        refresh_button.clicked.connect(self.refresh_ports)
        refresh_img = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        refresh_button.setIcon(QIcon(refresh_img))

        # Add COM Port widgets to the right layout
        right_layout.addWidget(port_label, 0, 0, alignment=Qt.AlignRight)
        right_layout.addWidget(self.port_combo, 0, 1)
        right_layout.addWidget(refresh_button, 0, 2)

        # Baud Rate Selection
        baud_label = QLabel("Select Baud Rate:")
        self.baud_combo.setFixedSize(100, 25)
        self.baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        default_baud_rate = "115200"
        index = self.baud_combo.findText(default_baud_rate, Qt.MatchFixedString)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

        # Add Baud Rate widgets to the right layout
        right_layout.addWidget(baud_label, 1, 0, alignment=Qt.AlignRight)
        right_layout.addWidget(self.baud_combo, 1, 1)

        # Add Connect button and Sample time
        self.Connect_button.setFixedSize(100, 30)
        self.Connect_button.clicked.connect(self.toggle_connection)
        sampletime_label = QLabel("Sample Time WatchPlot:")
        self.sampletime.setFixedSize(100, 30)
        self.sampletime.setText("500")

        # Add Connect and Sample Time widgets to the right layout
        self.sampletime.setValidator(self.decimal_validator)
        self.sampletime.editingFinished.connect(self.sampletime_edit)
        right_layout.addWidget(sampletime_label, 2, 0, alignment=Qt.AlignRight)
        right_layout.addWidget(self.sampletime, 2, 1, alignment=Qt.AlignLeft)
        right_layout.addWidget(QLabel("ms"), 2, 2, alignment=Qt.AlignLeft)
        right_layout.addWidget(self.Connect_button, 3, 1, alignment=Qt.AlignBottom)

        # Create a horizontal layout to contain both left and right sections
        horizontal_layout = QHBoxLayout()

        # Add left (device information) and right (settings) layouts to the horizontal layout
        horizontal_layout.addLayout(left_layout)
        horizontal_layout.addLayout(right_layout)

        # Finally, add the horizontal layout to the grid at a specific row and column
        layout.addLayout(horizontal_layout, 0, 0, 1, 2)  # Span 1 row and 2 columns

    def setup_sampletime_layout(self, layout):
        """Set up the sample time layout."""
        # self.Connect_button.clicked.connect(self.toggle_connection)
        self.select_file_button.clicked.connect(self.select_elf_file)
        layout.addWidget(self.select_file_button, 4, 0)

    def setup_variable_layout(self, layout):
        """Set up the variable selection layout."""
        self.timer_list = [
            self.timer1,
            self.timer2,
            self.timer3,
            self.timer4,
            self.timer5,
        ]

        for col, label in enumerate(self.labels):
            self.grid_layout.addWidget(QLabel(label), 0, col)

        self.live_checkboxes = [
            self.Live_var1,
            self.Live_var2,
            self.Live_var3,
            self.Live_var4,
            self.Live_var5,
        ]
        self.line_edit_boxes = [
            self.line_edit1,
            self.line_edit2,
            self.line_edit3,
            self.line_edit4,
            self.line_edit5,
        ]
        self.Value_var_boxes = [
            self.Value_var1,
            self.Value_var2,
            self.Value_var3,
            self.Value_var4,
            self.Value_var5,
        ]
        self.scaling_boxes = [
            self.Scaling_var1,
            self.Scaling_var2,
            self.Scaling_var3,
            self.Scaling_var4,
            self.Scaling_var5,
        ]
        self.scaled_value_boxes = [
            self.ScaledValue_var1,
            self.ScaledValue_var2,
            self.ScaledValue_var3,
            self.ScaledValue_var4,
            self.ScaledValue_var5,
        ]
        unit_boxes = [
            self.Unit_var1,
            self.Unit_var2,
            self.Unit_var3,
            self.Unit_var4,
            self.Unit_var5,
        ]
        self.plot_checkboxes = [
            self.plot_var1_checkbox,
            self.plot_var2_checkbox,
            self.plot_var3_checkbox,
            self.plot_var4_checkbox,
            self.plot_var5_checkbox,
        ]
        self.offset_boxes = [
            self.offset_var1,
            self.offset_var2,
            self.offset_var3,
            self.offset_var4,
            self.offset_var5,
        ]

        for row_index, (
            live_var,
            line_edit,
            value_var,
            scaling_var,
            offset_var,
            scaled_value_var,
            unit_var,
            plot_checkbox,
        ) in enumerate(
            zip(
                self.live_checkboxes,
                self.line_edit_boxes,
                self.Value_var_boxes,
                self.scaling_boxes,
                self.offset_boxes,
                self.scaled_value_boxes,
                unit_boxes,
                self.plot_checkboxes,
            ),
            1,
        ):
            live_var.setEnabled(False)
            line_edit.setEnabled(False)

            # Set size policy for variable name (line_edit) and value field to expand
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            value_var.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            value_var.setText("0")
            value_var.setValidator(self.decimal_validator)
            scaling_var.setText("1")
            offset_var.setText("0")
            offset_var.setValidator(self.decimal_validator)
            scaled_value_var.setText("0")
            scaled_value_var.setValidator(self.decimal_validator)
            display_row = row_index  # Use a different variable name for the assignment
            if display_row > 1:
                display_row += 1
            self.grid_layout.addWidget(live_var, display_row, 0)
            self.grid_layout.addWidget(line_edit, display_row, 1)
            if display_row == 1:
                self.grid_layout.addWidget(self.slider_var1, display_row + 1, 0, 1, 7)

            self.grid_layout.addWidget(value_var, display_row, 2)
            self.grid_layout.addWidget(scaling_var, display_row, 3)
            self.grid_layout.addWidget(offset_var, display_row, 4)
            self.grid_layout.addWidget(scaled_value_var, display_row, 5)
            self.grid_layout.addWidget(unit_var, display_row, 6)
            self.grid_layout.addWidget(plot_checkbox, display_row, 7)
            plot_checkbox.stateChanged.connect(
                lambda state, x=row_index - 1: self.update_watch_plot()
            )

        layout.addLayout(self.grid_layout, 5, 0)

        # Adjust the column stretch factors to ensure proper resizing
        self.grid_layout.setColumnStretch(1, 5)  # Variable column expands more
        self.grid_layout.setColumnStretch(2, 2)  # Value column
        self.grid_layout.setColumnStretch(3, 1)  # Scaling column
        self.grid_layout.setColumnStretch(4, 1)  # Offset column
        self.grid_layout.setColumnStretch(5, 2)  # Scaled Value column
        self.grid_layout.setColumnStretch(6, 1)  # Unit column

        # Add the plot widget for watch view
        self.watch_plot_widget = pg.PlotWidget(title="Watch Plot")
        self.watch_plot_widget.setBackground("w")
        self.watch_plot_widget.addLegend()  # Add legend to the plot widget
        self.watch_plot_widget.showGrid(x=True, y=True)  # Enable grid lines
        # Change to 1-button zoom mode
        self.watch_plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.tab1.layout.addWidget(self.watch_plot_widget)

    def setup_connections(self):
        """Set up connections for various widgets."""
        self.plot_button.clicked.connect(self.plot_data_plot)

        for timer, line_edit, value_var in zip(
            self.timer_list, self.line_edit_boxes, self.Value_var_boxes
        ):
            timer.timeout.connect(
                lambda cb=line_edit, v_var=value_var: self.handle_var_update(
                    cb.text(), v_var
                )
            )

        for line_edit, value_var in zip(self.line_edit_boxes, self.Value_var_boxes):
            value_var.editingFinished.connect(
                lambda cb=line_edit, v_var=value_var: self.handle_variable_putram(
                    cb.text(), v_var
                )
            )

        self.connect_editing_finished()

        for timer, live_var in zip(self.timer_list, self.live_checkboxes):
            live_var.stateChanged.connect(
                lambda state, lv=live_var, tm=timer: self.var_live(lv, tm)
            )

        self.slider_var1.setMinimum(-32768)
        self.slider_var1.setMaximum(32767)
        self.slider_var1.setEnabled(False)
        self.slider_var1.valueChanged.connect(self.slider_var1_changed)

        self.plot_update_timer.timeout.connect(
            self.update_watch_plot
        )  # Connect the QTimer to the update method

    def connect_editing_finished(self):
        """Connect editingFinished signals for value and scaling inputs."""
        for (
            scaling,
            value_var,
            scaled_value,
            offset,
        ) in zip(
            self.scaling_boxes,
            self.Value_var_boxes,
            self.scaled_value_boxes,
            self.offset_boxes,
        ):

            def connect_editing_finished(
                sc_edit=scaling,
                v_edit=value_var,
                scd_edit=scaled_value,
                off_edit=offset,
            ):
                def on_editing_finished():
                    self.update_scaled_value(sc_edit, v_edit, scd_edit, off_edit)

                return on_editing_finished

            value_var.editingFinished.connect(connect_editing_finished())

        for (
            scaling,
            value_var,
            scaled_value,
            offset,
        ) in zip(
            self.scaling_boxes,
            self.Value_var_boxes,
            self.scaled_value_boxes,
            self.offset_boxes,
        ):

            def connect_editing_finished(
                sc_edit=scaling,
                v_edit=value_var,
                scd_edit=scaled_value,
                off_edit=offset,
            ):
                def on_editing_finished():
                    self.update_scaled_value(sc_edit, v_edit, scd_edit, off_edit)

                return on_editing_finished

            scaling.editingFinished.connect(connect_editing_finished())

        for (
            scaling,
            value_var,
            scaled_value,
            offset,
        ) in zip(
            self.scaling_boxes,
            self.Value_var_boxes,
            self.scaled_value_boxes,
            self.offset_boxes,
        ):

            def connect_text_changed(
                sc_edit=scaling,
                v_edit=value_var,
                scd_edit=scaled_value,
                off_edit=offset,
            ):
                def on_text_changed():
                    self.update_scaled_value(sc_edit, v_edit, scd_edit, off_edit)

                return on_text_changed

            value_var.textChanged.connect(connect_text_changed())

        for (
            scaling,
            value_var,
            scaled_value,
            offset,
        ) in zip(
            self.scaling_boxes,
            self.Value_var_boxes,
            self.scaled_value_boxes,
            self.offset_boxes,
        ):

            def connect_text_changed(
                sc_edit=scaling,
                v_edit=value_var,
                scd_edit=scaled_value,
                off_edit=offset,
            ):
                def on_text_changed():
                    self.update_scaled_value(sc_edit, v_edit, scd_edit, off_edit)

                return on_text_changed

            offset.editingFinished.connect(connect_text_changed())

    @pyqtSlot()
    def var_live(self, live_var, timer):
        """Handles the state change of live variable checkboxes.

        Args:
            live_var (QCheckBox): The checkbox representing a live variable.
            timer (QTimer): The timer associated with the live variable.
        """
        try:
            if live_var.isChecked():
                if not timer.isActive():
                    timer.start(self.timerValue)
            elif timer.isActive():
                timer.stop()
        except Exception as e:
            logging.error(e)
            self.handle_error(f"Live Variable: {e}")

    @pyqtSlot()
    def update_scaled_value(self, scaling_var, value_var, scaled_value_var, offset_var):
        """Updates the scaled value based on the provided scaling factor and offset.

        Args:
            scaling_var : Input field for the scaling factor.
            value_var : Input field for the raw value.
            scaled_value_var : Input field for the scaled value.
            offset_var : Input field for the offset.
        """
        scaling_text = scaling_var.text()
        value_text = value_var.text()
        offset_text = offset_var.text()
        try:
            value = float(value_text)
            if offset_text.startswith("-"):
                float_offset = float(offset_text.lstrip("-"))
                offset = -1 * float_offset
            else:
                offset = float(offset_text)
            if scaling_text.startswith("-"):
                float_scaling = float(scaling_text.lstrip("-"))
                scaling = -1 * float_scaling
            else:
                scaling = float(scaling_text)
            scaled_value = (scaling * value) + offset
            scaled_value_var.setText("{:.2f}".format(scaled_value))
        except Exception as e:
            logging.error(e)
            self.handle_error(f"Error update Scaled Value: {e}")

    def plot_data_update(self):
        """Updates the data for plotting."""
        try:
            timestamp = datetime.now()
            if len(self.plot_data) > 0:
                last_timestamp = self.plot_data[-1][0]
                time_diff = (
                    timestamp - last_timestamp
                ).total_seconds() * 1000  # to convert time in ms.
            else:
                time_diff = 0

            def safe_float(value):
                try:
                    return float(value)
                except ValueError:
                    return 0.0

            self.plot_data.append(
                (
                    timestamp,
                    time_diff,
                    safe_float(self.ScaledValue_var1.text()),
                    safe_float(self.ScaledValue_var2.text()),
                    safe_float(self.ScaledValue_var3.text()),
                    safe_float(self.ScaledValue_var4.text()),
                    safe_float(self.ScaledValue_var5.text()),
                )
            )
        except Exception as e:
            logging.error(e)

    def update_watch_plot(self):
        """Updates the plot in the WatchView tab with new data."""
        try:
            if not self.plot_data:
                return

            # Clear the plot and remove old labels
            self.watch_plot_widget.clear()

            data = np.array(self.plot_data, dtype=object).T
            time_diffs = np.array(data[1], dtype=float)
            values = [np.array(data[i], dtype=float) for i in range(2, 7)]

            # Keep track of plot lines to avoid clearing and recreating them unnecessarily
            for i, (value, line_edit, plot_var) in enumerate(
                zip(values, self.line_edit_boxes, self.plot_checkboxes)
            ):
                # Check if the variable should be plotted and is not empty
                if plot_var.isChecked() and line_edit.text() != "":
                    self.watch_plot_widget.plot(
                        np.cumsum(time_diffs),
                        value,
                        pen=pg.mkPen(
                            color=self.plot_colors[i], width=2
                        ),  # Thicker plot line
                        name=line_edit.text(),
                    )

            # Reset plot labels
            self.watch_plot_widget.setLabel("left", "Value")
            self.watch_plot_widget.setLabel("bottom", "Time", units="ms")
            self.watch_plot_widget.showGrid(x=True, y=True)  # Enable grid lines
        except Exception as e:
            logging.error(e)

    def update_scope_plot(self):
        """Updates the plot in the ScopeView tab with new data and scaling."""
        try:
            if not self.sampling_active:
                return

            if not self.x2cscope.is_scope_data_ready():
                return

            data_storage = {}
            for channel, data in self.x2cscope.get_scope_channel_data(valid_data=True).items():
                data_storage[channel] = data

            self.scope_plot_widget.clear()

            for i, (channel, data) in enumerate(data_storage.items()):
                checkbox_state = self.scope_channel_checkboxes[i].isChecked()
                logging.debug(
                    f"Channel {channel}: Checkbox is {'checked' if checkbox_state else 'unchecked'}"
                )
                if checkbox_state:  # Check if the checkbox is checked
                    scale_factor = float(
                        self.scope_scaling_boxes[i].text()
                    )  # Get the scaling factor
                    # time_values = self.real_sampletime  # Generate time values in ms
                    # start = self.real_sampletime / len(data)
                    start = 0
                    time_values = np.linspace(start, self.real_sampletime, len(data))
                    data_scaled = (
                        np.array(data, dtype=float) * scale_factor
                    )  # Apply the scaling factor
                    self.scope_plot_widget.plot(
                        time_values,
                        data_scaled,
                        pen=pg.mkPen(color=self.plot_colors[i], width=2),
                        name=f"Channel {channel}",
                    )
                    logging.debug(
                        f"Plotting channel {channel} with color {self.plot_colors[i]}"
                    )
                else:
                    logging.debug(f"Not plotting channel {channel}")
            self.scope_plot_widget.setLabel("left", "Value")
            self.scope_plot_widget.setLabel("bottom", "Time", units="ms")
            self.scope_plot_widget.showGrid(x=True, y=True)
        except Exception as e:
            error_message = f"Error updating scope plot: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def plot_data_plot(self):
        """Initializes and starts data plotting."""
        try:
            if not self.plot_data:
                return

            self.update_watch_plot()
            self.update_scope_plot()

            if not self.plot_window_open:
                self.plot_window_open = True
        except Exception as e:
            logging.error(e)

    def handle_error(self, error_message: str):
        """Displays an error message in a message box with a cooldown period."""
        current_time = time.time()
        if self.last_error_time is None or (
            current_time - self.last_error_time > self.timeout
        ):  # Cooldown period of 5 seconds
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(error_message)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            self.last_error_time = current_time  # Update the last error time

    def sampletime_edit(self):
        """Handles the editing of the sample time value."""
        try:
            new_sample_time = int(self.sampletime.text())
            if new_sample_time != self.timerValue:
                self.timerValue = new_sample_time
                for timer in self.timer_list:
                    if timer.isActive():
                        timer.start(self.timerValue)
        except ValueError as e:
            logging.error(e)
            self.handle_error(f"Invalid sample time: {e}")

    @pyqtSlot()
    def handle_var_update(self, counter, value_var):
        """Handles the update of variable values from the microcontroller.

        Args:
            counter: The variable to update.
            value_var (QLineEdit): The input field to display the updated value.
        """
        if not self.is_connected():
            return  # Do not proceed if the device is not connected
        try:
            if counter is not None:
                counter = self.x2cscope.get_variable(counter)
                value = counter.get_value()
                value_var.setText(str(value))
                if value_var == self.Value_var1:
                    self.slider_var1.setValue(int(value))
                self.plot_data_update()
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def slider_var1_changed(self, value):
        """Handles the change in slider value for Variable 1.

        Args:
            value (int): The new value of the slider.
        """
        if self.line_edit1.text() == "":
            self.handle_error("Search Variable")
        else:
            self.Value_var1.setText(str(value))
            self.update_scaled_value(
                self.Scaling_var1,
                self.Value_var1,
                self.ScaledValue_var1,
                self.offset_var1,
            )
            self.handle_variable_putram(self.line_edit1.text(), self.Value_var1)

    @pyqtSlot()
    def handle_variable_getram(self, variable, value_var):
        """Handle the retrieval of values from RAM for the specified variable.

        Args:
            variable: The variable to retrieve the value for.
            value_var: The QLineEdit widget to display the retrieved value.
        """
        if not self.is_connected():
            return  # Do not proceed if the device is not connected

        try:
            current_variable = variable

            for index, line_edit in enumerate(self.line_edit_boxes):
                if line_edit.text() == current_variable:
                    self.selected_var_indices[index] = current_variable

            if current_variable and current_variable != "None":
                counter = self.x2cscope.get_variable(current_variable)
                value = counter.get_value()
                value_var.setText(str(value))
                if value_var == self.Value_var1:
                    self.slider_var1.setValue(int(value))

                if current_variable not in self.selected_variables:
                    self.selected_variables.append(current_variable)

        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def handle_variable_putram(self, variable, value_var):
        """Handle the writing of values to RAM for the specified variable.

        Args:
            variable: The variable to write the value to.
            value_var: The QLineEdit widget to get the value from.
        """
        if not self.is_connected():
            return  # Do not proceed if the device is not connected
        try:
            current_variable = variable
            value = float(value_var.text())

            if current_variable and current_variable != "None":
                counter = self.x2cscope.get_variable(current_variable)
                counter.set_value(value)

        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def select_elf_file(self):
        """Function to select elf file."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("ELF Files (*.elf)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if self.file_path:
            file_dialog.setDirectory(os.path.dirname(self.file_path))
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.file_path = selected_files[0]
                self.settings.setValue("file_path", self.file_path)
                self.select_file_button.setText(QFileInfo(self.file_path).fileName())
                self.elf_file_loaded = True

                # If Auto Connect is selected, attempt to auto-connect to the first available port

    def refresh_line_edit(self):
        """Refresh the contents of the variable selection line edits.

        This method repopulates the line edits used for variable selection
        with the updated list of variables.
        """
        if self.VariableList is not None:
            for index, line_edit in enumerate(self.line_edit_boxes):
                current_selected_text = line_edit.text()

                if current_selected_text in self.VariableList:
                    line_edit.setText(current_selected_text)
                else:
                    line_edit.setText("")

            for line_edit in self.scope_var_lines:
                current_selected_text = line_edit.text()

                if current_selected_text in self.VariableList:
                    line_edit.setText(current_selected_text)
                else:
                    line_edit.setText("")
        else:
            logging.warning("VariableList is None. Unable to refresh line edits.")

    def refresh_ports(self):
        """Refresh the list of available serial ports.

        This method updates the combo box containing the list of available
        serial ports to reflect the current state of the system.
        """
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItem("Auto Connect")  # Add an Auto Connect option
        self.port_combo.addItems(available_ports)

    @pyqtSlot()
    def toggle_connection(self):
        """Handle the connection or disconnection of the serial port.

        This method establishes or terminates the serial connection based on
        the current state of the connection.
        """
        if self.file_path == "":
            QMessageBox.warning(self, "Error", "Please select an ELF file.")
            self.select_elf_file()
            return

        # Check if already connected
        if self.ser is not None and self.ser.is_open:
            # Call the disconnect function if already connected
            logging.info("Already connected, disconnecting now.")
            self.disconnect_serial()
        else:
            # Handle connection logic if not connected
            for label in self.device_info_labels.values():
                label.setText("Loading...")
            for timer in self.timer_list:
                if timer.isActive():
                    timer.stop()
            self.plot_data.clear()
            self.save_selected_variables()  # Save the current selections before connecting

            try:
                self.connect_serial()  # Attempt to connect
                if self.ser is not None and self.ser.is_open:
                    # Fetch device information after successful connection
                    self.update_device_info()
            except Exception as e:
                logging.error(e)
                self.handle_error(f"Error connecting: {e}")

    def handle_failed_connection(self):
        """Popping up a window for the errors."""
        choice = QMessageBox.question(
            self,
            "Connection Failed",
            "Failed to connect with the current settings. Would you like to adjust the settings?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice == QMessageBox.Yes:
            # Optionally, bring up settings dialog or similar
            self.show_connection_settings()

    def save_selected_variables(self):
        """Save the current selections of variables in WatchView and ScopeView."""
        self.previous_selected_variables = {
            "watch": [(le.text(), le.text()) for le in self.line_edit_boxes],
            "scope": [(le.text(), le.text()) for le in self.scope_var_lines],
        }

    def restore_selected_variables(self):
        """Restore the previously selected variables in WatchView and ScopeView."""
        if "watch" in self.previous_selected_variables:
            for le, (var, _) in zip(
                self.line_edit_boxes, self.previous_selected_variables["watch"]
            ):
                le.setText(var)

        if "scope" in self.previous_selected_variables:
            for le, (var, _) in zip(
                self.scope_var_lines, self.previous_selected_variables["scope"]
            ):
                le.setText(var)

    def disconnect_serial(self):
        """Disconnect the current serial connection.

        This method safely terminates the existing serial connection, if any,
        and updates the UI to reflect the disconnection.
        """
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.stop()
                self.ser = None

            self.Connect_button.setText("Connect")
            self.Connect_button.setEnabled(True)
            self.select_file_button.setEnabled(True)
            widget_list = [self.port_combo, self.baud_combo]

            for widget in widget_list:
                widget.setEnabled(True)

            for line_edit in self.line_edit_boxes:
                line_edit.setEnabled(False)

            for live_var in self.live_checkboxes:
                live_var.setEnabled(False)

            self.slider_var1.setEnabled(False)
            for timer in self.timer_list:
                if timer.isActive():
                    timer.stop()

            self.plot_update_timer.stop()  # Stop the continuous plot update

        except Exception as e:
            error_message = f"Error while disconnecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

        if self.ser and self.ser.is_open:
            self.ser.close()
            self.Connect_button.setText("Connect")

    def connect_serial(self):
        """Establish a serial connection based on the current UI settings."""
        try:
            # Disconnect if already connected
            if self.ser is not None and self.ser.is_open:
                self.disconnect_serial()

            baud_rate = int(self.baud_combo.currentText())

            # Check if Auto Connect is selected
            if self.port_combo.currentText() == "Auto Connect":
                self.auto_connect_serial(baud_rate)
            else:
                self.manual_connect_serial(baud_rate)

        except Exception as e:
            error_message = f"Error while connecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def auto_connect_serial(self, baud_rate):
        """Attempt to auto-connect to available COM ports."""
        available_ports = [port.device for port in serial.tools.list_ports.comports()]

        # Iterate through available ports and attempt to connect
        for port in available_ports:
            if self.connect_to_port(port, baud_rate):
                return  # Exit once a connection is established

        # If no ports were successfully connected
        self.handle_error(
            "Auto-connect failed to connect to any available COM ports. Please check your connection!"
        )
        raise Exception("Auto-connect failed to connect to any available COM ports.")

    def manual_connect_serial(self, baud_rate):
        """Attempt to manually connect to the selected COM port."""
        port = self.port_combo.currentText()
        logging.info(f"Trying to connect to {port} manually.")

        # Retry mechanism: try to connect twice if the first attempt fails
        for attempt in range(2):
            if self.connect_to_port(port, baud_rate):
                return  # Exit once the connection is successful
            logging.info(f"Retrying connection to {port} (Attempt {attempt + 1})")

        raise Exception(f"Failed to connect to {port} after multiple attempts.")

    def connect_to_port(self, port, baud_rate):
        """Attempt to establish a connection to the specified port."""
        try:
            logging.info(f"Trying to connect to {port}...")
            self.x2cscope = X2CScope(
                port=port, elf_file=self.file_path, baud_rate=baud_rate
            )
            self.ser = self.x2cscope.interface

            # If connection is successful
            logging.info(f"Connected to {port} successfully.")
            self.select_file_button.setText(QFileInfo(self.file_path).fileName())
            self.port_combo.setCurrentText(
                port
            )  # Update combo box with the successful port
            self.setup_connected_state()  # Handle UI updates after connection
            return True
        except OSError as e:
            logging.error(f"Failed to connect to {port}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error connecting to {port}: {e}")
            return False

    def setup_connected_state(self):
        """Handle the UI updates and logic when a connection is successfully established."""
        # Refresh the variable list from the device
        self.VariableList = self.x2cscope.list_variables()
        if self.VariableList:
            self.VariableList.insert(0, "None")
        self.refresh_line_edit()

        # Update the UI elements
        self.Connect_button.setText("Disconnect")
        self.Connect_button.setEnabled(True)

        widget_list = [self.port_combo, self.baud_combo, self.select_file_button]
        for widget in widget_list:
            widget.setEnabled(False)

        for line_edit in self.line_edit_boxes:
            line_edit.setEnabled(True)
        self.slider_var1.setEnabled(True)

        for live_var in self.live_checkboxes:
            live_var.setEnabled(True)

        # Start any live variable timers
        for timer, live_var in zip(self.timer_list, self.live_checkboxes):
            if live_var.isChecked():
                timer.start(self.timerValue)

        # Start the continuous plot update
        self.plot_update_timer.start(self.timerValue)

        # Restore any selected variables that were saved before disconnecting
        self.restore_selected_variables()

    def close_plot_window(self):
        """Close the plot window if it is open.

        This method stops the animation and closes the plot window if it is open.
        """
        self.plot_window_open = False

    def close_event(self, event):
        """Handle the event when the main window is closed.

        Args:
            event: The close event.

        This method ensures that all resources are properly released and the
        application is closed cleanly.
        """
        if self.sampling_active:
            self.sampling_active = False
        if self.ser:
            self.disconnect_serial()
        event.accept()

    def start_sampling(self):
        """Start the sampling process."""
        if not self.is_connected():
            return  # Do not proceed if the device is not connected
        try:
            a = time.time()
            if self.sampling_active:
                self.sampling_active = False
                self.scope_sample_button.setText("Sample")
                logging.info("Stopped sampling.")

                # Stop sampling and timers
                if self.scope_timer.isActive():
                    self.scope_timer.stop()  # Stop the periodic sampling

                self.x2cscope.clear_all_scope_channel()  # Clears channels and stops requests
            else:
                self.x2cscope.clear_all_scope_channel()
                for line_edit in self.scope_var_lines:
                    variable_name = line_edit.text()
                    if variable_name and variable_name != "None":
                        variable = self.x2cscope.get_variable(variable_name)
                        self.x2cscope.add_scope_channel(variable)

                self.x2cscope.set_sample_time(
                    int(self.sample_time_factor.text())
                )  # set sample time factor

                # Set the scope sample time from the user input in microseconds
                scope_sample_time_us = int(self.scope_sampletime_edit.text())
                self.real_sampletime = self.x2cscope.scope_sample_time(
                    scope_sample_time_us
                )
                print(
                    f"Real sample time: {self.real_sampletime} µs"
                )  # Check this value

                # Update the Total Time display
                self.total_time_value.setText(str(self.real_sampletime))

                self.sampling_active = True
                self.configure_trigger()
                self.scope_sample_button.setText("Stop")
                logging.info("Started sampling.")
                self.x2cscope.request_scope_data()
                self.sample_scope_data(
                    single_shot=self.single_shot_checkbox.isChecked()
                )
            b = time.time()
            print("time execution", b - a)
        except Exception as e:
            error_message = f"Error starting sampling: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def configure_trigger(self):
        """Configure the trigger settings."""
        if not self.is_connected():
            return  # Do not proceed if the device is not connected
        try:
            if self.triggerVariable is not None:
                variable_name = self.triggerVariable
                variable = self.x2cscope.get_variable(variable_name)

                # Handle empty string for trigger level and delay
                trigger_level_text = self.trigger_level_edit.text().strip()
                trigger_delay_text = self.trigger_delay_edit.text().strip()

                if not trigger_level_text:
                    trigger_level = 0
                else:
                    try:
                        trigger_level = int(trigger_level_text)  # YA
                        print(trigger_level)
                    except ValueError:
                        logging.error(
                            f"Invalid trigger level value: {trigger_level_text}"
                        )
                        self.handle_error(
                            f"Invalid trigger level value: {trigger_level_text}"
                        )
                        return

                if not trigger_delay_text:
                    trigger_delay = 0
                else:
                    try:
                        trigger_delay = int(trigger_delay_text)
                    except ValueError:
                        logging.error(
                            f"Invalid trigger delay value: {trigger_delay_text}"
                        )
                        self.handle_error(
                            f"Invalid trigger delay value: {trigger_delay_text}"
                        )
                        return

                trigger_edge = (
                    0 if self.trigger_edge_combo.currentText() == "Rising" else 1
                )
                trigger_mode = (
                    2 if self.trigger_mode_combo.currentText() == "Auto" else 1
                )

                trigger_config = TriggerConfig(
                    variable=variable,
                    trigger_level=trigger_level,
                    trigger_mode=trigger_mode,
                    trigger_delay=trigger_delay,
                    trigger_edge=trigger_edge,
                )
                self.x2cscope.set_scope_trigger(trigger_config)
                logging.info("Trigger configured.")
        except Exception as e:
            error_message = f"Error configuring trigger: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def sample_scope_data(self, single_shot=False):
        """Sample the scope data using QTimer for non-blocking updates."""
        try:
            if not self.is_connected():
                return  # Do not proceed if the device is not connected

            self.sampling_active = True
            self.scope_sample_button.setText("Stop")  # Update button text

            # Create a QTimer for periodic scope data requests
            self.scope_timer = QTimer()
            self.scope_timer.timeout.connect(
                lambda: self._sample_scope_data_timer(single_shot)
            )
            self.scope_timer.start(250)  # Adjust the interval (milliseconds) as needed

        except Exception as e:
            error_message = f"Error starting sampling: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def _sample_scope_data_timer(self, single_shot):
        """Function that QTimer calls periodically to handle scope data sampling."""
        try:
            # Retry mechanism for single-shot mode
            if not self.x2cscope.is_scope_data_ready():
                if single_shot:
                    QTimer.singleShot(250, lambda: self._sample_scope_data_timer(single_shot))
                return  # Exit if data is not ready

            logging.info("Scope data is ready.")
            data_storage = {}
            for channel, data in self.x2cscope.get_scope_channel_data().items():
                data_storage[channel] = data

            # Plot the data
            self.scope_plot_widget.clear()
            for i, (channel, data) in enumerate(data_storage.items()):
                if self.scope_channel_checkboxes[i].isChecked():  # Check if the channel is enabled
                    scale_factor = float(self.scope_scaling_boxes[i].text())  # Get the scaling factor
                    start = 0
                    time_values = np.linspace(start, self.real_sampletime, len(data))
                    data_scaled = (
                            np.array(data, dtype=float) * scale_factor
                    )  # Apply the scaling factor
                    self.scope_plot_widget.plot(
                        time_values,
                        data_scaled,
                        pen=pg.mkPen(
                            color=self.plot_colors[i], width=2
                        ),  # Thicker plot line
                        name=f"Channel {channel}",
                    )

            # Update plot labels and grid
            self.scope_plot_widget.setLabel("left", "Value")
            self.scope_plot_widget.setLabel("bottom", "Time", units="ms")
            self.scope_plot_widget.showGrid(x=True, y=True)  # Enable grid lines

            # Stop timer if single-shot mode is active
            if single_shot:
                self.scope_timer.stop()  # Stop the timer
                self.sampling_active = False
                self.scope_sample_button.setText("Sample")  # Update button text

            # Request new data for the next tick
            if self.x2cscope.is_scope_data_ready():
                self.x2cscope.request_scope_data()

        except Exception as e:
            error_message = f"Error sampling scope data: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            self.scope_timer.stop()  # Stop timer on error
            self.sampling_active = False
            self.scope_sample_button.setText("Sample")  # Update button text

    def save_config(self):
        """Save current working config."""
        try:
            # Configuration dictionary includes the path to the ELF file
            config = {
                "elf_file": self.file_path,  # Store the current ELF file path
                "com_port": self.port_combo.currentText(),
                "baud_rate": self.baud_combo.currentText(),
                "watch_view": {
                    "variables": [le.text() for le in self.line_edit_boxes],
                    "values": [ve.text() for ve in self.Value_var_boxes],
                    "scaling": [sc.text() for sc in self.scaling_boxes],
                    "offsets": [off.text() for off in self.offset_boxes],
                    "visible": [cb.isChecked() for cb in self.plot_checkboxes],
                    "live": [cb.isChecked() for cb in self.live_checkboxes],
                },
                "scope_view": {
                    "variables": [le.text() for le in self.scope_var_lines],
                    "trigger": [cb.isChecked() for cb in self.trigger_var_checkbox],
                    "scale": [sc.text() for sc in self.scope_scaling_boxes],
                    "show": [cb.isChecked() for cb in self.scope_channel_checkboxes],
                    "trigger_variable": self.triggerVariable,
                    "trigger_level": self.trigger_level_edit.text(),
                    "trigger_delay": self.trigger_delay_edit.text(),
                    "trigger_edge": self.trigger_edge_combo.currentText(),
                    "trigger_mode": self.trigger_mode_combo.currentText(),
                    "sample_time_factor": self.sample_time_factor.text(),
                    "single_shot": self.single_shot_checkbox.isChecked(),
                },
                "tab3_view": {
                    "variables": [le.text() for le in self.variable_line_edits],
                    "values": [ve.text() for ve in self.value_line_edits],
                    "scaling": [sc.text() for sc in self.scaling_edits_tab3],
                    "offsets": [off.text() for off in self.offset_edits_tab3],
                    "scaled_values": [sv.text() for sv in self.scaled_value_edits_tab3],
                    "live": [cb.isChecked() for cb in self.live_tab3],
                },
            }
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Configuration", "", "JSON Files (*.json)"
            )
            if file_path:
                with open(file_path, "w") as file:
                    json.dump(config, file, indent=4)
                logging.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            self.handle_error(f"Error saving configuration: {e}")

    def load_config(self):
        """Loads a pre-saved/configured config file and applies its settings to the application.

        The method first prompts the user to select a configuration file. If a valid file is selected,
        it parses the JSON contents and loads settings related to the general application configuration,
        WatchView, ScopeView, and Tab 3. If an ELF file path is missing or incorrect, the user is prompted
        to reselect it. If connection to a COM port fails, it attempts to connect to available ports.
        """
        try:
            file_path = self.prompt_for_file()
            if file_path:
                config = self.load_json_file(file_path)
                self.load_general_settings(config)
                self.load_watch_view(config.get("watch_view", {}))
                self.load_scope_view(config.get("scope_view", {}))
                self.load_tab3_view(config.get("tab3_view", {}))
                logging.info(f"Configuration loaded from {file_path}")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            self.handle_error(f"Error loading configuration: {e}")

    def prompt_for_file(self):
        """Prompts the user to select a configuration file through a file dialog.

        :return: The file path selected by the user, or None if no file was selected.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "JSON Files (*.json)"
        )
        return file_path if file_path else None

    def load_json_file(self, file_path):
        """Loads a JSON file from the specified file path.

        :param file_path: The path to the JSON configuration file.
        :return: Parsed JSON content as a dictionary.
        """
        with open(file_path, "r") as file:
            return json.load(file)

    def load_general_settings(self, config):
        """Loads general configuration settings such as COM port, baud rate, and ELF file path.

        If the ELF file does not exist, prompts the user to select a new one. Attempts to connect
        to the specified COM port or other available ports if the connection fails.

        :param config: A dictionary containing general configuration settings.
        """
        self.config_file_loaded = True
        config_port = config.get("com_port", "")
        self.baud_combo.setCurrentText(config.get("baud_rate", ""))

        elf_file_path = config.get("elf_file", "")
        if os.path.exists(elf_file_path):
            self.file_path = elf_file_path
            self.elf_file_loaded = True
        else:
            self.show_file_not_found_warning(elf_file_path)
            self.select_elf_file()

        self.handle_connection(config_port)
        self.select_file_button.setText(QFileInfo(self.file_path).fileName())
        self.settings.setValue("file_path", self.file_path)

    def show_file_not_found_warning(self, elf_file_path):
        """Shows a warning message if the specified ELF file does not exist.

        :param elf_file_path: The path to the ELF file that was not found.
        """
        QMessageBox.warning(
            self, "File Not Found", f"The ELF file {elf_file_path} does not exist."
        )

    def handle_connection(self, config_port):
        """Attempts to connect to the specified COM port or any available port.

        If the connection to the specified port fails, it tries to connect to other available ports.
        If no port connection is successful, it shows a warning message.

        :param config_port: The port specified in the configuration file.
        """
        if not self.is_connected():
            available_ports = [
                port.device for port in serial.tools.list_ports.comports()
            ]
            if config_port in available_ports and self.attempt_connection():
                logging.info(f"Connected to the specified port: {config_port}")
            else:
                self.try_other_ports(available_ports)

    def try_other_ports(self, available_ports):
        """Attempts to connect to other available COM ports if the specified port connection fails.

        :param available_ports: A list of available COM ports.
        """
        for port in available_ports:
            self.port_combo.setCurrentText(port)
            if self.attempt_connection():
                logging.info(f"Connected to an alternative port: {port}")
                break
        else:
            QMessageBox.warning(
                self,
                "Connection Failed",
                "Could not connect to any available ports. Please check your connection.",
            )

    def load_watch_view(self, watch_view):
        """Loads the WatchView settings from the configuration file.

        This includes variables, values, scaling, offsets, plot visibility, and live status.

        :param watch_view: A dictionary containing WatchView settings.
        """
        for le, var in zip(self.line_edit_boxes, watch_view.get("variables", [])):
            le.setText(var)
        for ve, val in zip(self.Value_var_boxes, watch_view.get("values", [])):
            ve.setText(val)
        for sc, scale in zip(self.scaling_boxes, watch_view.get("scaling", [])):
            sc.setText(scale)
        for off, offset in zip(self.offset_boxes, watch_view.get("offsets", [])):
            off.setText(offset)
        for cb, visible in zip(self.plot_checkboxes, watch_view.get("visible", [])):
            cb.setChecked(visible)
        for cb, live in zip(self.live_checkboxes, watch_view.get("live", [])):
            cb.setChecked(live)

    def load_scope_view(self, scope_view):
        """Loads the ScopeView settings from the configuration file.

        This includes variables, trigger settings, and sampling configuration.

        :param scope_view: A dictionary containing ScopeView settings.
        """
        for le, var in zip(self.scope_var_lines, scope_view.get("variables", [])):
            le.setText(var)
        for cb, trigger in zip(
            self.trigger_var_checkbox, scope_view.get("trigger", [])
        ):
            cb.setChecked(trigger)
        self.triggerVariable = scope_view.get("trigger_variable", "")
        self.trigger_level_edit.setText(scope_view.get("trigger_level", ""))
        self.trigger_delay_edit.setText(scope_view.get("trigger_delay", ""))
        self.trigger_edge_combo.setCurrentText(scope_view.get("trigger_edge", ""))
        self.trigger_mode_combo.setCurrentText(scope_view.get("trigger_mode", ""))
        self.sample_time_factor.setText(scope_view.get("sample_time_factor", ""))
        self.single_shot_checkbox.setChecked(scope_view.get("single_shot", False))

    def load_tab3_view(self, tab3_view):
        """Loads the configuration settings for Tab 3 (WatchView).

        This includes variables, values, scaling, offsets, scaled values, and live status.

        :param tab3_view: A dictionary containing Tab 3 settings.
        """
        self.clear_tab3()
        for var, val, sc, off, sv, live in zip(
            tab3_view.get("variables", []),
            tab3_view.get("values", []),
            tab3_view.get("scaling", []),
            tab3_view.get("offsets", []),
            tab3_view.get("scaled_values", []),
            tab3_view.get("live", []),
        ):
            self.add_variable_row()
            self.variable_line_edits[-1].setText(var)
            self.value_line_edits[-1].setText(val)
            self.scaling_edits_tab3[-1].setText(sc)
            self.offset_edits_tab3[-1].setText(off)
            self.scaled_value_edits_tab3[-1].setText(sv)
            self.live_tab3[-1].setChecked(live)

    def attempt_connection(self):
        """Attempt to connect to the selected port and ELF file."""
        if self.elf_file_loaded:
            try:
                self.toggle_connection()  # Trigger connection
                if self.ser and self.ser.is_open:
                    return True
            except Exception as e:
                logging.error(f"Connection failed: {e}")
                self.handle_error(f"Connection failed: {e}")
        return False

    def is_connected(self):
        """Check if the serial connection is established and the device is connected."""
        return self.ser is not None and self.ser.is_open

    def clear_tab3(self):
        """Remove all variable rows in Tab 3 efficiently."""
        if not self.row_widgets:  # Check if there is anything to clear
            return  # Skip clearing if already empty

        # Block updates to the GUI while making changes
        self.tab3.layout().blockSignals(True)
        try:
            while self.row_widgets:
                for widget in self.row_widgets.pop():
                    widget.setVisible(False)  # Hide widget to improve performance
                    self.watchview_grid.removeWidget(widget)  # Remove widget from grid
                    widget.deleteLater()  # Schedule widget for deletion

            self.current_row = 1  # Reset the row count
        finally:
            self.tab3.layout().blockSignals(False)  # Ensure signals are re-enabled
            self.tab3.layout().update()  # Force an update to the layout

    def setup_tab3(self):
        """Set up the third tab (WatchView Only) with Add/Remove Variable buttons and live functionality."""
        self.tab3.layout = QVBoxLayout()
        self.tab3.setLayout(self.tab3.layout)

        # Add a scroll area to the layout
        scroll_area = QScrollArea()
        scroll_area_widget = QWidget()  # Widget to hold the scroll area content
        self.tab3.layout.addWidget(scroll_area)

        # Create a vertical layout inside the scroll area
        scroll_area_layout = QVBoxLayout(scroll_area_widget)
        scroll_area_widget.setLayout(scroll_area_layout)

        scroll_area.setWidget(scroll_area_widget)
        scroll_area.setWidgetResizable(True)  # Make the scroll area resizable

        # Create grid layout for adding rows similar to WatchView
        self.watchview_grid = QGridLayout()
        scroll_area_layout.addLayout(self.watchview_grid)

        # Set margins and spacing to remove excess gaps
        self.watchview_grid.setContentsMargins(0, 0, 0, 0)  # Remove margins
        self.watchview_grid.setVerticalSpacing(
            2
        )  # Reduce vertical spacing between rows
        self.watchview_grid.setHorizontalSpacing(
            5
        )  # Reduce horizontal spacing between columns

        # Add header row for the grid with proper alignment and size policy
        headers = [
            "Live",
            "Variable",
            "Value",
            "Scaling",
            "Offset",
            "Scaled Value",
            "Unit",
            "Remove",
        ]
        for i, header in enumerate(headers):
            label = QLabel(header)
            label.setAlignment(Qt.AlignCenter)  # Center align the headers
            label.setSizePolicy(
                QSizePolicy.Minimum, QSizePolicy.Fixed
            )  # Prevent labels from stretching vertically
            self.watchview_grid.addWidget(label, 0, i)

        # Set column stretch to allow the variable field to resize
        self.watchview_grid.setColumnStretch(1, 5)  # Column for 'Variable'
        self.watchview_grid.setColumnStretch(2, 2)  # Column for 'Value'
        self.watchview_grid.setColumnStretch(3, 1)  # Column for 'Scaling'
        self.watchview_grid.setColumnStretch(4, 1)  # Column for 'Offset'
        self.watchview_grid.setColumnStretch(5, 1)  # Column for 'Scaled Value'
        self.watchview_grid.setColumnStretch(6, 1)  # Column for 'Unit'

        # Keep track of the current row count
        self.current_row = 1

        # Timer for updating live variables
        self.live_update_timer = QTimer()
        self.live_update_timer.timeout.connect(self.update_live_variables)
        self.live_update_timer.start(500)  # Set the update interval (500 ms)

        # Store references to live checkboxes and variables
        self.live_tab3 = []
        self.variable_line_edits = []
        self.value_line_edits = []
        self.row_widgets = []

        # Add button to add more variables at the bottom
        self.add_variable_button = QPushButton("Add Variable")
        scroll_area_layout.addWidget(self.add_variable_button, alignment=Qt.AlignBottom)
        self.add_variable_button.clicked.connect(self.add_variable_row)

        # Add Load and Save Config buttons
        self.save_button_tab3 = QPushButton("Save Config")
        self.load_button_tab3 = QPushButton("Load Config")
        self.save_button_tab3.setFixedSize(100, 30)
        self.load_button_tab3.setFixedSize(100, 30)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button_tab3)
        button_layout.addWidget(self.load_button_tab3)
        scroll_area_layout.addLayout(button_layout)

        # Connect buttons to their functions
        self.save_button_tab3.clicked.connect(self.save_config)
        self.load_button_tab3.clicked.connect(self.load_config)

        # Adjust the scroll area margins to remove any additional gaps
        scroll_area_layout.setContentsMargins(0, 0, 0, 0)

    @pyqtSlot()
    def add_variable_row(self):
        """Add a row of widgets to represent a variable in the WatchView Only tab with live functionality."""
        row = self.current_row

        # Create widgets for the row
        live_checkbox = QCheckBox(self)
        variable_edit = QLineEdit(self)
        value_edit = QLineEdit(self)
        scaling_edit = QLineEdit(self)
        offset_edit = QLineEdit(self)
        scaled_value_edit = QLineEdit(self)
        unit_edit = QLineEdit(self)
        remove_button = QPushButton("Remove", self)

        # Set default values for scaling and offset
        scaling_edit.setText("1")  # Default scaling to 1
        offset_edit.setText("0")  # Default offset to 0

        # Set placeholder text for variable search (like in WatchView)
        variable_edit.setPlaceholderText("Search Variable")

        # Make scaled value read-only
        scaled_value_edit.setReadOnly(True)

        # Set size policies to make the variable name and value resize dynamically
        variable_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Add the widgets to the grid layout
        self.watchview_grid.addWidget(live_checkbox, row, 0)
        self.watchview_grid.addWidget(variable_edit, row, 1)
        self.watchview_grid.addWidget(value_edit, row, 2)
        self.watchview_grid.addWidget(scaling_edit, row, 3)
        self.watchview_grid.addWidget(offset_edit, row, 4)
        self.watchview_grid.addWidget(scaled_value_edit, row, 5)
        self.watchview_grid.addWidget(unit_edit, row, 6)
        self.watchview_grid.addWidget(remove_button, row, 7)

        # Set column stretch to allow the variable field to resize
        self.watchview_grid.setColumnStretch(1, 5)  # Column for 'Variable'
        self.watchview_grid.setColumnStretch(2, 2)  # Column for 'Value'
        self.watchview_grid.setColumnStretch(3, 1)  # Column for 'Scaling'
        self.watchview_grid.setColumnStretch(4, 1)  # Column for 'Offset'
        self.watchview_grid.setColumnStretch(5, 1)  # Column for 'Scaled Value'
        self.watchview_grid.setColumnStretch(6, 1)  # Column for 'Unit'

        # Connect remove button to function to remove the row
        remove_button.clicked.connect(
            lambda: self.remove_variable_row(
                live_checkbox,
                variable_edit,
                value_edit,
                scaling_edit,
                offset_edit,
                scaled_value_edit,
                unit_edit,
                remove_button,
            )
        )

        # Connect the variable search to the dialog
        variable_edit.installEventFilter(self)

        # Connect value editing to set value using handle_putram when Enter is pressed
        value_edit.editingFinished.connect(
            lambda: self.handle_variable_putram(variable_edit.text(), value_edit)
        )

        # Connect scaling and offset fields to recalculate the scaled value
        scaling_edit.editingFinished.connect(
            lambda: self.update_scaled_value_tab3(
                value_edit, scaling_edit, offset_edit, scaled_value_edit
            )
        )
        offset_edit.editingFinished.connect(
            lambda: self.update_scaled_value_tab3(
                value_edit, scaling_edit, offset_edit, scaled_value_edit
            )
        )

        # Calculate and show the scaled value immediately using the default scaling and offset
        self.update_scaled_value_tab3(
            value_edit, scaling_edit, offset_edit, scaled_value_edit
        )

        # Add widgets to the lists for tracking
        self.live_tab3.append(live_checkbox)
        self.variable_line_edits.append(variable_edit)
        self.value_line_edits.append(value_edit)

        # Track scaling and offset for live updates in Tab 3
        self.scaling_edits_tab3.append(scaling_edit)
        self.offset_edits_tab3.append(offset_edit)
        self.scaled_value_edits_tab3.append(scaled_value_edit)

        # Track the row widgets to remove them easily
        self.row_widgets.append(
            (
                live_checkbox,
                variable_edit,
                value_edit,
                scaling_edit,
                offset_edit,
                scaled_value_edit,
                unit_edit,
                remove_button,
            )
        )

        # Increment the current row counter
        self.current_row += 1

    def remove_variable_row(
        self,
        live_checkbox,
        variable_edit,
        value_edit,
        scaling_edit,
        offset_edit,
        scaled_value_edit,
        unit_edit,
        remove_button,
    ):
        """Remove a specific row in the WatchView Only tab."""
        # Remove the widgets from the grid layout
        for widget in [
            live_checkbox,
            variable_edit,
            value_edit,
            scaling_edit,
            offset_edit,
            scaled_value_edit,
            unit_edit,
            remove_button,
        ]:
            widget.deleteLater()

        # Remove the corresponding widgets from the tracking lists
        self.live_tab3.remove(live_checkbox)
        self.variable_line_edits.remove(variable_edit)
        self.value_line_edits.remove(value_edit)
        self.scaling_edits_tab3.remove(scaling_edit)  # Remove from a scaling list
        self.offset_edits_tab3.remove(offset_edit)  # Remove from offset list
        self.scaled_value_edits_tab3.remove(
            scaled_value_edit
        )  # Remove from a scaled value list

        # Remove the widget references from the row widgets tracking
        self.row_widgets.remove(
            (
                live_checkbox,
                variable_edit,
                value_edit,
                scaling_edit,
                offset_edit,
                scaled_value_edit,
                unit_edit,
                remove_button,
            )
        )

        # Decrement the row count
        self.current_row -= 1

        # Adjust the layout for remaining rows
        self.rearrange_grid()

    def rearrange_grid(self):
        """Rearrange the grid layout after a row has been removed."""
        # Clear the entire grid layout
        for i in reversed(range(self.watchview_grid.count())):
            widget = self.watchview_grid.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Add the headers again
        headers = [
            "Live",
            "Variable",
            "Value",
            "Scaling",
            "Offset",
            "Scaled Value",
            "Unit",
            "Remove",
        ]
        for i, header in enumerate(headers):
            self.watchview_grid.addWidget(QLabel(header), 0, i)

        # Add the remaining rows back to the grid
        for row, widgets in enumerate(self.row_widgets, start=1):
            for col, widget in enumerate(widgets):
                self.watchview_grid.addWidget(widget, row, col)

    def eventFilter(self, source, event):  # noqa: N802 #Overriding 3rd party function.
        """Event filter to handle line edit click events for variable selection."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if isinstance(source, QLineEdit):
                dialog = VariableSelectionDialog(self.VariableList, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected_variable = dialog.selected_variable
                    if selected_variable:
                        source.setText(selected_variable)
                        # Get the initial value from the microcontroller (if applicable)
                        try:
                            self.handle_variable_getram(
                                selected_variable,
                                self.value_line_edits[
                                    self.variable_line_edits.index(source)
                                ],
                            )
                        except Exception as e:
                            print(e)

        return super().eventFilter(source, event)

    def update_live_variables(self):
        """Update the values of variables in real-time if live checkbox is checked."""
        for (
            checkbox,
            variable_edit,
            value_edit,
            scaling_edit,
            offset_edit,
            scaled_value_edit,
        ) in zip(
            self.live_tab3,
            self.variable_line_edits,
            self.value_line_edits,
            self.scaling_edits_tab3,
            self.offset_edits_tab3,
            self.scaled_value_edits_tab3,
        ):

            if checkbox.isChecked() and variable_edit.text():
                # Fetch the variable value from the microcontroller
                variable_name = variable_edit.text()
                self.handle_variable_getram(variable_name, value_edit)

                # Update the scaled value in real-time based on the raw value, scaling, and offset
                self.update_scaled_value_tab3(
                    value_edit, scaling_edit, offset_edit, scaled_value_edit
                )

    @pyqtSlot()
    def update_scaled_value_tab3(
        self, value_edit, scaling_edit, offset_edit, scaled_value_edit
    ):
        """Updates the scaled value in both Tab 1 and Tab 3 based on the provided scaling factor and offset.

        Args:
            value_edit : Input field for the raw value.
            scaling_edit : Input field for the scaling factor.
            offset_edit : Input field for the offset.
            scaled_value_edit : Output field for the scaled value.
        """
        try:
            value = float(value_edit.text())
            scaling = float(scaling_edit.text()) if scaling_edit.text() else 1.0
            offset = float(offset_edit.text()) if offset_edit.text() else 0.0
            scaled_value = (scaling * value) + offset
            scaled_value_edit.setText(f"{scaled_value:.2f}")
        except ValueError as e:
            logging.error(f"Error updating scaled value: {e}")
            scaled_value_edit.setText("0.00")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2cscopeGui()
    ex.show()
    sys.exit(app.exec_())
