"""This module is for all the different GUI."""


def execute_qt(*args, **kwargs):
    """Execute the default Qt GUI interface.

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
    """Start the web server.

    Args:
        *args: non-keyed arguments
        **kwargs: keyed arguments related to the web server. See parse_arguments function documentations.
    """
    from pyx2cscope.gui.web import app

    app.main(*args, **kwargs)
