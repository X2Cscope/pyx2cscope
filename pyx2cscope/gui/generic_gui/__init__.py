"""pyX2Cscope Generic GUI - A PyQt5-based GUI for motor control and debugging.

This package provides a modular GUI with the following components:

Tabs:
    - WatchPlotTab: Watch variables with real-time plotting
    - ScopeViewTab: Oscilloscope-style capture and trigger configuration
    - WatchViewTab: Dynamic watch variable management

Controllers:
    - ConnectionManager: Serial connection management
    - ConfigManager: Configuration save/load

Workers:
    - DataPoller: Background thread for polling watch and scope data

Models:
    - AppState: Centralized application state management
"""

from pyx2cscope.gui.generic_gui.main_window import MainWindow, execute_qt
from pyx2cscope.gui.generic_gui.models.app_state import (
    AppState,
    ScopeChannel,
    TriggerSettings,
    WatchVariable,
)
from pyx2cscope.gui.generic_gui.controllers.connection_manager import ConnectionManager
from pyx2cscope.gui.generic_gui.controllers.config_manager import ConfigManager
from pyx2cscope.gui.generic_gui.workers.data_poller import DataPoller
from pyx2cscope.gui.generic_gui.tabs.base_tab import BaseTab
from pyx2cscope.gui.generic_gui.tabs.watch_plot_tab import WatchPlotTab
from pyx2cscope.gui.generic_gui.tabs.scope_view_tab import ScopeViewTab
from pyx2cscope.gui.generic_gui.tabs.watch_view_tab import WatchViewTab
from pyx2cscope.gui.generic_gui.dialogs.variable_selection import VariableSelectionDialog

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
    "WatchPlotTab",
    "ScopeViewTab",
    "WatchViewTab",
    # Dialogs
    "VariableSelectionDialog",
]
