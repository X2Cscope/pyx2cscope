"""Background worker thread for data polling.

This module consolidates all timer-based polling into a single QThread,
replacing the 7 separate QTimer instances from the original implementation.
"""

import logging
import time
from typing import List

from PyQt5.QtCore import QMutex, QThread, pyqtSignal


class DataPoller(QThread):
    """Background thread for polling watch variables and scope data.

    Consolidates polling for:
    - Tab1: Watch variables (previously timer1-5)
    - Tab1: Plot data updates (previously plot_update_timer)
    - Tab2: Scope data sampling (previously scope_timer)
    - Tab3: Live variable updates (previously live_update_timer)

    Signals:
        watch_var_updated: Emitted when a watch variable value is read.
            Args: (index: int, name: str, value: float)
        scope_data_ready: Emitted when scope data is available.
            Args: (data: dict)
        live_var_updated: Emitted when a Tab3 live variable is read.
            Args: (index: int, name: str, value: float)
        error_occurred: Emitted when an error occurs during polling.
            Args: (message: str)
    """

    # Signals for thread-safe UI updates
    watch_var_updated = pyqtSignal(int, str, float)  # index, name, value
    scope_data_ready = pyqtSignal(dict)  # channel_data
    live_var_updated = pyqtSignal(int, str, float)  # index, name, value
    error_occurred = pyqtSignal(str)  # error message
    plot_data_ready = pyqtSignal()  # signal to update plot

    def __init__(self, app_state, parent=None):
        """Initialize the data poller.

        Args:
            app_state: The centralized AppState instance.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._mutex = QMutex()
        self._running = False

        # Polling intervals (ms)
        self._watch_interval_ms = 500
        self._scope_interval_ms = 250
        self._live_interval_ms = 500

        # Enable flags for different polling tasks
        self._watch_polling_enabled = False
        self._scope_polling_enabled = False
        self._live_polling_enabled = False
        self._scope_single_shot = False

        # Track which watch variables are active (Tab1)
        self._active_watch_indices: List[int] = []

        # Track which live variables are active (Tab3)
        self._active_live_indices: List[int] = []

    def run(self):
        """Main thread loop - polls data at configured intervals."""
        self._running = True
        logging.debug("DataPoller thread started")

        # Track last poll times
        last_watch_poll = 0.0
        last_scope_poll = 0.0
        last_live_poll = 0.0

        while self._running:
            current_time = time.time() * 1000  # Convert to ms

            try:
                # Poll watch variables (Tab1)
                if self._watch_polling_enabled:
                    if current_time - last_watch_poll >= self._watch_interval_ms:
                        self._poll_watch_variables()
                        last_watch_poll = current_time

                # Poll scope data (Tab2)
                if self._scope_polling_enabled:
                    if current_time - last_scope_poll >= self._scope_interval_ms:
                        self._poll_scope_data()
                        last_scope_poll = current_time

                # Poll live variables (Tab3)
                if self._live_polling_enabled:
                    if current_time - last_live_poll >= self._live_interval_ms:
                        self._poll_live_variables()
                        last_live_poll = current_time

            except Exception as e:
                logging.error(f"DataPoller error: {e}")
                self.error_occurred.emit(str(e))

            # Sleep to prevent busy-waiting (10ms granularity)
            self.msleep(10)

    def stop(self):
        """Stop the polling thread."""
        self._running = False
        self.wait()

    # ============= Watch Variables (Tab1) =============

    def set_watch_polling_enabled(self, enabled: bool):
        """Enable or disable watch variable polling."""
        self._mutex.lock()
        self._watch_polling_enabled = enabled
        self._mutex.unlock()

    def set_active_watch_indices(self, indices: List[int]):
        """Set which watch variable indices should be polled."""
        self._mutex.lock()
        self._active_watch_indices = indices.copy()
        self._mutex.unlock()

    def add_active_watch_index(self, index: int):
        """Add a watch variable index to active polling."""
        logging.debug(f"add_active_watch_index: adding index {index}")
        self._mutex.lock()
        if index not in self._active_watch_indices:
            self._active_watch_indices.append(index)
        self._watch_polling_enabled = len(self._active_watch_indices) > 0
        logging.debug(f"add_active_watch_index: enabled={self._watch_polling_enabled}, indices={self._active_watch_indices}")
        self._mutex.unlock()

    def remove_active_watch_index(self, index: int):
        """Remove a watch variable index from active polling."""
        self._mutex.lock()
        if index in self._active_watch_indices:
            self._active_watch_indices.remove(index)
        self._watch_polling_enabled = len(self._active_watch_indices) > 0
        self._mutex.unlock()

    def _poll_watch_variables(self):
        """Poll all active watch variables."""
        if not self._app_state.is_connected():
            logging.debug("_poll_watch_variables: not connected")
            return

        self._mutex.lock()
        indices = self._active_watch_indices.copy()
        self._mutex.unlock()

        logging.debug(f"_poll_watch_variables: polling indices {indices}")
        for index in indices:
            watch_var = self._app_state.get_watch_var(index)
            logging.debug(f"_poll_watch_variables: index={index}, name='{watch_var.name}'")
            if watch_var.name and watch_var.name != "None":
                # Use cached var_ref for faster polling
                value = self._app_state.read_watch_var_value(index)
                logging.debug(f"_poll_watch_variables: read value={value}")
                if value is not None:
                    self._app_state.update_watch_var_field(index, "value", value)
                    self.watch_var_updated.emit(index, watch_var.name, value)

        # Signal plot update after all variables polled
        if indices:
            self.plot_data_ready.emit()

    # ============= Scope Data (Tab2) =============

    def set_scope_polling_enabled(self, enabled: bool, single_shot: bool = False):
        """Enable or disable scope data polling."""
        self._mutex.lock()
        self._scope_polling_enabled = enabled
        self._scope_single_shot = single_shot
        self._mutex.unlock()

    def _poll_scope_data(self):
        """Poll scope data if ready."""
        if not self._app_state.is_connected():
            return

        if self._app_state.is_scope_data_ready():
            data = self._app_state.get_scope_channel_data()
            if data:
                self.scope_data_ready.emit(data)

                # Handle single-shot mode
                self._mutex.lock()
                is_single_shot = self._scope_single_shot
                self._mutex.unlock()

                if is_single_shot:
                    self.set_scope_polling_enabled(False)
                else:
                    # Request next data
                    self._app_state.request_scope_data()

    # ============= Live Variables (Tab3) =============

    def set_live_polling_enabled(self, enabled: bool):
        """Enable or disable live variable polling (Tab3)."""
        self._mutex.lock()
        self._live_polling_enabled = enabled
        self._mutex.unlock()

    def set_active_live_indices(self, indices: List[int]):
        """Set which live variable indices should be polled."""
        self._mutex.lock()
        self._active_live_indices = indices.copy()
        self._mutex.unlock()

    def add_active_live_index(self, index: int):
        """Add a live variable index to active polling."""
        logging.debug(f"add_active_live_index: adding index {index}")
        self._mutex.lock()
        if index not in self._active_live_indices:
            self._active_live_indices.append(index)
        self._live_polling_enabled = len(self._active_live_indices) > 0
        logging.debug(f"add_active_live_index: enabled={self._live_polling_enabled}, indices={self._active_live_indices}")
        self._mutex.unlock()

    def remove_active_live_index(self, index: int):
        """Remove a live variable index from active polling."""
        self._mutex.lock()
        if index in self._active_live_indices:
            self._active_live_indices.remove(index)
        self._live_polling_enabled = len(self._active_live_indices) > 0
        self._mutex.unlock()

    def _poll_live_variables(self):
        """Poll all active live variables (Tab3)."""
        if not self._app_state.is_connected():
            logging.debug("_poll_live_variables: not connected")
            return

        self._mutex.lock()
        indices = self._active_live_indices.copy()
        self._mutex.unlock()

        logging.debug(f"_poll_live_variables: polling indices {indices}")
        for index in indices:
            live_var = self._app_state.get_live_watch_var(index)
            logging.debug(f"_poll_live_variables: index={index}, name='{live_var.name}'")
            if live_var.name and live_var.name != "None":
                # Use cached var_ref for faster polling
                value = self._app_state.read_live_watch_var_value(index)
                logging.debug(f"_poll_live_variables: read value={value}")
                if value is not None:
                    self._app_state.update_live_watch_var_field(index, "value", value)
                    self.live_var_updated.emit(index, live_var.name, value)

    # ============= Interval Configuration =============

    def set_watch_interval(self, interval_ms: int):
        """Set the watch variable polling interval."""
        self._mutex.lock()
        self._watch_interval_ms = max(50, interval_ms)
        self._mutex.unlock()

    def set_scope_interval(self, interval_ms: int):
        """Set the scope data polling interval."""
        self._mutex.lock()
        self._scope_interval_ms = max(50, interval_ms)
        self._mutex.unlock()

    def set_live_interval(self, interval_ms: int):
        """Set the live variable polling interval."""
        self._mutex.lock()
        self._live_interval_ms = max(50, interval_ms)
        self._mutex.unlock()
