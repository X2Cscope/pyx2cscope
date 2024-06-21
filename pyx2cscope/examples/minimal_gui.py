"""To run the minimal gui (watch-View)."""
import sys

from PyQt5.QtWidgets import QApplication

from pyx2cscope.gui.watchView.minimal_gui import X2cscopeGui

# logging.basicConfig(
#     level=0,
#     filename="minimal_gui.py.log",
# )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = X2cscopeGui()
    ex.show()
    app.exec_()
