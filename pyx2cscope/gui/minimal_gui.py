import logging
import os
import sys
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import serial.tools.list_ports
from matplotlib.animation import FuncAnimation
from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from PyQt5.QtCore import (QFileInfo, QMutex, QRegExp, QSettings, Qt, QTimer,
                          pyqtSlot)
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QSlider,
                             QWidget)

from pyx2cscope.gui import img as img_src
from pyx2cscope.variable.variable_factory import VariableFactory

logging.basicConfig(level=logging.DEBUG)  # Configure the logging module


class X2Cscope_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.VariableList = None
        self.var_factory = None
        self.ser = None
        self.timerValue = 500
        self.port_combo = QComboBox()
        self.layout = None
        self.slider_var2 = QSlider(Qt.Horizontal)
        self.Scaling_var5 = QLineEdit(self)
        self.Unit_var5 = QComboBox(self)
        self.Scaling_var4 = QLineEdit(self)
        self.Value_var5 = QLineEdit(self)
        self.ScaledValue_var5 = QLineEdit(self)
        self.combo_box5 = QComboBox()
        self.Live_var5 = QCheckBox(self)
        self.ScaledValue_var4 = QLineEdit(self)
        self.Unit_var4 = QComboBox(self)
        self.Value_var4 = QLineEdit(self)
        self.combo_box4 = QComboBox()
        self.Value_var3 = QLineEdit(self)
        self.Live_var3 = QCheckBox(self)
        self.Live_var4 = QCheckBox(self)
        self.Unit_var3 = QComboBox(self)
        self.ScaledValue_var3 = QLineEdit(self)
        self.Scaling_var3 = QLineEdit(self)
        self.combo_box3 = QComboBox()
        self.plot_button = QPushButton("Plot")
        self.combo_box2 = QComboBox()
        self.ScaledValue_var2 = QLineEdit(self)
        self.Unit_var2 = QComboBox(self)
        self.Scaling_var2 = QLineEdit(self)
        self.Value_var2 = QLineEdit(self)
        self.Live_var2 = QCheckBox(self)
        self.plot_var5_checkbox = QCheckBox()
        self.plot_var2_checkbox = QCheckBox()
        self.plot_var4_checkbox = QCheckBox()
        self.plot_var3_checkbox = QCheckBox()
        self.plot_var1_checkbox = QCheckBox()
        self.ScaledValue_var1 = QLineEdit(self)
        self.Scaling_var1 = QLineEdit(self)
        self.Unit_var1 = QComboBox(self)
        self.Value_var1 = QLineEdit(self)
        self.combo_box1 = QComboBox()
        self.Live_var1 = QCheckBox(self)
        self.mutex = QMutex()
        self.grid_layout = QGridLayout()
        self.grid_layout1 = QHBoxLayout()
        self.timer5 = QTimer()
        self.timer4 = QTimer()
        self.timer3 = QTimer()
        self.timer2 = QTimer()
        self.timer1 = QTimer()
        self.sampletime = QLineEdit()
        self.Connect_button = QPushButton("Connect")
        self.baud_combo = QComboBox()
        self.select_file_button = QPushButton("Select elf file")
        self.error_shown = False
        self.shown_errors = set()
        self.plot_window_open = False
        self.settings = QSettings("MyCompany", "MyApp")
        self.file_path: str = self.settings.value("file_path", "", type=str)

        decimal_regex = QRegExp("[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

        self.plot_data = deque(
            maxlen=250
        )  # Store plot data for Variable 1 and Variable 2
        self.fig, self.ax = None, None
        self.ani = None
        self.init_ui()

    # noinspection PyUnresolvedReferences
    def init_ui(self):
        # Create a central widget and layout
        central_widget = QWidget(self)
        self.layout = QGridLayout(central_widget)

        port_layout = QGridLayout()
        port_label = QLabel("Select Port:")

        # Refresh button initialization
        refresh_button = QPushButton()
        refresh_button.setFixedHeight(10)
        refresh_button.setFixedSize(25, 25)
        refresh_button.clicked.connect(self.refresh_ports)
        refresh_img = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        refresh_button.setIcon(QIcon(refresh_img))

        # Elf file loader button
        self.select_file_button.clicked.connect(self.select_elf_file)

        port_layout.addWidget(port_label, 0, 0)
        port_layout.addWidget(self.port_combo, 0, 1)
        port_layout.addWidget(refresh_button, 0, 2)

        baud_layout = QGridLayout()
        baud_label = QLabel("Select Baud Rate:")
        baud_layout.addWidget(baud_label, 0, 0)
        baud_layout.addWidget(self.baud_combo, 0, 1)

        # Add common baud rates to the combo box
        self.baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        default_baud_rate = "115200"
        index = self.baud_combo.findText(default_baud_rate, Qt.MatchFixedString)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

        self.Connect_button.clicked.connect(self.toggle_connection)
        self.Connect_button.setFixedSize(100, 30)

        self.sampletime.setText("500")
        self.sampletime.setValidator(self.decimal_validator)
        self.sampletime.editingFinished.connect(self.sampletime_edit)
        self.sampletime.setFixedSize(30, 20)

        self.layout.addLayout(port_layout, 0, 0)
        self.layout.addLayout(baud_layout, 1, 0)

        self.layout.addWidget(self.select_file_button, 3, 0)

        self.grid_layout1.addWidget(QLabel("Sampletime"), alignment=Qt.AlignLeft)
        self.grid_layout1.addWidget(self.sampletime, alignment=Qt.AlignLeft)
        self.grid_layout1.addWidget(QLabel("ms"), alignment=Qt.AlignLeft)

        self.grid_layout1.addStretch(1)
        self.grid_layout1.addWidget(self.Connect_button, alignment=Qt.AlignRight)

        self.layout.addLayout(self.grid_layout1, 4, 0)

        # Create the grid layout for combo boxes and input boxes

        # Add labels on top
        labels = ["Live", "Variable", "Value", "Scaling", "Scaled Value", "Unit", "Plot"]
        for col, label in enumerate(labels):
            self.grid_layout.addWidget(QLabel(label), 0, col)

        # Live check box
        self.Live_var1.setEnabled(False)

        self.grid_layout.addWidget(self.Live_var1, 1, 0)
        # Create Combo Box 1
        self.combo_box1.addItems(["None"])
        self.combo_box1.setEnabled(False)
        self.grid_layout.addWidget(self.combo_box1, 1, 1)

        # Create input boxes for Combo Box
        self.Value_var1.setText("0")
        self.Value_var1.setValidator(self.decimal_validator)
        self.Unit_var1.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var1.setText("0")
        self.ScaledValue_var1.setValidator(self.decimal_validator)
        self.Scaling_var1.setText("1")

        self.grid_layout.addWidget(self.Value_var1, 1, 2)
        self.grid_layout.addWidget(self.Scaling_var1, 1, 3)
        self.grid_layout.addWidget(self.ScaledValue_var1, 1, 4)
        self.grid_layout.addWidget(self.Unit_var1, 1, 5)

        self.grid_layout.addWidget(self.plot_var1_checkbox, 1, 6)
        self.grid_layout.addWidget(self.plot_var2_checkbox, 2, 6)
        self.grid_layout.addWidget(self.plot_var3_checkbox, 3, 6)
        self.grid_layout.addWidget(self.plot_var4_checkbox, 4, 6)
        self.grid_layout.addWidget(self.plot_var5_checkbox, 5, 6)

        self.Live_var2.setEnabled(False)
        self.grid_layout.addWidget(self.Live_var2, 2, 0)
        # Create Combo Box 2
        self.combo_box2.addItems(["None"])
        self.combo_box2.setEnabled(False)
        self.combo_box2.setFixedWidth(350)
        self.grid_layout.addWidget(self.combo_box2, 2, 1)

        self.Value_var2.setText("0")
        self.Value_var2.setValidator(self.decimal_validator)

        self.Scaling_var2.setText("1")
        self.Unit_var2.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var2.setText("0")
        self.ScaledValue_var2.setValidator(self.decimal_validator)

        self.grid_layout.addWidget(self.Value_var2, 2, 2)
        self.grid_layout.addWidget(self.Scaling_var2, 2, 3)
        self.grid_layout.addWidget(self.ScaledValue_var2, 2, 4)
        self.grid_layout.addWidget(self.Unit_var2, 2, 5)

        self.layout.addLayout(self.grid_layout, 5, 0)

        self.plot_button.clicked.connect(self.plot_data_plot)
        self.layout.addWidget(self.plot_button, 6, 0)
        self.layout.addLayout(self.grid_layout, 5, 0)

        # Set the central widget and example window properties
        self.setCentralWidget(central_widget)
        self.setWindowTitle("PyX2Cscope")
        mchp_img = os.path.join(os.path.dirname(img_src.__file__), "MCHP.png")
        self.setWindowIcon(QIcon(mchp_img))

        # Populate the available ports combo box
        self.refresh_ports()

        self.Live_var3.setEnabled(False)
        self.grid_layout.addWidget(self.Live_var3, 3, 0)
        # Create Combo Box 3
        self.combo_box3.addItems(["None"])
        self.combo_box3.setEnabled(False)
        self.combo_box3.setFixedWidth(350)
        self.grid_layout.addWidget(self.combo_box3, 3, 1)

        self.Value_var3.setText("0")
        self.Value_var3.setValidator(self.decimal_validator)

        self.Scaling_var3.setText("1")
        self.Unit_var3.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var3.setText("0")
        self.ScaledValue_var3.setValidator(self.decimal_validator)

        self.grid_layout.addWidget(self.Value_var3, 3, 2)
        self.grid_layout.addWidget(self.Scaling_var3, 3, 3)
        self.grid_layout.addWidget(self.ScaledValue_var3, 3, 4)
        self.grid_layout.addWidget(self.Unit_var3, 3, 5)

        self.Live_var4.setEnabled(False)
        self.grid_layout.addWidget(self.Live_var4, 4, 0)
        # Create Combo Box 4
        self.combo_box4.addItems(["None"])
        self.combo_box4.setEnabled(False)
        self.combo_box4.setFixedWidth(350)
        self.grid_layout.addWidget(self.combo_box4, 4, 1)

        self.Value_var4.setText("0")
        self.Value_var4.setValidator(self.decimal_validator)

        self.Scaling_var4.setText("1")
        self.Unit_var4.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var4.setText("0")
        self.ScaledValue_var4.setValidator(self.decimal_validator)

        self.grid_layout.addWidget(self.Value_var4, 4, 2)
        self.grid_layout.addWidget(self.Scaling_var4, 4, 3)
        self.grid_layout.addWidget(self.ScaledValue_var4, 4, 4)
        self.grid_layout.addWidget(self.Unit_var4, 4, 5)

        self.Live_var5.setEnabled(False)
        self.grid_layout.addWidget(self.Live_var5, 5, 0)
        # Create Combo Box 5
        self.combo_box5.addItems(["None"])
        self.combo_box5.setEnabled(False)
        self.combo_box5.setFixedWidth(350)
        self.grid_layout.addWidget(self.combo_box5, 5, 1)

        self.Value_var5.setText("0")
        self.Value_var5.setValidator(self.decimal_validator)

        self.Scaling_var5.setText("1")

        self.Unit_var5.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var5.setText("0")
        self.ScaledValue_var5.setValidator(self.decimal_validator)

        self.grid_layout.addWidget(self.Value_var5, 5, 2)
        self.grid_layout.addWidget(self.Scaling_var5, 5, 3)
        self.grid_layout.addWidget(self.ScaledValue_var5, 5, 4)
        self.grid_layout.addWidget(self.ScaledValue_var5, 5, 4)
        self.grid_layout.addWidget(self.Unit_var5, 5, 5)

        self.layout.addLayout(self.grid_layout, 6, 0)

        self.timer1.timeout.connect(lambda: self.handle_var_update(self.combo_box1.currentText(), self.Value_var1))

        self.timer2.timeout.connect(lambda: self.handle_var_update(self.combo_box2.currentText(), self.Value_var2))

        self.timer3.timeout.connect(lambda: self.handle_var_update(self.combo_box3.currentText(), self.Value_var3))

        self.timer4.timeout.connect(lambda: self.handle_var_update(self.combo_box4.currentText(), self.Value_var4))

        self.timer5.timeout.connect(lambda: self.handle_var_update(self.combo_box5.currentText(), self.Value_var5))

        self.combo_box1.currentIndexChanged.connect(lambda: self.handle_variable_getram(
                self.combo_box1.currentText(), self.Value_var1))
        self.combo_box2.currentIndexChanged.connect(lambda: self.handle_variable_getram(
                self.combo_box2.currentText(), self.Value_var2))
        self.combo_box3.currentIndexChanged.connect(lambda: self.handle_variable_getram(
                self.combo_box3.currentText(), self.Value_var3))
        self.combo_box4.currentIndexChanged.connect(lambda: self.handle_variable_getram(
                self.combo_box4.currentText(), self.Value_var4))
        self.combo_box5.currentIndexChanged.connect(lambda: self.handle_variable_getram(
                self.combo_box5.currentText(), self.Value_var5))
        self.Value_var1.editingFinished.connect(lambda: self.handle_variable_putram(
                self.combo_box1.currentText(), self.Value_var1))
        self.Value_var2.editingFinished.connect(lambda: self.handle_variable_putram(
                self.combo_box2.currentText(), self.Value_var2))
        self.Value_var3.editingFinished.connect(lambda: self.handle_variable_putram(
                self.combo_box3.currentText(), self.Value_var3))
        self.Value_var4.editingFinished.connect(lambda: self.handle_variable_putram(
                self.combo_box4.currentText(), self.Value_var4))
        self.Value_var5.editingFinished.connect(lambda: self.handle_variable_putram(
                self.combo_box5.currentText(), self.Value_var5))

        self.Value_var1.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var1, self.Value_var1, self.ScaledValue_var1))
        self.Scaling_var1.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var1, self.Value_var1, self.ScaledValue_var1))

        self.Value_var2.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var2, self.Value_var2, self.ScaledValue_var2))
        self.Scaling_var2.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var2, self.Value_var2, self.ScaledValue_var2))

        self.Value_var3.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var3, self.Value_var3, self.ScaledValue_var3))
        self.Scaling_var3.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var3, self.Value_var3, self.ScaledValue_var3))

        self.Value_var4.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var4, self.Value_var4, self.ScaledValue_var4))
        self.Scaling_var4.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var4, self.Value_var4, self.ScaledValue_var4))

        self.Value_var5.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var5, self.Value_var5, self.ScaledValue_var5))
        self.Scaling_var5.textChanged.connect(lambda: self.update_scaled_value(
                self.Scaling_var5, self.Value_var5, self.ScaledValue_var5))

        self.Live_var1.stateChanged.connect(lambda: self.var_live(self.Live_var1, self.timer1))
        self.Live_var2.stateChanged.connect(lambda: self.var_live(self.Live_var2, self.timer2))
        self.Live_var3.stateChanged.connect(lambda: self.var_live(self.Live_var3, self.timer3))
        self.Live_var4.stateChanged.connect(lambda: self.var_live(self.Live_var4, self.timer4))
        self.Live_var5.stateChanged.connect(lambda: self.var_live(self.Live_var5, self.timer5))

        # Add slider for Variable 2
        self.slider_var2.setMinimum(0)
        self.slider_var2.setMaximum(10000)
        self.slider_var2.setEnabled(False)

        self.slider_var2.valueChanged.connect(self.slider_var2_changed)
        self.grid_layout.addWidget(self.slider_var2, 8, 0, 1, 6)

        self.layout.addLayout(self.grid_layout, 6, 0)

        # Set the central widget and example window properties
        self.setCentralWidget(central_widget)
        self.setWindowTitle("PyX2Cscope")
        mchp_img = os.path.join(os.path.dirname(img_src.__file__), "MCHP.png")
        self.setWindowIcon(QIcon(mchp_img))

        # Populate the available ports combo box
        self.refresh_ports()

    @pyqtSlot()
    def var_live(self, live_var, timer):
        try:
            if live_var.isChecked():
                if not timer.isActive():
                    timer.start(self.timerValue)
            else:
                if timer.isActive():
                    timer.stop()
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def update_scaled_value(self, scaling_var, value_var, scaled_value_var):
        scaling_text = scaling_var.text()
        value_text = value_var.text()

        if scaling_text and value_text:
            try:
                scaling = float(scaling_text)
                value = float(value_text)
                scaled_value = scaling * value
                scaled_value_var.setText("{:.2f}".format(scaled_value))
            except Exception as e:
                error_message = f"Error: {e}"
                logging.error(error_message)
                self.handle_error(error_message)
        else:
            scaled_value_var.setText("")

    def plot_data_update(self):
        try:
            timestamp = datetime.now()
            if len(self.plot_data) > 0:
                last_timestamp = self.plot_data[-1][0]
                time_diff = (
                                    timestamp - last_timestamp
                            ).total_seconds() * 1000  # to convert time in ms.
            else:
                time_diff = 0
            self.plot_data.append(
                (
                    timestamp,
                    time_diff,
                    float(self.Value_var1.text()),
                    float(self.Value_var2.text()),
                    float(self.Value_var3.text()),
                    float(self.Value_var4.text()),
                    float(self.Value_var5.text()),
                )
            )
        except Exception as e:
            print(e)

    def update_plot(self, frame):
        try:
            if not self.plot_data:
                return

            data = np.array(self.plot_data).T
            time_diffs = data[1]
            values = data[2:7]
            combo_boxes = [self.combo_box1, self.combo_box2, self.combo_box3,
                           self.combo_box4, self.combo_box5]
            plot_vars = [self.plot_var1_checkbox, self.plot_var2_checkbox,
                         self.plot_var3_checkbox, self.plot_var4_checkbox,
                         self.plot_var5_checkbox]

            self.ax.clear()
            start = time.time()

            for value, combo_box, plot_var in zip(values, combo_boxes, plot_vars):
                if plot_var.isChecked() and combo_box.currentIndex() != 0:
                    self.ax.plot(np.cumsum(time_diffs), value,
                                 label=combo_box.currentText())

            self.ax.set_xlabel("Time (ms)")
            self.ax.set_ylabel("Value")
            self.ax.set_title("Live Plot")
            self.ax.legend(loc="upper right")
            end = time.time()
            print(end - start)
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception as e:
            print(e)

    def plot_data_plot(self):
        try:
            if not self.plot_data:
                return

            def initialize_plot():
                self.fig, self.ax = plt.subplots()
                self.ani = FuncAnimation(self.fig, self.update_plot, interval=1)
                plt.xticks(rotation=45)  # Rotate x-axis labels for better visibility
                self.ax.axhline(0, color="black", linewidth=0.5)  # Reference line at y=0
                self.ax.axvline(0, color="black", linewidth=0.5)  # Reference line at x=0
                plt.subplots_adjust(bottom=0.15, left=0.15)  # Adjust plot window position
                plt.show(block=False)  # Use block=False to prevent the GUI from freezing

            if self.plot_window_open:
                if self.fig is not None and plt.fignum_exists(self.fig.number):
                    # If the plot window is still open, update the plot and restart the animation with the new interval
                    self.update_plot(0)
                    self.ani.event_source.stop()
                    self.ani.event_source.start(self.timerValue)
                else:
                    # The plot window was closed manually, recreate it
                    initialize_plot()
            else:
                # Create a new plot window
                initialize_plot()
                self.plot_window_open = True
        except Exception as e:
            print(e)

    # noinspection PyUnresolvedReferences
    def handle_error(self, error_message: str):
        if error_message not in self.shown_errors:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(error_message)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.buttonClicked.connect(self.error_box_closed)
            msg_box.exec_()
            self.shown_errors.add(error_message)

    def error_box_closed(self):
        # Handle closing of the error pop-up box if needed
        pass

    def sampletime_edit(self):
        try:
            new_sample_time = int(self.sampletime.text())
            if new_sample_time != self.timerValue:
                self.timerValue = new_sample_time
                timer_list = [self.timer1, self.timer2, self.timer3,
                              self.timer4, self.timer5]
                for timer in timer_list:
                    if timer.isActive():
                        timer.start(self.timerValue)
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print(e)

    @pyqtSlot()
    def handle_var_update(self, counter, value_var):
        try:
            if counter is not None:
                counter = self.var_factory.get_variable_elf(counter)
                value = float(counter.get_value())
                value_var.setText(str(value))
                if value_var == self.Value_var2:  # Check if it's Variable 2 being updated
                    self.slider_var2.setValue(int(value))  # Set slider to the updated value
                self.plot_data_update()
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def slider_var2_changed(self, value):
        if self.combo_box2.currentIndex() == 0:
            self.handle_error("Select Variable")
        else:
            self.Value_var2.setText(str(value))
            self.update_scaled_value(
                self.Scaling_var2, self.Value_var2, self.ScaledValue_var2
            )
            self.handle_variable_putram(self.combo_box2.currentText(), self.Value_var2)

    @pyqtSlot()
    def handle_variable_getram(self, variable, Value_var):
        try:
            current_variable = variable

            if current_variable and current_variable != "None":
                counter = self.var_factory.get_variable_elf(current_variable)
                value = str(counter.get_value())
                Value_var.setText(value)
                if Value_var == self.Value_var2:  # Check if it's Variable 2 being updated
                    self.slider_var2.setValue(int(value))  # Set slider to the updated value
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def handle_variable_putram(self, variable, Value_var):
        try:
            current_variable = variable
            value = int(Value_var.text())

            if current_variable and current_variable != "None":
                counter = self.var_factory.get_variable_elf(current_variable)
                counter.set_value(value)
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def select_elf_file(self):
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

    def refresh_combo_box(self):
        combo_boxes = [self.combo_box1, self.combo_box2, self.combo_box3,
                       self.combo_box4, self.combo_box5]
        for combo_box in combo_boxes:
            combo_box.addItems(self.VariableList)

    def refresh_ports(self):
        # Clear and repopulate the available ports combo box
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.addItems(available_ports)

    @pyqtSlot()
    def toggle_connection(self):
        if self.file_path == "":
            QMessageBox.warning(self, "Error", "Please select an ELF file.")
            self.select_elf_file()
            return

        timer_list = [self.timer1, self.timer2, self.timer3, self.timer4, self.timer5]

        if self.ser is None or not self.ser.is_open:
            for timer in timer_list:
                if timer.isActive():
                    timer.stop()
            self.plot_data.clear()  # Clear plot data when disconnected
            self.connect_serial()
        else:
            self.disconnect_serial()

    def disconnect_serial(self):
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.stop()
                self.ser = None  # Reset the serial connection object

            # Reset UI elements and timers
            self.Connect_button.setText("Connect")
            self.Connect_button.setEnabled(True)
            widget_list = [self.port_combo, self.baud_combo]
            combo_boxes = [self.combo_box1, self.combo_box2, self.combo_box3,
                           self.combo_box4, self.combo_box5]
            live_vars = [self.Live_var1, self.Live_var2, self.Live_var3,
                         self.Live_var4, self.Live_var5]

            for widget in widget_list:
                widget.setEnabled(True)

            for combo_box in combo_boxes:
                combo_box.setEnabled(False)

            for live_var in live_vars:
                live_var.setEnabled(False)

            self.slider_var2.setEnabled(False)

            timer_list = [self.timer1, self.timer2, self.timer3,
                          self.timer4, self.timer5]

            for timer in timer_list:
                if timer.isActive():
                    timer.stop()

            if self.file_path:
                self.refresh_combo_box()

        except Exception as e:
            error_message = f"Error while disconnecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def connect_serial(self):
        try:
            # Disconnect first if already connected
            if self.ser is not None and self.ser.is_open:
                self.disconnect_serial()

            port = self.port_combo.currentText()
            baud_rate = int(self.baud_combo.currentText())

            self.ser = InterfaceFactory.get_interface(IType.SERIAL, port=port, baudrate=baud_rate)
            l_net = LNet(self.ser)
            self.var_factory = VariableFactory(l_net, self.file_path)
            self.VariableList = self.var_factory.get_var_list_elf()

            self.refresh_combo_box()
            logging.info("Serial Port Configuration:")
            logging.info(f"Port: {port}")
            logging.info(f"Baud Rate: {baud_rate}")

            self.Connect_button.setText("Disconnect")
            self.Connect_button.setEnabled(True)

            widget_list = [self.port_combo, self.baud_combo]
            combo_boxes = [self.combo_box1, self.combo_box2, self.combo_box3,
                           self.combo_box4, self.combo_box5]
            live_vars = [self.Live_var1, self.Live_var2, self.Live_var3,
                         self.Live_var4, self.Live_var5]

            for widget in widget_list:
                widget.setEnabled(False)

            for combo_box in combo_boxes:
                combo_box.setEnabled(True)

            for live_var in live_vars:
                live_var.setEnabled(True)

            self.slider_var2.setEnabled(True)

            timer_list = [(self.Live_var1, self.timer1), (self.Live_var2, self.timer2),
                          (self.Live_var3, self.timer3), (self.Live_var4, self.timer4),
                          (self.Live_var5, self.timer5)]

            for live_var, timer in timer_list:
                if live_var.isChecked():
                    timer.start(self.timerValue)

            if self.file_path:
                self.refresh_combo_box()

        except Exception as e:
            error_message = f"Error while connecting: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

        # ... (existing code)

    def closeEvent(self, event):
        # Close the serial connection and clean up when the application is closed
        self.disconnect_serial()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2Cscope_GUI()
    ex.show()
    sys.exit(app.exec_())
