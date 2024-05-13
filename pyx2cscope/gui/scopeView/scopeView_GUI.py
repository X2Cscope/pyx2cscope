import logging
import sys

import serial
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget


class MotorControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Motor Control Oscilloscope")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        layout = QVBoxLayout()

        # Plot widget
        self.plotWidget = PlotWidget()
        layout.addWidget(self.plotWidget)

        # ComboBox for variable selection
        self.variableComboBox = QComboBox()
        self.variableComboBox.addItems(["motor.idq.q", "motor.vabc.a", "other variables..."])  # Add all your variables
        layout.addWidget(self.variableComboBox)

        # Button for starting/stopping the plot
        self.plotButton = QPushButton("Start Plotting")
        self.plotButton.clicked.connect(self.togglePlotting)
        layout.addWidget(self.plotButton)

        # Central widget
        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        # Timer setup for updating the plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.updatePlot)
        self.isPlotting = False

    def togglePlotting(self):
        if self.isPlotting:
            self.timer.stop()
            self.plotButton.setText("Start Plotting")
        else:
            self.timer.start(100)  # Update interval in ms
            self.plotButton.setText("Stop Plotting")
        self.isPlotting = not self.isPlotting

    def updatePlot(self):
        # This function should handle the data acquisition and update the plot
        # For now, it's a placeholder that does nothing
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = MotorControlGUI()
    ex.show()
    sys.exit(app.exec_())
