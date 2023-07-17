import logging
import os
import sys
from datetime import datetime
import serial.tools.list_ports
from PyQt5.QtCore import (QFileInfo, QMutex, QRegExp, QSettings, Qt, QTimer,
                          pyqtSlot)
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QSlider,
                             QWidget)
from mchplnet.interfaces.factory import InterfaceFactory
from mchplnet.interfaces.factory import InterfaceType as IType
from mchplnet.lnet import LNet
from pyx2cscope.gui import img as img_src
from pyx2cscope.variable.variable_factory import VariableFactory

import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.animation import FuncAnimation

logging.basicConfig(level=logging.DEBUG)  # Configure the logging module


class X2Cscope_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.voltage_value = None
        self.current_value = None
        self.port_combo: QComboBox = None
        self.select_file_button: QPushButton = None
        self.layout: QGridLayout = None
        self.combo_box1: QComboBox = None
        self.VariableList = None
        self.combo_box2: QComboBox = None
        self.ser = None  # Hold a reference to the serial port object
        self.variable_factory = None
        self.counter1 = None
        self.counter2 = None
        self.error_shown = False
        self.shown_errors = set()

        self.plot_window_open = False

        self.settings = QSettings("MyCompany", "MyApp")
        self.file_path: str = self.settings.value("file_path", "", type=str)

        decimal_regex = QRegExp("[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

        self.plot_data = deque(maxlen=250)  # Store plot data for Variable 1 and Variable 2
        self.fig, self.ax = None, None
        self.ani = None
        self.init_ui()

    def init_ui(self):
        # Create a central widget and layout
        central_widget = QWidget(self)
        self.layout = QGridLayout(central_widget)

        port_layout = QGridLayout()
        port_label = QLabel("Select Port:")
        self.port_combo = QComboBox()

        # Refresh button initialization
        refresh_button = QPushButton()
        refresh_button.setFixedHeight(10)
        refresh_button.setFixedSize(25, 25)
        refresh_button.clicked.connect(self.refresh_ports)
        refresh_img = os.path.join(os.path.dirname(img_src.__file__), "refresh.png")
        refresh_button.setIcon(QIcon(refresh_img))

        # Elf file loader button
        self.select_file_button = QPushButton("Select elf file")
        self.select_file_button.clicked.connect(self.select_elf_file)

        port_layout.addWidget(port_label, 0, 0)
        port_layout.addWidget(self.port_combo, 0, 1)
        port_layout.addWidget(refresh_button, 0, 2)

        baud_layout = QGridLayout()
        baud_label = QLabel("Select Baud Rate:")
        self.baud_combo = QComboBox()
        baud_layout.addWidget(baud_label, 0, 0)
        baud_layout.addWidget(self.baud_combo, 0, 1)

        # Add common baud rates to the combo box
        self.baud_combo.addItems(["38400", "115200", "230400", "460800", "921600"])
        default_baud_rate = "115200"
        index = self.baud_combo.findText(default_baud_rate, Qt.MatchFixedString)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

        self.Connect_button = QPushButton("Connect")
        self.Connect_button.clicked.connect(self.toggle_connection)
        self.Connect_button.setFixedSize(100, 30)


        self.sampletime = QLineEdit()
        self.sampletime.setText("500")
        self.sampletime.setValidator(self.decimal_validator)
        self.sampletime.editingFinished.connect(self.sampletimeEdit)
        self.sampletime.setFixedSize(30, 20)

        self.timer = QTimer()
        self.timer.timeout.connect(self.var1_update)
        self.timer2 = QTimer()
        self.timer2.timeout.connect(self.var2_update)

        self.timerValue = 500

        self.layout.addLayout(port_layout, 0, 0)
        self.layout.addLayout(baud_layout, 1, 0)

        self.layout.addWidget(self.select_file_button, 3, 0)
        self.grid_layout1 = QHBoxLayout()

        self.grid_layout1.addWidget(QLabel("Sampletime"), alignment=Qt.AlignLeft)
        self.grid_layout1.addWidget(self.sampletime, alignment=Qt.AlignLeft)
        self.grid_layout1.addWidget(QLabel("ms"), alignment=Qt.AlignLeft)

        self.grid_layout1.addStretch(1)
        self.grid_layout1.addWidget(self.Connect_button, alignment=Qt.AlignRight)

        self.layout.addLayout(self.grid_layout1, 4, 0)

        # Create the grid layout for combo boxes and input boxes
        self.grid_layout = QGridLayout()

        # Add labels on top
        labels = ["Live", "Variable", "Value", "Scaling", "Scaled Value", "Unit"]
        for col, label in enumerate(labels):
            self.grid_layout.addWidget(QLabel(label), 0, col)

        self.mutex = QMutex()
        # Live check box
        self.Live_var1 = QCheckBox(self)
        self.Live_var1.setEnabled(False)

        self.grid_layout.addWidget(self.Live_var1, 1, 0)
        self.Live_var1.stateChanged.connect(self.Var1_Live)

        # Create Combo Box 1
        self.combo_box1 = QComboBox()
        self.combo_box1.textActivated.connect(self.Variable1_getram)
        self.combo_box1.addItems(["None"])
        self.combo_box1.setEnabled(False)
        self.grid_layout.addWidget(self.combo_box1, 1, 1)

        # Create input boxes for Combo Box
        self.Value_var1 = QLineEdit(self)
        self.Value_var1.setValidator(self.decimal_validator)
        self.Value_var1.editingFinished.connect(self.Variable1_putram)
        self.Value_var1.textChanged.connect(self.update_scaled_value1)
        self.Scaling_var1 = QLineEdit(self)
        self.Unit_var1 = QComboBox(self)
        self.Unit_var1.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var1 = QLineEdit(self)
        self.ScaledValue_var1.setValidator(self.decimal_validator)
        self.Scaling_var1.setText("1")
        self.Scaling_var1.editingFinished.connect(self.update_scaled_value1)

        self.grid_layout.addWidget(self.Value_var1, 1, 2)
        self.grid_layout.addWidget(self.Scaling_var1, 1, 3)
        self.grid_layout.addWidget(self.ScaledValue_var1, 1, 4)
        self.grid_layout.addWidget(self.Unit_var1, 1, 5)

        self.Live_var2 = QCheckBox(self)
        self.Live_var2.setEnabled(False)
        self.Live_var2.stateChanged.connect(self.Var2_Live)
        self.grid_layout.addWidget(self.Live_var2, 2, 0)
        # Create Combo Box 2
        self.combo_box2 = QComboBox()
        self.combo_box2.addItems(["None"])
        self.combo_box2.setEnabled(False)
        self.combo_box2.setFixedWidth(350)
        self.combo_box2.textActivated.connect(self.Variable2_getram)
        self.grid_layout.addWidget(self.combo_box2, 2, 1)

        self.Value_var2 = QLineEdit(self)
        self.Value_var2.setValidator(self.decimal_validator)
        self.Value_var2.editingFinished.connect(self.Variable2_putram)
        self.Value_var2.textChanged.connect(self.update_scaled_value2)
        self.Scaling_var2 = QLineEdit(self)
        self.Scaling_var2.setText("1")
        self.Scaling_var2.editingFinished.connect(self.update_scaled_value2)
        self.Unit_var2 = QComboBox(self)
        self.Unit_var2.addItems([" ", "V", "RPM", "Watt", "Ampere"])
        self.ScaledValue_var2 = QLineEdit(self)
        self.ScaledValue_var2.setValidator(self.decimal_validator)

        self.grid_layout.addWidget(self.Value_var2, 2, 2)
        self.grid_layout.addWidget(self.Scaling_var2, 2, 3)
        self.grid_layout.addWidget(self.ScaledValue_var2, 2, 4)
        self.grid_layout.addWidget(self.Unit_var2, 2, 5)

        self.layout.addLayout(self.grid_layout, 5, 0)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot_data_plot)
        self.layout.addWidget(self.plot_button, 6, 0)


        # Add slider for Variable 2
        self.slider_var2 = QSlider(Qt.Horizontal)
        self.slider_var2.setMinimum(0)
        self.slider_var2.setMaximum(10000)
        self.slider_var2.setEnabled(False)

        self.slider_var2.valueChanged.connect(self.slider_var2_changed)
        self.grid_layout.addWidget(self.slider_var2, 3, 0, 1, 6)

        self.layout.addLayout(self.grid_layout, 5, 0)

        # Set the central widget and example window properties
        self.setCentralWidget(central_widget)
        self.setWindowTitle("PyX2Cscope")
        mchp_img = os.path.join(os.path.dirname(img_src.__file__), "MCHP.png")
        self.setWindowIcon(QIcon(mchp_img))

        # Populate the available ports combo box
        self.refresh_ports()

    def plot_data_update(self, value1, value2):
        timestamp = datetime.now()
        if len(self.plot_data) > 0:
            last_timestamp = self.plot_data[-1][0]
            time_diff = (timestamp - last_timestamp).total_seconds() * 1000
        else:
            time_diff = 0
        self.plot_data.append((timestamp, time_diff, value1, value2))

    def update_plot(self, frame):
        if not self.plot_data:
            return

        data = np.array(self.plot_data).T
        timestamps = data[0]
        time_diffs = data[1]
        values1 = data[2]
        values2 = data[3]

        self.ax.clear()
        self.ax.plot(np.cumsum(time_diffs), values1, label=self.combo_box1.currentText())
        self.ax.plot(np.cumsum(time_diffs), values2, label=self.combo_box2.currentText())
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("Value")
        self.ax.set_title("Live Plot")
        self.ax.legend()

    def plot_data_plot(self):
        if not self.plot_data:
            return

        if self.plot_window_open:
            if self.fig is not None and plt.fignum_exists(self.fig.number):
                # If the plot window is still open, update the plot and restart the animation with the new interval
                self.update_plot(0)
                self.ani.event_source.stop()
                self.ani.event_source.start(self.timerValue)
            else:
                # The plot window was closed manually, recreate it
                self.fig, self.ax = plt.subplots()
                self.ani = FuncAnimation(self.fig, self.update_plot, interval=self.timerValue)
                plt.xticks(rotation=45)  # Rotate x-axis labels for better visibility
                self.ax.axhline(0, color='black', linewidth=0.5)  # Reference line at y=0
                self.ax.axvline(0, color='black', linewidth=0.5)  # Reference line at x=0
                plt.subplots_adjust(bottom=0.15, left=0.15)  # Adjust plot window position
                plt.show(block=False)  # Use block=False to prevent the GUI from freezing
        else:
            # Create a new plot window
            self.fig, self.ax = plt.subplots()
            self.ani = FuncAnimation(self.fig, self.update_plot, interval=self.timerValue)
            plt.xticks(rotation=45)  # Rotate x-axis labels for better visibility
            self.ax.axhline(0, color='black', linewidth=0.5)  # Reference line at y=0
            self.ax.axvline(0, color='black', linewidth=0.5)  # Reference line at x=0
            plt.subplots_adjust(bottom=0.15, left=0.15)  # Adjust plot window position
            plt.show(block=False)  # Use block=False to prevent the GUI from freezing
            self.plot_window_open = True

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

    def update_scaled_value1(self):
        scaling_text = self.Scaling_var1.text()
        value_text = self.Value_var1.text()

        if scaling_text and value_text:
            try:
                scaling = float(scaling_text)
                value = float(value_text)
                scaled_value = scaling * value
                self.ScaledValue_var1.setText("{:.2f}".format(scaled_value))
            except Exception as e:
                error_message = f"Error: {e}"
                logging.error(error_message)
                self.handle_error(error_message)
        else:
            self.ScaledValue_var1.setText("")

    def update_scaled_value2(self):
        scaling_text = self.Scaling_var2.text()
        value_text = self.Value_var2.text()

        if scaling_text and value_text:
            try:
                scaling = float(scaling_text)
                value = float(value_text)
                scaled_value = scaling * value
                self.ScaledValue_var2.setText("{:.2f}".format(scaled_value))

            except Exception as e:
                print(e)
                error_message = f"Error: {e}"
                logging.error(error_message)
                self.handle_error(error_message)
        else:
            self.ScaledValue_var2.setText("")

    def sampletimeEdit(self):
        try:
            new_sample_time = int(self.sampletime.text())
            if new_sample_time != self.timerValue:
                self.timerValue = new_sample_time
                if self.timer.isActive():
                    self.timer.start(self.timerValue)
                if self.timer2.isActive():
                    self.timer2.start(self.timerValue)
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print(e)

    @pyqtSlot()
    def Variable1_getram(self):
        try:
            self.counter1 = self.var_factory.get_variable_elf(
                self.combo_box1.currentText()
            )
            self.Value_var1.setText(str(self.counter1.get_value()))
        except Exception as e:
            print(e)
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def Variable1_putram(self):
        self.counter1.set_value(float(self.Value_var1.text()))

    @pyqtSlot()
    def Var1_Live(self):
        try:
            if self.Live_var1.isChecked():
                if not self.timer.isActive():
                    self.timer.start(self.timerValue)
            else:
                if self.timer.isActive():
                    self.timer.stop()
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print(e)

    @pyqtSlot()
    def Var2_Live(self):
        try:
            if self.Live_var2.isChecked():
                if not self.timer2.isActive():
                    self.timer2.start(self.timerValue)
            else:
                if self.timer2.isActive():
                    self.timer2.stop()
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print(e)

    @pyqtSlot()
    def var1_update(self):
        try:
            if self.counter1 is not None:
                if self.mutex.tryLock(0):
                    try:
                        value = float(self.counter1.get_value())
                        self.Value_var1.setText(str(value))
                        self.plot_data_update(value, float(self.Value_var2.text()))
                    finally:
                        self.mutex.unlock()
                else:
                    logging.warning("var1_update skipped due to concurrent execution")
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def var2_update(self):
        try:
            if self.counter2 is not None:
                if self.mutex.tryLock(0):
                    try:
                        value = float(self.counter2.get_value())
                        self.Value_var2.setText(str(value))
                        self.plot_data_update(float(self.Value_var1.text()), value)
                    finally:
                        self.mutex.unlock()
                else:
                    logging.warning("var2_update skipped due to concurrent execution")
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    def slider_var2_changed(self, value):
        if self.combo_box2.currentIndex() == 0:
            self.handle_error("Select Variable")
        else:
            self.Value_var2.setText(str(value))
            self.update_scaled_value2()
            self.Variable2_putram()

    @pyqtSlot()
    def Variable2_getram(self):
        try:
            self.counter2 = self.var_factory.get_variable_elf(
                self.combo_box2.currentText()
            )
            self.Value_var2.setText(str(self.counter2.get_value()))
            self.slider_var2.setValue(int(self.counter2.get_value()))
        except Exception as e:
            print(e)
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)

    @pyqtSlot()
    def Variable2_putram(self):
        self.counter2.set_value(int(self.Value_var2.text()))
        value = int(self.Value_var2.text())
        self.Variable2 = value
        self.slider_var2.setValue(value)

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

    def refreshComboBox(self):
        self.combo_box1.clear()
        self.combo_box1.addItems(self.VariableList)
        self.combo_box2.clear()
        self.combo_box2.addItems(self.VariableList)

    def refresh_ports(self):
        # Clear and repopulate the available ports combo box
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(available_ports)

    @pyqtSlot()
    def toggle_connection(self):
        if self.file_path == "":
            QMessageBox.warning(self, "Error", "Please select an ELF file.")
            self.select_elf_file()
            return

        if self.ser is None or not self.ser.is_open:
            if self.timer.isActive():
                self.timer.stop()
            if self.timer2.isActive():
                self.timer2.stop()
            self.plot_data.clear()  # Clear plot data when disconnected
            self.connect_serial()
        else:
            self.disconnect_serial()

    def disconnect_serial(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.stop()
            self.ser = None
            self.Connect_button.setText("Connect")
            self.Connect_button.setEnabled(True)

            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.combo_box2.setEnabled(False)
            self.combo_box1.setEnabled(False)
            self.Live_var1.setEnabled(False)
            self.Live_var2.setEnabled(False)
            self.slider_var2.setEnabled(False)

            if self.timer.isActive():
                self.timer.stop()
            if self.timer2.isActive():
                self.timer2.stop()

            self.combo_box1.clear()
            self.combo_box1.addItems(["None"])
            self.combo_box2.clear()
            self.combo_box2.addItems(["None"])
            self.counter1 = None
            self.counter2 = None

            # Re-populate the combo box with variable list from the previously selected ELF file
            if self.file_path:
                self.refreshComboBox()

    def connect_serial(self):
        port = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())

        try:
            self.ser = InterfaceFactory.get_interface(
                IType.SERIAL, port=port, baudrate=baud_rate
            )
            l_net = LNet(self.ser)
            self.var_factory = VariableFactory(l_net, self.file_path)
            self.VariableList = self.var_factory.get_var_list_elf()

            self.refreshComboBox()
            logging.info("Serial Port Configuration:")
            logging.info(f"Port: {port}")
            logging.info(f"Baud Rate: {baud_rate}")

            self.Connect_button.setText("Disconnect")
            self.Connect_button.setEnabled(True)

            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.combo_box2.setEnabled(True)
            self.combo_box1.setEnabled(True)
            self.Live_var1.setEnabled(True)
            self.Live_var2.setEnabled(True)
            self.slider_var2.setEnabled(True)

            if self.Live_var1.isChecked():
                self.timer.start(self.timerValue)
            if self.Live_var2.isChecked():
                self.timer2.start(self.timerValue)

            # Re-populate the combo box with variable list from the previously selected ELF file
            if self.file_path:
                self.refreshComboBox()

        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ex = X2Cscope_GUI()
    ex.show()
    app.exec_()
