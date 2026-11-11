"""Dashboard tab: load a dashboard that was built with the Dashboard Creator and use it live."""

import json
import os
import time

from PyQt5.QtCore import QSettings, QTimer
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .canvas import Canvas
from .variables import VariableBridge, parse_source, variable_sources

FILE_FILTER = "Dashboard (*.dash.json *.json)"
TICK_MS = 33
SETTINGS_KEY = "dashboard/last_file"


class DashboardViewer(QWidget):
    """Shows a saved dashboard and updates it live with the variables of the connected target."""

    def __init__(self, app_state, parent=None):
        """Initialize the viewer.

        Args:
            app_state: The pyX2Cscope AppState that provides the variables.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.app_state = app_state
        self.path = ""
        self._settings = QSettings("Microchip", "pyX2Cscope")
        self.bridge = VariableBridge(app_state.read_variable_value, self._write_variable)
        self._t0 = time.perf_counter()
        self._running = False

        self.canvas = Canvas()
        self.canvas.set_edit_mode(False)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setStyleSheet("QScrollArea{background:#e1e0d9;}")

        self._open_btn = QPushButton("Open Dashboard…")
        self._open_btn.clicked.connect(self.open_dialog)
        self._reload_btn = QPushButton("Reload")
        self._reload_btn.setToolTip("Load the file again, e.g. after saving it in the Dashboard Creator")
        self._reload_btn.clicked.connect(self.reload)
        self._run_btn = QPushButton("Stop")
        self._run_btn.setCheckable(True)
        self._run_btn.setChecked(True)
        self._run_btn.toggled.connect(self._toggle_run)
        self._label = QLabel("No dashboard loaded. Open a .dash.json file, or build one with "
                             "the Dashboard Creator button in the Setup tab.")
        self._label.setStyleSheet("color:#666;")

        bar = QHBoxLayout()
        for w in (self._open_btn, self._reload_btn, self._run_btn):
            bar.addWidget(w)
        bar.addSpacing(10)
        bar.addWidget(self._label, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(scroll, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._update_buttons()

    # ---------------------------------------------------------------- files
    def open_dialog(self):
        """Ask for a dashboard file and load it."""
        start = self.path or self._settings.value(SETTINGS_KEY, "", type=str)
        path, _ = QFileDialog.getOpenFileName(self, "Open Dashboard", start, FILE_FILTER)
        if path:
            self.load(path)

    def reload(self):
        """Load the current dashboard file again."""
        if self.path:
            self.load(self.path)

    def load(self, path: str) -> bool:
        """Load a dashboard file and start it.

        Args:
            path: The ``.dash.json`` file.

        Returns:
            bool: True when the dashboard was loaded.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return False
        self._stop()
        self.canvas.load_dict(data)
        self.canvas.set_edit_mode(False)
        self.path = path
        self._settings.setValue(SETTINGS_KEY, path)
        self._label.setText(os.path.basename(path))
        self._update_buttons()
        if self._run_btn.isChecked():
            self._start()
        return True

    # ---------------------------------------------------------------- run
    def _toggle_run(self, on: bool):
        self._run_btn.setText("Stop" if on else "Run")
        if on:
            self._start()
        else:
            self._stop()

    def _start(self):
        if self._running or not self.canvas.frames:
            return
        self._running = True
        self._t0 = time.perf_counter()
        for f in self.canvas.frames:
            if f.type in ("ytgraph", "xygraph"):
                f.inner.clear()
            elif f.type == "slider":  # moving a slider writes its variable
                f.inner.userChanged.connect(lambda v, f=f: self.bridge.write(f.props.get("source", ""), v))
        self.bridge.start(variable_sources(self.canvas.frames))
        for f in self.canvas.frames:
            if f.type == "logger":
                f.inner.set_running(True)
        self._timer.start()

    def _stop(self):
        if not self._running:
            return
        self._running = False
        self._timer.stop()
        self.bridge.stop()
        for f in self.canvas.frames:
            if f.type == "slider":
                f.inner.userChanged.disconnect()
            elif f.type == "logger":
                f.inner.set_running(False)

    def _tick(self):
        t = time.perf_counter() - self._t0
        for f in self.canvas.frames:
            if f.spec.tick:
                f.spec.tick(f, t, self._resolve)

    def _resolve(self, frame, idx, source, t, freq, phase):
        """Return (value, True) of a variable data source; widgets without a variable get 0."""
        if parse_source(source):
            return self.bridge.value(source), True
        return 0.0, True

    def _write_variable(self, name, value, sfr):
        return self.app_state.write_variable(name, value, sfr=sfr)

    def _update_buttons(self):
        self._reload_btn.setEnabled(bool(self.path))
        self._run_btn.setEnabled(bool(self.canvas.frames))

    def shutdown(self):
        """Stop reading variables; called when the application closes."""
        self._stop()
