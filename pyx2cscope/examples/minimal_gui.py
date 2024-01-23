import sys

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.watchView.minimal_gui import X2Cscope_GUI

# logging.basicConfig(
#     level=0,
#     filename="minimal_gui.py.log",
# )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2Cscope_GUI()
    ex.show()
    app.exec_()
