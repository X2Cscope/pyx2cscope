"""pyX2Cscope Qt GUI - A PyQt5-based GUI for motor control and debugging.

This package provides a modular GUI with the following components:

Tabs:
    - SetupTab: Connection setup and device information
    - ScopeViewTab: Oscilloscope-style capture and trigger configuration
    - WatchViewTab: Dynamic watch variable management

Controllers:
    - ConnectionManager: Serial/TCP/CAN connection management
    - ConfigManager: Configuration save/load

Workers:
    - DataPoller: Background thread for polling watch and scope data

Models:
    - AppState: Centralized application state management
"""

from pyx2cscope.gui.qt.controllers.config_manager import ConfigManager
from pyx2cscope.gui.qt.controllers.connection_manager import ConnectionManager
from pyx2cscope.gui.qt.dialogs.variable_selection import VariableSelectionDialog
from pyx2cscope.gui.qt.main_window import MainWindow, execute_qt
from pyx2cscope.gui.qt.models.app_state import (
    AppState,
    ScopeChannel,
    TriggerSettings,
    WatchVariable,
)
from pyx2cscope.gui.qt.tabs.base_tab import BaseTab
from pyx2cscope.gui.qt.tabs.scope_view_tab import ScopeViewTab
from pyx2cscope.gui.qt.tabs.setup_tab import SetupTab
from pyx2cscope.gui.qt.tabs.watch_view_tab import WatchViewTab
from pyx2cscope.gui.qt.workers.data_poller import DataPoller

__all__ = [
    # Main
    "MainWindow",
    "execute_qt",
    # Models
    "AppState",
    "WatchVariable",
    "ScopeChannel",
    "TriggerSettings",
    # Controllers
    "ConnectionManager",
    "ConfigManager",
    # Workers
    "DataPoller",
    # Tabs
    "BaseTab",
    "SetupTab",
    "ScopeViewTab",
    "WatchViewTab",
    # Dialogs
    "VariableSelectionDialog",
]
