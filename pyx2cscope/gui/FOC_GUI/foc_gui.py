"""replicate of X2Cscpope."""
import logging
logging.basicConfig(level=logging.WARNING)
import os
import sys
import time
from collections import deque
from datetime import datetime
import json

import matplotlib
import numpy as np
import pyqtgraph as pg  # Added pyqtgraph for interactive plotting
import serial.tools.list_ports  # Import the serial module to fix the NameError
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import QFileInfo, QMutex, QRegExp, QSettings, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QStyleFactory,
    QSizePolicy,
    QDialog,
    QListWidget,
    QDialogButtonBox,
)

from pyx2cscope.gui import img as img_src
from pyx2cscope.xc2scope import TriggerConfig, X2CScope

logging.basicConfig(level=logging.DEBUG)

matplotlib.use("QtAgg")  # This sets the backend to Qt for Matplotlib

class VariableSelectionDialog(QDialog):
    """Dialog for selecting a variable from a list with search functionality."""

    def __init__(self, variables, parent=None):
        super().__init__(parent)
        self.variables = variables
        self.selected_variable = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Select Variable")
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

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept_selection)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def filter_variables(self, text):
        self.variable_list.clear()
        filtered_variables = [var for var in self.variables if text.lower() in var.lower()]
        self.variable_list.addItems(filtered_variables)

    def accept_selection(self):
        selected_items = self.variable_list.selectedItems()
        if selected_items:
            self.selected_variable = selected_items[0].text()
            self.accept()

class X2cscopeGui(QMainWindow):
    """Main GUI class for the pyX2Cscope application."""

    def __init__(self):
        """Initializing all the elements required."""
        super().__init__()

        self.triggerVariable = None
        self.initialize_variables()
        self.init_ui()

    def initialize_variables(self):
        """Initialize instance variables."""
        self.sampling_active = False
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
        self.selected_var_indices = [0, 0, 0, 0, 0]  # List to store selected variable indices
        self.selected_variables = []  # List to store selected variables
        self.previous_selected_variables = {}  # Dictionary to store previous selections
        decimal_regex = QRegExp("-?[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

        self.plot_data = deque(maxlen=250)  # Store plot data for all variables
        self.plot_colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']  #colours for different plot
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

    def create_tabs(self):
        """Create tabs for the main window."""
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab_widget.addTab(self.tab1, "WatchView")
        self.tab_widget.addTab(self.tab2, "ScopeView")

    def setup_tabs(self):
        """Set up the contents of each tab."""
        self.setup_tab1()
        self.setup_tab2()

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

        for line_edit in [self.line_edit1, self.line_edit2, self.line_edit3, self.line_edit4, self.line_edit5]:
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Select Variable")
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
        """Initializing timer."""
        self.timer5 = QTimer()
        self.timer4 = QTimer()
        self.timer3 = QTimer()
        self.timer2 = QTimer()
        self.timer1 = QTimer()

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
        self.setup_baud_layout(grid_layout)
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

        # Trigger Configuration Group Box
        trigger_group = QGroupBox("Trigger Configuration")
        trigger_layout = QVBoxLayout()
        trigger_group.setLayout(trigger_layout)

        grid_layout_trigger = QGridLayout()
        trigger_layout.addLayout(grid_layout_trigger)

        self.single_shot_checkbox = QCheckBox("Single Shot")  # Add Single Shot checkbox
        self.sample_time_factor = QLineEdit("1")
        self.sample_time_factor.setValidator(self.decimal_validator)
        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems(["Auto", "Triggered"])
        self.trigger_edge_combo = QComboBox()
        self.trigger_edge_combo.addItems(["Rising", "Falling"])
        self.trigger_level_edit = QLineEdit()
        self.trigger_level_edit.setValidator(self.decimal_validator)
        self.trigger_delay_edit = QLineEdit()
        self.trigger_delay_edit.setValidator(self.decimal_validator)

        self.scope_sample_button = QPushButton("Sample")
        self.scope_sample_button.setFixedSize(100, 30)  # Set the button size
        self.scope_sample_button.clicked.connect(self.start_sampling)

        grid_layout_trigger.addWidget(self.single_shot_checkbox, 0, 0, 1,
                                      2)  # Add the Single Shot checkbox to the layout
        grid_layout_trigger.addWidget(QLabel("Sample Time Factor"), 1, 0)
        grid_layout_trigger.addWidget(self.sample_time_factor, 1, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Mode:"), 2, 0)
        grid_layout_trigger.addWidget(self.trigger_mode_combo, 2, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Edge:"), 3, 0)
        grid_layout_trigger.addWidget(self.trigger_edge_combo, 3, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Level:"), 4, 0)
        grid_layout_trigger.addWidget(self.trigger_level_edit, 4, 1)
        grid_layout_trigger.addWidget(QLabel("Trigger Delay:"), 5, 0)
        grid_layout_trigger.addWidget(self.trigger_delay_edit, 5, 1)
        grid_layout_trigger.addWidget(self.scope_sample_button, 8, 0)

        # Variable Selection Group Box
        variable_group = QGroupBox("Variable Selection")
        variable_layout = QVBoxLayout()
        variable_group.setLayout(variable_layout)

        grid_layout_variable = QGridLayout()
        variable_layout.addLayout(grid_layout_variable)

        self.scope_var_lines = [QLineEdit() for _ in range(7)]
        self.trigger_var_checkbox = [QCheckBox() for _ in range(7)]
        self.scope_channel_checkboxes = [QCheckBox() for _ in range(7)]  # Add checkboxes for each channel
        self.scope_scaling_boxes = [QLineEdit("1") for _ in range(7)]  # Add scaling boxes

        for checkbox in self.scope_channel_checkboxes:
            checkbox.setChecked(True)  # Check all checkboxes by default

        for line_edit in self.scope_var_lines:
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText("Select Variable")
            line_edit.installEventFilter(self)

        # Add "Select Variable" label
        grid_layout_variable.addWidget(QLabel("Select Variable"), 0, 1)

        # Add "Trigger", "Scale", and "Show" labels spanning across multiple columns
        trigger_label = QLabel("Trigger")
        trigger_label.setAlignment(Qt.AlignCenter)  # Center align the label
        grid_layout_variable.addWidget(trigger_label, 0, 0)

        scale_label = QLabel("Scale")  # Add a label for scaling
        scale_label.setAlignment(Qt.AlignCenter)
        grid_layout_variable.addWidget(scale_label, 0, 2)

        show_label = QLabel("Plot")
        show_label.setAlignment(Qt.AlignCenter)  # Center align the label
        grid_layout_variable.addWidget(show_label, 0, 3)

        for i, (line_edit, trigger_checkbox, scale_box, show_checkbox) in enumerate(
                zip(self.scope_var_lines, self.trigger_var_checkbox, self.scope_scaling_boxes,
                    self.scope_channel_checkboxes)):
            line_edit.setMinimumHeight(20)
            trigger_checkbox.setMinimumHeight(20)
            show_checkbox.setMinimumHeight(20)  # Set minimum height for channel checkboxes
            scale_box.setMinimumHeight(20)  # Set minimum height for scaling boxes
            scale_box.setFixedSize(50, 20)  # Set fixed size for scaling boxes
            scale_box.setValidator(self.decimal_validator)  # Validate as float

            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            grid_layout_variable.addWidget(trigger_checkbox, i + 1, 0)
            grid_layout_variable.addWidget(line_edit, i + 1, 1)
            grid_layout_variable.addWidget(scale_box, i + 1, 2)  # Add scaling boxes to layout
            grid_layout_variable.addWidget(show_checkbox, i + 1, 3)  # Add channel checkboxes to layout

            trigger_checkbox.stateChanged.connect(lambda state, x=i: self.handle_scope_checkbox_change(state, x))
            scale_box.editingFinished.connect(self.update_scope_plot)  # Connect scaling box change to plot update
            show_checkbox.stateChanged.connect(self.update_scope_plot)  # Connect the state change to update_scope_plot

        # Add the group boxes to the main layout with stretch factors
        main_grid_layout.addWidget(trigger_group, 0, 0)
        main_grid_layout.addWidget(variable_group, 0, 1)

        # Set the column stretch factors to make the variable group larger
        main_grid_layout.setColumnStretch(0, 1)  # Trigger configuration box
        main_grid_layout.setColumnStretch(1, 3)  # Variable selection box

        # Add the plot widget for scope view
        self.scope_plot_widget = pg.PlotWidget(title="Scope Plot")
        self.scope_plot_widget.setBackground('w')
        self.scope_plot_widget.addLegend()  # Add legend to the plot widget
        self.scope_plot_widget.showGrid(x=True, y=True)  # Enable grid lines
        self.tab2.layout.addWidget(self.scope_plot_widget)

        # Add Save and Load buttons
        self.save_button_scope = QPushButton("Save Config")
        self.load_button_scope = QPushButton("Load Config")
        self.save_button_scope.setFixedSize(100, 30)
        self.load_button_scope.setFixedSize(100, 30)
        self.save_button_scope.clicked.connect(self.save_config)
        self.load_button_scope.clicked.connect(self.load_config)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button_scope)
        button_layout.addWidget(self.load_button_scope)
        self.tab2.layout.addLayout(button_layout)

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
        """Set up the port selection layout."""
        port_layout = QGridLayout()  # Use QVBoxLayout to align items vertically
        port_label = QLabel("Select Port:")
        self.port_combo.setFixedSize(100, 25)  # Set fixed size for the port combo box

        refresh_button = QPushButton()
        refresh_button.setFixedSize(25, 25)
        refresh_button.clicked.connect(self.refresh_ports)
        refresh_img = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        refresh_button.setIcon(QIcon(refresh_img))

        self.select_file_button.setEnabled(True)
        self.select_file_button.clicked.connect(self.select_elf_file)

        port_layout.addWidget(port_label,0,0)
        port_layout.addWidget(self.port_combo,0,2)
        port_layout.addWidget(refresh_button,0,1)
        port_layout.setAlignment(Qt.AlignLeft)  # Align all widgets to the left

        layout.addLayout(port_layout, 1, 0)

    def setup_baud_layout(self, layout):
        """Set up the baud rate selection layout."""
        baud_layout = QHBoxLayout()  # Use QVBoxLayout to align items vertically
        baud_label = QLabel("Select Baud Rate:")
        self.baud_combo.setFixedSize(100, 25)  # Set fixed size for the baud combo box

        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo)
        baud_layout.setAlignment(Qt.AlignRight)  # Align all widgets to the left

        self.baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        default_baud_rate = "115200"
        index = self.baud_combo.findText(default_baud_rate, Qt.MatchFixedString)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

        layout.addLayout(baud_layout, 2, 0)

    def setup_sampletime_layout(self, layout):
        """Set up the sample time layout."""
        self.Connect_button.clicked.connect(self.toggle_connection)
        self.Connect_button.setFixedSize(100, 30)
        self.Connect_button.setMinimumHeight(30)

        self.sampletime.setText("500")
        self.sampletime.setValidator(self.decimal_validator)
        self.sampletime.editingFinished.connect(self.sampletime_edit)
        self.sampletime.setFixedSize(50, 20)

        sampletime_layout = QHBoxLayout()
        sampletime_layout.addWidget(QLabel("Sampletime"), alignment=Qt.AlignLeft)
        sampletime_layout.addWidget(self.sampletime, alignment=Qt.AlignLeft)
        sampletime_layout.addWidget(QLabel("ms"), alignment=Qt.AlignLeft)
        sampletime_layout.addStretch(1)
        sampletime_layout.addWidget(self.Connect_button, alignment=Qt.AlignRight)

        layout.addLayout(sampletime_layout, 3, 0)
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
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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
            plot_checkbox.stateChanged.connect(lambda state, x=row_index - 1: self.update_watch_plot())

        layout.addLayout(self.grid_layout, 5, 0)

        # Add the plot widget for watch view
        self.watch_plot_widget = pg.PlotWidget(title="Watch Plot")
        self.watch_plot_widget.setBackground('w')
        self.watch_plot_widget.addLegend()  # Add legend to the plot widget
        self.watch_plot_widget.showGrid(x=True, y=True)  # Enable grid lines
        self.tab1.layout.addWidget(self.watch_plot_widget)

    def setup_connections(self):
        """Set up connections for various widgets."""
        self.plot_button.clicked.connect(self.plot_data_plot)

        for timer, line_edit, value_var in zip(self.timer_list, self.line_edit_boxes, self.Value_var_boxes):
            timer.timeout.connect(lambda cb=line_edit, v_var=value_var: self.handle_var_update(cb.text(), v_var))

        for line_edit, value_var in zip(self.line_edit_boxes, self.Value_var_boxes):
            value_var.editingFinished.connect(
                lambda cb=line_edit, v_var=value_var: self.handle_variable_putram(cb.text(), v_var)
            )

        self.connect_editing_finished()

        for timer, live_var in zip(self.timer_list, self.live_checkboxes):
            live_var.stateChanged.connect(lambda state, lv=live_var, tm=timer: self.var_live(lv, tm))

        self.slider_var1.setMinimum(-32768)
        self.slider_var1.setMaximum(32767)
        self.slider_var1.setEnabled(False)
        self.slider_var1.valueChanged.connect(self.slider_var1_changed)

        self.plot_update_timer.timeout.connect(self.update_watch_plot)  # Connect the QTimer to the update method

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
                time_diff = (timestamp - last_timestamp).total_seconds() * 1000  # to convert time in ms.
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

            data = np.array(self.plot_data, dtype=object).T
            time_diffs = np.array(data[1], dtype=float)
            values = [np.array(data[i], dtype=float) for i in range(2, 7)]

            # Keep the last plot lines to avoid clearing and recreate them
            plot_lines = {}
            for item in self.watch_plot_widget.plotItem.items:
                if isinstance(item, pg.PlotDataItem):
                    plot_lines[item.name()] = item

            for i, (value, line_edit, plot_var) in enumerate(zip(values, self.line_edit_boxes, self.plot_checkboxes)):
                if plot_var.isChecked() and line_edit.text() != "":
                    if line_edit.text() in plot_lines:
                        plot_line = plot_lines[line_edit.text()]
                        plot_line.setData(np.cumsum(time_diffs), value)
                    else:
                        self.watch_plot_widget.plot(np.cumsum(time_diffs), value,
                                                    pen=pg.mkPen(color=self.plot_colors[i], width=2),
                                                    # Thicker plot line
                                                    name=line_edit.text())

            self.watch_plot_widget.setLabel('left', 'Value')
            self.watch_plot_widget.setLabel('bottom', 'Time', units='ms')
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
            for channel, data in self.x2cscope.get_scope_channel_data().items():
                data_storage[channel] = data

            self.scope_plot_widget.clear()

            for i, (channel, data) in enumerate(data_storage.items()):
                checkbox_state = self.scope_channel_checkboxes[i].isChecked()
                logging.debug(f"Channel {channel}: Checkbox is {'checked' if checkbox_state else 'unchecked'}")
                if checkbox_state:  # Check if the checkbox is checked
                    scale_factor = float(self.scope_scaling_boxes[i].text())  # Get the scaling factor
                    time_values = np.array([j * 0.001 for j in range(len(data))], dtype=float)  # milliseconds
                    data = np.array(data, dtype=float) * scale_factor  # Apply the scaling factor
                    self.scope_plot_widget.plot(time_values, data, pen=pg.mkPen(color=self.plot_colors[i], width=2),
                                                name=f"Channel {channel}")
                    logging.debug(f"Plotting channel {channel} with color {self.plot_colors[i]}")
                else:
                    logging.debug(f"Not plotting channel {channel}")

            self.scope_plot_widget.setLabel('left', 'Value')
            self.scope_plot_widget.setLabel('bottom', 'Time', units='ms')
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
        """Displays an error message in a message box.

        Args:
            error_message (str): The error message to display.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Error")
        msg_box.setText(error_message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

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
            self.handle_error("Select Variable")
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
        """Open a file dialog to select an ELF file.

        This method opens a file dialog for the user to select an ELF file.
        The selected file path is then stored in settings for later use.
        """
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("ELF Files (*.elf)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        fileinfo = QFileInfo(self.file_path)
        self.select_file_button.setText(fileinfo.fileName())

        if self.file_path:
            file_dialog.setDirectory(self.file_path)
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.file_path = selected_files[0]
                self.settings.setValue("file_path", self.file_path)
                self.select_file_button.setText(QFileInfo(self.file_path).fileName())

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

        if self.ser is None or not self.ser.is_open:
            for timer in self.timer_list:
                if timer.isActive():
                    timer.stop()
            self.plot_data.clear()
            self.save_selected_variables()  # Save the current selections before disconnecting
            self.connect_serial()
        else:
            self.disconnect_serial()

    def save_selected_variables(self):
        """Save the current selections of variables in WatchView and ScopeView."""
        self.previous_selected_variables = {
            'watch': [(le.text(), le.text()) for le in self.line_edit_boxes],
            'scope': [(le.text(), le.text()) for le in self.scope_var_lines]
        }

    def restore_selected_variables(self):
        """Restore the previously selected variables in WatchView and ScopeView."""
        if 'watch' in self.previous_selected_variables:
            for le, (var, _) in zip(self.line_edit_boxes, self.previous_selected_variables['watch']):
                le.setText(var)

        if 'scope' in self.previous_selected_variables:
            for le, (var, _) in zip(self.scope_var_lines, self.previous_selected_variables['scope']):
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

    def connect_serial(self):
        """Establish a serial connection based on the current UI settings.

        This method sets up a serial connection using the selected port and
        baud rate. It also initializes the variable factory and updates the
        UI to reflect the connection state.
        """
        try:
            if self.ser is not None and self.ser.is_open:
                self.disconnect_serial()

            port = self.port_combo.currentText()
            baud_rate = int(self.baud_combo.currentText())

            self.x2cscope = X2CScope(port=port, elf_file=self.file_path, baud_rate=baud_rate)
            self.ser = self.x2cscope.interface
            self.VariableList = self.x2cscope.list_variables()
            if self.VariableList:
                self.VariableList.insert(0, "None")
            else:
                return
            self.refresh_line_edit()
            logging.info("Serial Port Configuration:")
            logging.info(f"Port: {port}")
            logging.info(f"Baud Rate: {baud_rate}")

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

            timer_list = []
            for i in range(len(self.live_checkboxes)):
                timer_list.append((self.live_checkboxes[i], self.timer_list[i]))

            for live_var, timer in timer_list:
                if live_var.isChecked():
                    timer.start(self.timerValue)

            self.plot_update_timer.start(self.timerValue)  # Start the continuous plot update

            self.restore_selected_variables()  # Restore the selections after reconnecting

        except Exception as e:
            error_message = f"Error while connecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def close_plot_window(self):
        """Close the plot window if it is open.

        This method stops the animation and closes the plot window, if it is open.
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
        try:
            if self.sampling_active:
                self.sampling_active = False
                self.scope_sample_button.setText("Sample")
                logging.info("Stopped sampling.")
            else:
                self.x2cscope.clear_all_scope_channel()
                for line_edit in self.scope_var_lines:
                    variable_name = line_edit.text()
                    if variable_name and variable_name != "None":
                        variable = self.x2cscope.get_variable(variable_name)
                        self.x2cscope.add_scope_channel(variable)

                self.x2cscope.set_sample_time(int(self.sample_time_factor.text()))  # set sample time factor
                self.sampling_active = True
                self.configure_trigger()
                self.scope_sample_button.setText("Stop")
                logging.info("Started sampling.")
                self.x2cscope.request_scope_data()
                self.sample_scope_data(single_shot=self.single_shot_checkbox.isChecked())
        except Exception as e:
            error_message = f"Error starting sampling: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def configure_trigger(self):
        """Configure the trigger settings."""
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
                        trigger_level = float(trigger_level_text)
                        print(trigger_level)
                    except ValueError:
                        logging.error(f"Invalid trigger level value: {trigger_level_text}")
                        self.handle_error(f"Invalid trigger level value: {trigger_level_text}")
                        return

                if not trigger_delay_text:
                    trigger_delay = 0
                else:
                    try:
                        trigger_delay = int(trigger_delay_text)
                    except ValueError:
                        logging.error(f"Invalid trigger delay value: {trigger_delay_text}")
                        self.handle_error(f"Invalid trigger delay value: {trigger_delay_text}")
                        return

                trigger_edge = 0 if self.trigger_edge_combo.currentText() == "Rising" else 1
                trigger_mode = 0 if self.trigger_mode_combo.currentText() == "Auto" else 1

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
        """Sample the scope data."""
        try:
            while self.sampling_active:
                if self.x2cscope.is_scope_data_ready():
                    logging.info("Scope data is ready.")

                    data_storage = {}
                    for channel, data in self.x2cscope.get_scope_channel_data().items():
                        data_storage[channel] = data

                    self.scope_plot_widget.clear()
                    for i, (channel, data) in enumerate(data_storage.items()):
                        if self.scope_channel_checkboxes[i].isChecked():  # Check if the channel is enabled
                            scale_factor = float(self.scope_scaling_boxes[i].text())  # Get the scaling factor
                            time_values = np.array([j * 0.001 for j in range(len(data))], dtype=float)  # milliseconds
                            data = np.array(data, dtype=float)  * scale_factor  # Apply the scaling factor
                            self.scope_plot_widget.plot(time_values, data,
                                                        pen=pg.mkPen(color=self.plot_colors[i], width=2),
                                                        # Thicker plot line
                                                        name=f"Channel {channel}")

                    self.scope_plot_widget.setLabel('left', 'Value')
                    self.scope_plot_widget.setLabel('bottom', 'Time', units='ms')
                    self.scope_plot_widget.showGrid(x=True, y=True)  # Enable grid lines

                    if single_shot:
                        break

                    self.x2cscope.request_scope_data()

                QApplication.processEvents()  # Keep the GUI responsive

                time.sleep(0.1)

            self.sampling_active = False
            self.scope_sample_button.setText("Sample")
            logging.info("Data collection complete.")
        except Exception as e:
            error_message = f"Error sampling scope data: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def eventFilter(self, source, event):
        """Event filter to handle line edit click events."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if isinstance(source, QLineEdit):
                dialog = VariableSelectionDialog(self.VariableList, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected_variable = dialog.selected_variable
                    if selected_variable:
                        source.setText(selected_variable)
                        try:
                            self.handle_variable_getram(selected_variable, self.Value_var_boxes[self.line_edit_boxes.index(source)])
                        except Exception as e:
                            print(e)

        return super().eventFilter(source, event)

    def save_config(self):
        """Save the current configuration to a file."""
        config = {
            "watch_view": {
                "variables": [le.text() for le in self.line_edit_boxes],
                "values": [ve.text() for ve in self.Value_var_boxes],
                "scaling": [sc.text() for sc in self.scaling_boxes],
                "offsets": [off.text() for off in self.offset_boxes],
                "plot": [cb.isChecked() for cb in self.plot_checkboxes],
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
            }
        }

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "w") as file:
                json.dump(config, file, indent=4)

    def load_config(self):
        """Load a configuration from a file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "r") as file:
                config = json.load(file)

            watch_view = config.get("watch_view", {})
            scope_view = config.get("scope_view", {})

            for le, var in zip(self.line_edit_boxes, watch_view.get("variables", [])):
                le.setText(var)
            for ve, val in zip(self.Value_var_boxes, watch_view.get("values", [])):
                ve.setText(val)
            for sc, scale in zip(self.scaling_boxes, watch_view.get("scaling", [])):
                sc.setText(scale)
            for off, offset in zip(self.offset_boxes, watch_view.get("offsets", [])):
                off.setText(offset)
            for cb, plot in zip(self.plot_checkboxes, watch_view.get("plot", [])):
                cb.setChecked(plot)
            for cb, live in zip(self.live_checkboxes, watch_view.get("live", [])):
                cb.setChecked(live)

            for le, var in zip(self.scope_var_lines, scope_view.get("variables", [])):
                le.setText(var)
            for cb, trigger in zip(self.trigger_var_checkbox, scope_view.get("trigger", [])):
                cb.setChecked(trigger)
            for sc, scale in zip(self.scope_scaling_boxes, scope_view.get("scale", [])):
                sc.setText(scale)
            for cb, show in zip(self.scope_channel_checkboxes, scope_view.get("show", [])):
                cb.setChecked(show)

            self.triggerVariable = scope_view.get("trigger_variable", "")
            self.trigger_level_edit.setText(scope_view.get("trigger_level", ""))
            self.trigger_delay_edit.setText(scope_view.get("trigger_delay", ""))
            self.trigger_edge_combo.setCurrentText(scope_view.get("trigger_edge", ""))
            self.trigger_mode_combo.setCurrentText(scope_view.get("trigger_mode", ""))
            self.sample_time_factor.setText(scope_view.get("sample_time_factor", ""))
            self.single_shot_checkbox.setChecked(scope_view.get("single_shot", False))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2cscopeGui()
    ex.show()
    sys.exit(app.exec_())
