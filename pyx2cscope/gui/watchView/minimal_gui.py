"""This is the minimal gui to test the pyx2cscope interface library."""

import logging
import os
import sys
import time
from collections import deque
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import serial.tools.list_ports
from matplotlib.animation import FuncAnimation
from PyQt5 import QtGui
from PyQt5.QtCore import QFileInfo, QMutex, QRegExp, QSettings, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QWidget,
)

from pyx2cscope import set_logger
from pyx2cscope.gui import img as img_src
from pyx2cscope.xc2scope import X2CScope

set_logger(logging.INFO, __name__)
matplotlib.use("QtAgg")  # This sets the backend to Qt for Matplotlib

class X2cscopeGui(QMainWindow):
    """Main GUI class for the pyX2Cscope application.

    This class creates and manages the GUI for pyX2Cscope, providing an interface
    to connect to a microcontroller, select variables for monitoring, and plot their values.
    """

    def __init__(self):
        """Initializing all the elements required."""
        super().__init__()
        self.initialize_variables()
        self.init_ui()

    def initialize_variables(self):
        """Initialize instance variables."""
        self.offset_boxes = None
        self.plot_checkboxes = None
        self.scaled_value_boxes = None
        self.scaling_boxes = None
        self.Value_var_boxes = None
        self.combo_boxes = None
        self.live_checkboxes = None
        self.timer_list = None
        self.VariableList = []
        self.old_Variablelist = []
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
        self.timer()
        self.offset_var()
        self.plot_var_check()
        self.scailing_var()
        self.value_var()
        self.live_var()
        self.scaled_value()
        self.combo_box()
        self.sampletime = QLineEdit()
        self.unit_var()
        self.Connect_button = QPushButton("Connect")
        self.baud_combo = QComboBox()
        self.select_file_button = QPushButton("Select elf file")
        self.error_shown = False
        self.plot_window_open = False
        self.settings = QSettings("MyCompany", "MyApp")
        self.file_path: str = self.settings.value("file_path", "", type=str)
        self.selected_var_indices = [
            0,
            0,
            0,
            0,
            0,
        ]  # List to store selected variable indices
        self.selected_variables = []  # List to store selected variables
        decimal_regex = QRegExp("-?[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

        self.plot_data = deque(maxlen=250)  # Store plot data for all variable.
        self.fig, self.ax = None, None
        self.ani = None
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

    def combo_box(self):
        """Initializing combo boxes."""
        self.combo_box5 = QComboBox()
        self.combo_box4 = QComboBox()
        self.combo_box3 = QComboBox()
        self.combo_box2 = QComboBox()
        self.combo_box1 = QComboBox()
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
    def scailing_var(self):
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
    def init_ui(self):
        """Initializing all the required for GUI."""
        central_widget = QWidget(self)
        self.layout = QGridLayout(central_widget)

        self.setup_port_layout()
        self.setup_baud_layout()
        self.setup_sampletime_layout()

        self.setup_variable_layout()

        self.setup_connections()

        self.setCentralWidget(central_widget)
        self.setWindowTitle("pyX2Cscope")
        mchp_img = os.path.join(os.path.dirname(img_src.__file__), "pyx2cscope.jpg")
        self.setWindowIcon(QtGui.QIcon(mchp_img))

        self.refresh_ports()

    def setup_port_layout(self):
        """Set up the port selection layout."""
        port_layout = QGridLayout()
        port_label = QLabel("Select Port:")

        refresh_button = QPushButton()
        refresh_button.setFixedHeight(10)
        refresh_button.setFixedSize(25, 25)
        refresh_button.clicked.connect(self.refresh_ports)
        refresh_img = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        refresh_button.setIcon(QIcon(refresh_img))

        self.select_file_button.setEnabled(True)
        self.select_file_button.clicked.connect(self.select_elf_file)

        port_layout.addWidget(port_label, 0, 0)
        port_layout.addWidget(self.port_combo, 0, 1)
        port_layout.addWidget(refresh_button, 0, 2)

        self.layout.addLayout(port_layout, 1, 0)

    def setup_baud_layout(self):
        """Set up the baud rate selection layout."""
        baud_layout = QGridLayout()
        baud_label = QLabel("Select Baud Rate:")
        baud_layout.addWidget(baud_label, 0, 0)
        baud_layout.addWidget(self.baud_combo, 0, 1)

        self.baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        default_baud_rate = "115200"
        index = self.baud_combo.findText(default_baud_rate, Qt.MatchFixedString)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

        self.layout.addLayout(baud_layout, 2, 0)

    def setup_sampletime_layout(self):
        """Set up the sample time layout."""
        self.Connect_button.clicked.connect(self.toggle_connection)
        self.Connect_button.setFixedSize(100, 30)

        self.sampletime.setText("500")
        self.sampletime.setValidator(self.decimal_validator)
        self.sampletime.editingFinished.connect(self.sampletime_edit)
        self.sampletime.setFixedSize(30, 20)

        self.box_layout.addWidget(QLabel("Sampletime"), alignment=Qt.AlignLeft)
        self.box_layout.addWidget(self.sampletime, alignment=Qt.AlignLeft)
        self.box_layout.addWidget(QLabel("ms"), alignment=Qt.AlignLeft)
        self.box_layout.addStretch(1)
        self.box_layout.addWidget(self.Connect_button, alignment=Qt.AlignRight)

        self.layout.addWidget(self.select_file_button, 3, 0)
        self.layout.addLayout(self.box_layout, 4, 0)

    def setup_variable_layout(self):
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
        self.combo_boxes = [
            self.combo_box1,
            self.combo_box2,
            self.combo_box3,
            self.combo_box4,
            self.combo_box5,
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
            combo_box,
            value_var,
            scaling_var,
            offset_var,
            scaled_value_var,
            unit_var,
            plot_checkbox,
        ) in enumerate(
            zip(
                self.live_checkboxes,
                self.combo_boxes,
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
            combo_box.setEnabled(False)
            combo_box.setFixedWidth(350)
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
            self.grid_layout.addWidget(combo_box, display_row, 1)
            if display_row == 1:
                self.grid_layout.addWidget(self.slider_var1, display_row + 1, 0, 1, 7)

            self.grid_layout.addWidget(value_var, display_row, 2)
            self.grid_layout.addWidget(scaling_var, display_row, 3)
            self.grid_layout.addWidget(offset_var, display_row, 4)
            self.grid_layout.addWidget(scaled_value_var, display_row, 5)
            self.grid_layout.addWidget(unit_var, display_row, 6)
            self.grid_layout.addWidget(plot_checkbox, display_row, 7)

        self.layout.addLayout(self.grid_layout, 5, 0)
        self.layout.addWidget(self.plot_button, 6, 0)

    def setup_connections(self):
        """Set up connections for various widgets."""
        self.plot_button.clicked.connect(self.plot_data_plot)

        for timer, combo_box, value_var in zip(self.timer_list, self.combo_boxes, self.Value_var_boxes):
            timer.timeout.connect(lambda cb=combo_box, v_var=value_var: self.handle_var_update(cb.currentText(), v_var))

        for combo_box, value_var in zip(self.combo_boxes, self.Value_var_boxes):
            combo_box.currentIndexChanged.connect(
                lambda cb=combo_box, v_var=value_var: self.handle_variable_getram(self.VariableList[cb], v_var)
            )

        self.connect_editing_finished()

        for timer, live_var in zip(self.timer_list, self.live_checkboxes):
            live_var.stateChanged.connect(lambda state, lv=live_var, tm=timer: self.var_live(lv, tm))

        self.slider_var1.setMinimum(-32768)
        self.slider_var1.setMaximum(32767)
        self.slider_var1.setEnabled(False)
        self.slider_var1.valueChanged.connect(self.slider_var1_changed)

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
            self.plot_data.append(
                (
                    timestamp,
                    time_diff,
                    float(self.ScaledValue_var1.text()),
                    float(self.ScaledValue_var2.text()),
                    float(self.ScaledValue_var3.text()),
                    float(self.ScaledValue_var4.text()),
                    float(self.ScaledValue_var5.text()),
                )
            )
        except Exception as e:
            logging.error(e)

    def update_plot(self, frame):
        """Updates the plot with new data.

        Args:
            frame: The current frame for the FuncAnimation.
        """
        try:
            if not self.plot_data:
                return

            data = np.array(self.plot_data).T
            time_diffs = data[1]
            values = data[2:7]
            self.ax.clear()
            start = time.time()

            for value, combo_box, plot_var in zip(values, self.combo_boxes, self.plot_checkboxes):
                if plot_var.isChecked() and combo_box.currentIndex() != 0:
                    self.ax.plot(np.cumsum(time_diffs), value, label=combo_box.currentText())

            self.ax.set_xlabel("Time (ms)")
            self.ax.set_ylabel("Value")
            self.ax.set_title("Live Plot")
            self.ax.legend(loc="upper right")
            end = time.time()
            logging.debug(end - start)
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception as e:
            logging.error(e)

    def plot_data_plot(self):
        """Initializes and starts data plotting."""
        try:
            if not self.plot_data:
                return

            def initialize_plot():
                self.fig, self.ax = plt.subplots()

                self.ani = FuncAnimation(self.fig, self.update_plot, interval=1, cache_frame_data=False)
                logging.debug(self.ani)
                plt.xticks(rotation=45)
                self.ax.axhline(0, color="black", linewidth=0.5)  # Reference line at y=0
                self.ax.axvline(0, color="black", linewidth=0.5)  # Reference line at x=0
                plt.subplots_adjust(bottom=0.15, left=0.15)  # Adjust plot window position
                plt.show(block=False)  # Use block=False to prevent the GUI from freezing

            if self.plot_window_open:
                if self.fig is not None and plt.fignum_exists(self.fig.number):
                    self.update_plot(0)
                    self.ani.event_source.stop()
                    self.ani.event_source.start(self.timerValue)
                else:
                    initialize_plot()
            else:
                initialize_plot()
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
        if self.combo_box1.currentIndex() == 0:
            self.handle_error("Select Variable")
        else:
            self.Value_var1.setText(str(value))
            self.update_scaled_value(
                self.Scaling_var1,
                self.Value_var1,
                self.ScaledValue_var1,
                self.offset_var1,
            )
            self.handle_variable_putram(self.combo_box1.currentText(), self.Value_var1)

    @pyqtSlot()
    def handle_variable_getram(self, variable, value_var):
        """Handle the retrieval of values from RAM for the specified variable.

        Args:
            variable: The variable to retrieve the value for.
            value_var: The QLineEdit widget to display the retrieved value.
        """
        try:
            current_variable = variable

            for index, combo_box in enumerate(self.combo_boxes):
                if combo_box.currentText() == current_variable:
                    self.selected_var_indices[index] = combo_box.currentIndex()

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

    def refresh_combo_box(self):
        """Refresh the contents of the variable selection combo boxes.

        This method repopulates the combo boxes used for variable selection
        with the updated list of variables.
        """
        if self.VariableList is not None:
            for index, combo_box in enumerate(self.combo_boxes):
                selected_index = self.selected_var_indices[index]
                current_selected_text = combo_box.currentText()

                combo_box.clear()
                combo_box.addItems(self.VariableList)

                if current_selected_text in self.VariableList:
                    combo_box.setCurrentIndex(combo_box.findText(current_selected_text))
                else:
                    combo_box.setCurrentIndex(selected_index)
        else:
            logging.warning("VariableList is None. Unable to refresh combo boxes.")

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
            self.connect_serial()
        else:
            self.disconnect_serial()

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

            for combo_box in self.combo_boxes:
                combo_box.setEnabled(False)

            for live_var in self.live_checkboxes:
                live_var.setEnabled(False)

            self.slider_var1.setEnabled(False)
            for timer in self.timer_list:
                if timer.isActive():
                    timer.stop()

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
            self.refresh_combo_box()
            logging.info("Serial Port Configuration:")
            logging.info(f"Port: {port}")
            logging.info(f"Baud Rate: {baud_rate}")

            self.Connect_button.setText("Disconnect")
            self.Connect_button.setEnabled(True)

            widget_list = [self.port_combo, self.baud_combo, self.select_file_button]

            for widget in widget_list:
                widget.setEnabled(False)

            for combo_box in self.combo_boxes:
                combo_box.setEnabled(True)
            self.slider_var1.setEnabled(True)

            for live_var in self.live_checkboxes:
                live_var.setEnabled(True)

            timer_list = []
            for i in range(len(self.live_checkboxes)):
                timer_list.append((self.live_checkboxes[i], self.timer_list[i]))

            for live_var, timer in timer_list:
                if live_var.isChecked():
                    timer.start(self.timerValue)

        except Exception as e:
            error_message = f"Error while connecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def close_plot_window(self):
        """Close the plot window if it is open.

        This method stops the animation and closes the plot window, if it is open.
        """
        if self.ani is not None:
            self.ani.event_source.stop()
        plt.close(self.fig)
        self.plot_window_open = False

    def close_event(self, event):
        """Handle the event when the main window is closed.

        Args:
            event: The close event.

        This method ensures that all resources are properly released and the
        application is closed cleanly.
        """
        if self.plot_window_open:
            self.close_plot_window()
        if self.ser:
            self.disconnect_serial()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2cscopeGui()
    ex.show()
    sys.exit(app.exec_())
