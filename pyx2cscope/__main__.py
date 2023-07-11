import sys

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.minimal_gui import X2Cscope_GUI

app = QApplication(sys.argv)
ex = X2Cscope_GUI()
ex.show()
app.exec_()
