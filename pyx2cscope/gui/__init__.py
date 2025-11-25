"""This module serves as the entry point for launching the various graphical user interfaces (GUIs).

It provides functions to start either the Qt-based desktop GUI or the web-based GUI server.

Functions
---------
- execute_qt(*args, **kwargs): Launches the default Qt GUI interface for X2Cscope.
- execute_web(*args, **kwargs): Starts the web server for the web-based GUI.

Typical usage example:

    from pyx2cscope.gui import execute_qt, execute_web

    # To launch the Qt GUI:
    execute_qt()

    # To launch the web GUI:
    execute_web()

"""


def execute_qt(*args, **kwargs):
    """Executes the default Qt GUI interface.

    Args:
        args: non-keyed arguments for Qt App.
        kwargs: keyed arguments for Qt App.

    :return:
    """
    import sys

    from PyQt5.QtWidgets import QApplication

    from pyx2cscope.gui.generic_gui.generic_gui import X2cscopeGui

    # QApplication expects the first argument to be the program name.
    qt_args = sys.argv[:1] + args[0]
    # Initialize a PyQt5 application
    app = QApplication(qt_args)
    # Create an instance of the X2Cscope_GUI
    ex = X2cscopeGui(*args, **kwargs)
    # Display the GUI
    ex.show()
    # Start the PyQt5 application event loop
    app.exec_()


def execute_web(*args, **kwargs):
    """Starts the web server.

    Args:
        *args: non-keyed arguments
        **kwargs: keyed arguments related to the web server. See parse_arguments function documentations.
    """
    from pyx2cscope.gui.web import app

    app.main(*args, **kwargs)
