"""Data Logger widget: writes the values of all dashboard widgets to a CSV file in Run mode.

Columns are fixed when logging starts: `timestamp`, `elapsed_s`, then one or more columns per
widget, as returned by each widget spec's `log(frame)` function (see registry.py).

Sampling has its own precise timer, independent of the 33 ms display update, so the sample
period can be anything from 1 ms upwards. Samples are scheduled on a fixed grid
(0, T, 2T, ... after Start), so there is no drift; if the computer can't keep up, samples are
skipped rather than written in a burst. Rows are flushed at least every FLUSH_S seconds, so the
file can be read while logging and at most a fraction of a second is lost if the program dies.
"""

import csv
import os
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

CSV_FILTER = "CSV file (*.csv);;All files (*)"
SEPARATORS = {"comma": ",", "semicolon": ";", "tab": "\t"}
FILE_MODES = ("overwrite", "append", "new file per start")
MIN_MS, MAX_MS = 1, 3_600_000
FLUSH_S = 0.25      # write buffered rows to disk at least this often
STATUS_S = 0.2      # refresh the status text at most this often (cheap at high sample rates)


def sample_ms(props):
    """Sample period in ms, clamped to MIN_MS..MAX_MS."""
    return int(max(MIN_MS, min(MAX_MS, round(float(props.get("sample_ms", 1000))))))


def fmt_period(ms):
    if ms >= 60_000 and ms % 60_000 == 0:
        return f"{ms // 60_000} min"
    if ms >= 1000 and ms % 1000 == 0:
        return f"{ms // 1000} s"
    return f"{ms} ms"


def session_path(path, mode, now=None):
    """'new file per start' inserts a timestamp before the extension: log.csv -> log_20261102_140305.csv"""
    if mode != "new file per start":
        return path
    root, ext = os.path.splitext(path)
    return f"{root}_{(now or datetime.now()):%Y%m%d_%H%M%S}{ext or '.csv'}"


def fmt_value(v, decimal="."):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        s = f"{v:.10g}"
        return s.replace(".", ",") if decimal == "," else s
    return "" if v is None else str(v)


class LoggerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.props = {}
        self.state = "stopped"  # stopped | logging | paused
        self.rows = 0
        self.path = ""  # file of the current/last session
        self.error = ""
        self._fh = None
        self._writer = None
        self._columns = []
        self._t_start = 0.0
        self._k = 0            # index of the next sample on the grid k * period
        self._period = 1.0     # seconds, fixed at Start
        self._last_flush = self._last_status = 0.0
        self._running = False  # dashboard in Run mode
        self._picked = ""  # file chosen at Start when none is configured
        self.skipped = 0       # samples skipped because the PC could not keep up
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._sample)

        self._title = QLabel()
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.start_btn = QPushButton()
        self.start_btn.clicked.connect(self.toggle_start)
        self.pause_btn = QPushButton()
        self.pause_btn.clicked.connect(self.toggle_pause)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.pause_btn)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)
        lay.addWidget(self._title)
        lay.addWidget(self._status, 1, Qt.AlignTop)
        lay.addLayout(buttons)
        self._refresh()

    # ------------------------------------------------------------ helpers
    def _frame(self):
        return self.parentWidget()

    def _canvas(self):
        return getattr(self._frame(), "canvas", None)

    def configure(self, props):
        self.props = props
        self._title.setText(props.get("title", ""))
        self._title.setVisible(bool(props.get("title")))
        f = self._title.font()
        f.setBold(True)
        self._title.setFont(f)
        self._refresh()

    def _refresh(self):
        logging = self.state != "stopped"
        self.start_btn.setText("■ Stop" if logging else "● Start")
        self.pause_btn.setText("▶ Resume" if self.state == "paused" else "❚❚ Pause")
        self.start_btn.setEnabled(self._running)
        self.pause_btn.setEnabled(self._running and logging)
        name = os.path.basename(self.path or self.props.get("file", "")) or "(file asked at Start)"
        rate = fmt_period(round(self._period * 1000) if logging else sample_ms(self.props))
        skipped = f", {self.skipped} skipped" if self.skipped else ""
        if self.error:
            text, color = f"⚠ {self.error}", "#d03b3b"
        elif self.state == "logging":
            text, color = f"● Logging every {rate}: {self.rows} rows{skipped} → {name}", "#0ca30c"
        elif self.state == "paused":
            text, color = f"❚❚ Paused: {self.rows} rows{skipped} → {name}", "#b07800"
        elif self.rows:
            text, color = f"Stopped: {self.rows} rows written to {name}", ""
        elif self._running:
            text, color = f"Stopped. Press Start to log to {name}", ""
        else:
            text, color = f"Logs every {rate} to {name} in Run mode", "#898781"
        self._status.setText(text)
        self._status.setToolTip(self.path or self.props.get("file", ""))
        self._status.setStyleSheet(f"color:{color}" if color else "")

    # ------------------------------------------------------------ run mode hooks
    def set_running(self, running):
        self._running = running
        if not running:
            self.stop()
        else:
            self.rows, self.error, self.path, self._picked = 0, "", "", ""
            if self.props.get("auto_start"):
                self.start()
        self._refresh()

    def _elapsed(self):
        return time.perf_counter() - self._t_start

    def _schedule(self):
        """Arms the timer for the next grid point k * period."""
        delay_ms = (self._k * self._period - self._elapsed()) * 1000
        self._timer.start(max(0, int(delay_ms)))  # PreciseTimer: ~1 ms accuracy on Windows

    def _sample(self):
        if self.state != "logging":
            return
        now = self._elapsed()
        due = self._k * self._period
        if now + 0.0005 < due:  # woke up a little early: wait for the grid point
            self._schedule()
            return
        self._write_row(due)  # elapsed_s is the scheduled sample time, so it is exactly k * period
        if self.state != "logging":  # write error
            return
        self._k += 1
        behind = int((now - self._k * self._period) / self._period) + 1 if now >= self._k * self._period else 0
        if behind:  # couldn't keep up (busy PC, modal dialog, too fast): skip, don't burst
            self.skipped += behind
            self._k += behind
        t = time.perf_counter()
        if t - self._last_flush >= FLUSH_S:
            self._flush()
        if t - self._last_status >= STATUS_S:
            self._last_status = t
            self._refresh()
        self._schedule()

    def _flush(self):
        self._last_flush = time.perf_counter()
        if self._fh:
            try:
                self._fh.flush()
            except OSError as e:
                self.error = f"Write failed: {e.strerror or e}"
                self.stop()

    # ------------------------------------------------------------ buttons
    def toggle_start(self):
        self.stop() if self.state != "stopped" else self.start()

    def toggle_pause(self):
        if self.state == "logging":
            self.state = "paused"
            self._timer.stop()
            self._flush()
        elif self.state == "paused":
            self.state = "logging"
            # log a row right away, then continue on the original grid (elapsed time keeps counting)
            self._k = max(self._k, int(self._elapsed() / self._period))
            self._schedule()
        self._refresh()

    # ------------------------------------------------------------ logging
    def _choose_file(self):
        path, _ = QFileDialog.getSaveFileName(self.window(), "Data Logger: CSV file", "datalog.csv", CSV_FILTER,
                                              options=QFileDialog.DontConfirmOverwrite)
        return path

    def start(self):
        if self.state != "stopped" or not self._running:
            return False
        canvas = self._canvas()
        base = self.props.get("file", "").strip() or self._picked
        if not base:
            # no file configured: ask once; reused for later starts until Run mode ends
            base = self._choose_file()
            if not base:
                return False
            self._picked = base
        mode = self.props.get("mode", "overwrite")
        path = session_path(base, mode)
        cols = []
        for f in canvas.frames if canvas else []:
            if f.inner is self or not f.spec.log:
                continue
            for col, _ in f.spec.log(f):
                cols.append((f, col))
        try:
            d = os.path.dirname(os.path.abspath(path))
            os.makedirs(d, exist_ok=True)
            write_header = mode != "append" or not os.path.exists(path) or os.path.getsize(path) == 0
            self._fh = open(path, "a" if mode == "append" else "w", newline="", encoding="utf-8-sig"
                            if write_header else "utf-8")
        except OSError as e:
            self.error = f"Cannot open {path}: {e.strerror or e}. Is it open in another program?"
            self._refresh()
            QMessageBox.warning(self.window(), "Data Logger", self.error)
            return False
        self.path, self.error, self.rows = path, "", 0
        self._columns = cols
        self._writer = csv.writer(self._fh, delimiter=SEPARATORS.get(self.props.get("separator"), ","))
        if write_header:
            self._writer.writerow(["timestamp", "elapsed_s"] + [c for _, c in cols])
            self._fh.flush()
        self._period = sample_ms(self.props) / 1000
        self._k, self.skipped = 0, 0
        self._t_start = self._last_flush = time.perf_counter()
        self.state = "logging"
        self._refresh()
        self._sample()  # first row immediately, at elapsed 0
        return True

    def _write_row(self, elapsed):
        dec = self.props.get("decimal", ".")
        values = {}
        row = [datetime.now().isoformat(sep=" ", timespec="milliseconds"), fmt_value(round(elapsed, 3), dec)]
        for f, col in self._columns:
            if f not in values:
                try:
                    values[f] = dict(f.spec.log(f))
                except RuntimeError:  # widget deleted
                    values[f] = {}
            row.append(fmt_value(values[f].get(col), dec))
        try:
            self._writer.writerow(row)
        except OSError as e:
            self.error = f"Write failed: {e.strerror or e}"
            self.stop()
            return
        self.rows += 1

    def stop(self):
        self._timer.stop()
        if self._fh:
            try:
                self._fh.close()
            except OSError:
                pass
        self._fh = self._writer = None
        self.state = "stopped"
        self._refresh()
