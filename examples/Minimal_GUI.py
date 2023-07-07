import sys
import serial.tools.list_ports
import logging
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QGridLayout,
    QMessageBox,
    QHBoxLayout,
    QFileDialog,
    QPushButton,
    QSlider
)
from PyQt5.QtGui import *
from PyQt5.QtCore import QFileInfo, Qt, QMutex, QTimer, QSettings, QRegExp, pyqtSlot
from pylnet import LNet, VariableFactory
import serial.tools.list_ports

logging.basicConfig(level=logging.DEBUG)  # Configure the logging module


class X2Cscope_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
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

        self.settings = QSettings("MyCompany", "MyApp")
        self.file_path: str = self.settings.value("file_path", "", type=str)

        decimal_regex = QRegExp("[0-9]+(\\.[0-9]+)?")
        self.decimal_validator = QRegExpValidator(decimal_regex)

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
        refresh_button.setIcon(QIcon('../docs/img/refresh.png'))

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

        # Add slider for Variable 2
        self.slider_var2 = QSlider(Qt.Horizontal)
        self.slider_var2.setMinimum(0)
        self.slider_var2.setMaximum(10000)
        self.slider_var2.setEnabled(False)

        # Set the style sheet for the slider
        # self.slider_var2.setStyleSheet(
        #     """
        #     QSlider::groove:horizontal {
        #         height: 10px;
        #         background-color: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 rgba(0, 255, 0, 255), stop:1 rgba(255, 0, 0, 255));
        #     }
        #
        #     QSlider::handle:horizontal {
        #         width: 20px;
        #         background-color: purple;
        #         margin: -5px 0;
        #         border-radius: 10px;
        #     }
        #     """
        # )

        self.slider_var2.valueChanged.connect(self.slider_var2_changed)
        self.grid_layout.addWidget(self.slider_var2, 3, 0, 1, 6)

        self.layout.addLayout(self.grid_layout, 5, 0)

        # Set the central widget and example window properties
        self.setCentralWidget(central_widget)
        self.setWindowTitle("PyX2Cscope")
        self.setWindowIcon(QIcon('../docs/img/MCHP.png'))

        # Populate the available ports combo box
        self.refresh_ports()

    def handle_error(self, error_message: str):
        QMessageBox.critical(self, "Error", error_message)

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
            self.counter1 = self.var_factory.get_variable_elf(self.combo_box1.currentText())
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
                        self.Value_var1.setText(str(self.counter1.get_value()))
                    finally:
                        self.mutex.unlock()
                else:
                    logging.warning("var1_update skipped due to concurrent execution")
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print("var1_update", e)

    @pyqtSlot()
    def var2_update(self):
        try:
            if self.counter2 is not None:
                if self.mutex.tryLock(0):
                    try:
                        self.Value_var2.setText(str(self.counter2.get_value()))
                    finally:
                        self.mutex.unlock()
                else:
                    logging.warning("var2_update skipped due to concurrent execution")
        except Exception as e:
            error_message = f"Error: {e}"
            logging.error(error_message)
            self.handle_error(error_message)
            print("var2_update", e)

    def slider_var2_changed(self, value):
        self.Value_var2.setText(str(value))
        self.update_scaled_value2()
        self.Variable2_putram()
    @pyqtSlot()
    def Variable2_getram(self):
        try:
            self.counter2 = self.var_factory.get_variable_elf(self.combo_box2.currentText())
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



    # ...

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
            self.connect_serial()
        else:
            self.disconnect_serial()

    def disconnect_serial(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
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

            # Re-populate combo box with variable list from the previously selected ELF file
            if self.file_path:
                self.refreshComboBox()

    def connect_serial(self):
        port = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())

        try:
            self.ser = serial.Serial(port, baud_rate)
            lnet = LNet(self.ser)
            self.var_factory = VariableFactory(lnet, self.file_path)
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

            # Re-populate combo box with variable list from the previously selected ELF file
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
