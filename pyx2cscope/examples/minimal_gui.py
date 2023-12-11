import sys

# logging.basicConfig(
#     level=0,
#     filename="minimal_gui.py.log",
# )

from PyQt5.QtWidgets import QApplication

from gui.watchView.minimal_gui import X2Cscope_GUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2Cscope_GUI()
    ex.show()
    app.exec_()
