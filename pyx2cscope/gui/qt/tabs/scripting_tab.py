"""Scripting tab - Execute Python scripts with access to x2cscope."""

import io
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt5.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pyx2cscope.gui.resources import get_resource_path

if TYPE_CHECKING:
    from pyx2cscope.gui.qt.models.app_state import AppState


class ScriptHelpDialog(QDialog):
    """Dialog showing help for writing scripts."""

    def __init__(self, parent=None):
        """Initialize the script help dialog."""
        super().__init__(parent)
        self.setWindowTitle("Script Help")
        self.setMinimumSize(700, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        help_browser = QTextBrowser()
        help_browser.setOpenExternalLinks(True)
        help_browser.setStyleSheet(
            "QTextBrowser { font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; }"
        )
        help_browser.setMarkdown(self._load_help_content())
        layout.addWidget(help_browser)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_help_content(self) -> str:
        """Load help content from external markdown file."""
        try:
            help_path = get_resource_path("script_help.md")
            with open(help_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"# Error\n\nCould not load help file: {e}\n\nPlease check that `script_help.md` exists in the resources folder."


class ScriptWorker(QThread):
    """Worker thread for executing Python scripts."""

    output_ready = pyqtSignal(str)
    finished_with_code = pyqtSignal(int)

    def __init__(self, script_path: str, x2cscope, parent=None):
        """Initialize the script worker.

        Args:
            script_path: Path to the Python script to execute.
            x2cscope: The x2cscope instance to inject into script namespace.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._script_path = script_path
        self._x2cscope = x2cscope
        self._stop_requested = False

    def is_stop_requested(self) -> bool:
        """Check if stop has been requested. Scripts should call this in loops."""
        return self._stop_requested

    def run(self):
        """Execute the script in this thread."""
        exit_code = 0

        # Create a custom stdout/stderr that emits signals
        class OutputCapture(io.StringIO):
            def __init__(self, signal):
                super().__init__()
                self._signal = signal

            def write(self, text):
                if text:
                    self._signal.emit(text)
                return len(text) if text else 0

            def flush(self):
                pass

        stdout_capture = OutputCapture(self.output_ready)
        stderr_capture = OutputCapture(self.output_ready)

        try:
            with open(self._script_path, "r", encoding="utf-8") as f:
                script_code = f.read()

            # Create namespace with x2cscope and stop_requested function
            namespace = {
                "__name__": "__main__",
                "__file__": self._script_path,
                "x2cscope": self._x2cscope,
                "stop_requested": self.is_stop_requested,
            }

            # Execute with captured output
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compile(script_code, self._script_path, "exec"), namespace)

        except SystemExit as e:
            # Handle sys.exit() calls in scripts
            exit_code = e.code if isinstance(e.code, int) else 1
        except StopIteration:
            # Script was stopped via stop_requested
            exit_code = 0
        except Exception as e:
            self.output_ready.emit(f"\nScript error: {e}\n")
            self.output_ready.emit(traceback.format_exc())
            exit_code = 1

        self.finished_with_code.emit(exit_code)

    def request_stop(self):
        """Request the script to stop. Scripts should check stop_requested() in loops."""
        self._stop_requested = True


class ScriptingTab(QWidget):
    """Tab for executing Python scripts with x2cscope access.

    Features:
    - Select and execute Python scripts
    - View script output in real-time (separate tab)
    - Log messages with timestamps (separate tab)
    - Option to log output to file with custom location
    - Edit scripts with IDLE
    - Scripts can access the x2cscope instance from the main app
    """

    # Signals
    script_started = pyqtSignal()
    script_finished = pyqtSignal(int)  # exit code

    def __init__(self, app_state: "AppState", parent=None):
        """Initialize the Scripting tab.

        Args:
            app_state: The centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._script_path = ""
        self._settings = QSettings("Microchip", "pyX2Cscope")
        self._worker = None
        self._log_file = None
        self._log_file_path = ""

        self._setup_ui()

    def _setup_ui(self):  # noqa: PLR0915
        """Set up the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        # === Script Selection Group ===
        script_group = QGroupBox("Script Selection")
        script_layout = QHBoxLayout()
        script_layout.setSpacing(8)
        script_layout.setContentsMargins(10, 15, 10, 10)
        script_group.setLayout(script_layout)

        # Script path display
        self._script_path_edit = QLineEdit()
        self._script_path_edit.setReadOnly(True)
        self._script_path_edit.setPlaceholderText("No script selected")
        script_layout.addWidget(self._script_path_edit, 1)

        # Browse button
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(80)
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        script_layout.addWidget(self._browse_btn)

        # Edit button
        self._edit_btn = QPushButton("Edit Script")
        self._edit_btn.setFixedWidth(90)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._edit_btn.setEnabled(False)
        self._edit_btn.setToolTip("Open script in text editor")
        script_layout.addWidget(self._edit_btn)

        # Help button
        self._help_btn = QPushButton("Help")
        self._help_btn.setFixedWidth(60)
        self._help_btn.clicked.connect(self._on_help_clicked)
        script_layout.addWidget(self._help_btn)

        main_layout.addWidget(script_group)

        # === Execution Controls Group ===
        controls_group = QGroupBox("Execution Controls")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setContentsMargins(10, 15, 10, 10)
        controls_group.setLayout(controls_layout)

        # First row: Execute, Stop, Status
        row1_layout = QHBoxLayout()

        # Execute button
        self._execute_btn = QPushButton("Execute")
        self._execute_btn.setFixedSize(100, 30)
        self._execute_btn.clicked.connect(self._on_execute_clicked)
        self._execute_btn.setEnabled(False)
        row1_layout.addWidget(self._execute_btn)

        # Stop button
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedSize(100, 30)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setToolTip("Request script to stop (may not work for blocking operations)")
        row1_layout.addWidget(self._stop_btn)

        # Status label
        row1_layout.addStretch()
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #666;")
        row1_layout.addWidget(self._status_label)

        controls_layout.addLayout(row1_layout)

        # Second row: Log to file checkbox and path
        row2_layout = QHBoxLayout()

        # Log to file checkbox
        self._log_checkbox = QCheckBox("Log output to file:")
        self._log_checkbox.setChecked(False)
        self._log_checkbox.stateChanged.connect(self._on_log_checkbox_changed)
        row2_layout.addWidget(self._log_checkbox)

        # Log file path display
        self._log_path_edit = QLineEdit()
        self._log_path_edit.setReadOnly(True)
        self._log_path_edit.setPlaceholderText("Select log file location...")
        self._log_path_edit.setEnabled(False)
        row2_layout.addWidget(self._log_path_edit, 1)

        # Browse log location button
        self._log_browse_btn = QPushButton("Browse...")
        self._log_browse_btn.setFixedWidth(80)
        self._log_browse_btn.clicked.connect(self._on_log_browse_clicked)
        self._log_browse_btn.setEnabled(False)
        row2_layout.addWidget(self._log_browse_btn)

        controls_layout.addLayout(row2_layout)

        main_layout.addWidget(controls_group)

        # === Output Tabs ===
        self._output_tabs = QTabWidget()

        # Script Output tab
        script_output_widget = QWidget()
        script_output_layout = QVBoxLayout(script_output_widget)
        script_output_layout.setContentsMargins(5, 5, 5, 5)

        self._script_output_text = QPlainTextEdit()
        self._script_output_text.setReadOnly(True)
        self._script_output_text.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, monospace; font-size: 10pt; }"
        )
        script_output_layout.addWidget(self._script_output_text)

        # Clear button for script output
        script_clear_layout = QHBoxLayout()
        script_clear_layout.addStretch()
        script_clear_btn = QPushButton("Clear")
        script_clear_btn.setFixedWidth(80)
        script_clear_btn.clicked.connect(self._script_output_text.clear)
        script_clear_layout.addWidget(script_clear_btn)
        script_output_layout.addLayout(script_clear_layout)

        self._output_tabs.addTab(script_output_widget, "Script Output")

        # Log Output tab
        log_output_widget = QWidget()
        log_output_layout = QVBoxLayout(log_output_widget)
        log_output_layout.setContentsMargins(5, 5, 5, 5)

        self._log_output_text = QPlainTextEdit()
        self._log_output_text.setReadOnly(True)
        self._log_output_text.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, monospace; font-size: 10pt; "
            "color: #555; }"
        )
        log_output_layout.addWidget(self._log_output_text)

        # Clear button for log output
        log_clear_layout = QHBoxLayout()
        log_clear_layout.addStretch()
        log_clear_btn = QPushButton("Clear")
        log_clear_btn.setFixedWidth(80)
        log_clear_btn.clicked.connect(self._log_output_text.clear)
        log_clear_layout.addWidget(log_clear_btn)
        log_output_layout.addLayout(log_clear_layout)

        self._output_tabs.addTab(log_output_widget, "Log")

        main_layout.addWidget(self._output_tabs, 1)  # Stretch factor 1

        # === Info Label ===
        info_label = QLabel(
            "Scripts have access to 'x2cscope' variable when connected. "
            "Click Help for examples and documentation."
        )
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

    def _on_log_checkbox_changed(self, state):
        """Handle log checkbox state change."""
        enabled = state == Qt.Checked
        self._log_path_edit.setEnabled(enabled)
        self._log_browse_btn.setEnabled(enabled)

        if enabled and not self._log_file_path:
            # Suggest a default path based on script location
            if self._script_path:
                script_dir = os.path.dirname(self._script_path)
                script_name = os.path.splitext(os.path.basename(self._script_path))[0]
                self._log_file_path = os.path.join(script_dir, f"{script_name}_log.txt")
                self._log_path_edit.setText(self._log_file_path)

    def _on_log_browse_clicked(self):
        """Handle log file browse button click."""
        # Get initial directory
        if self._log_file_path:
            initial_dir = os.path.dirname(self._log_file_path)
        elif self._script_path:
            initial_dir = os.path.dirname(self._script_path)
        else:
            initial_dir = self._settings.value("log_file_dir", "", type=str)

        # Generate default filename with timestamp
        if self._script_path:
            script_name = os.path.splitext(os.path.basename(self._script_path))[0]
            default_name = f"{script_name}_log.txt"
        else:
            default_name = "script_log.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File Location",
            os.path.join(initial_dir, default_name),
            "Text Files (*.txt);;Log Files (*.log);;All Files (*.*)",
        )
        if file_path:
            self._log_file_path = file_path
            self._log_path_edit.setText(file_path)
            self._settings.setValue("log_file_dir", os.path.dirname(file_path))

    def _on_help_clicked(self):
        """Show help dialog."""
        dialog = ScriptHelpDialog(self)
        dialog.exec_()

    def _open_with_system_editor(self, script_path):
        """Open script with the system's default editor or associated application.

        Uses OS-specific methods to open the file with the default application
        associated with .py files.

        Args:
            script_path: Path to the script file to open.
        """
        if sys.platform == "win32":
            # Windows: Use os.startfile to open with associated application
            os.startfile(script_path)
        elif sys.platform == "darwin":
            # macOS: Use 'open' command
            subprocess.Popen(['open', script_path])
        else:
            # Linux: Use xdg-open to respect file associations
            subprocess.Popen(['xdg-open', script_path])

    def _on_browse_clicked(self):
        """Handle browse button click."""
        # Get last directory from settings
        last_dir = self._settings.value("script_file_dir", "", type=str)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Script",
            last_dir,
            "Python Files (*.py);;All Files (*.*)",
        )
        if file_path:
            self._script_path = file_path
            self._script_path_edit.setText(file_path)
            self._settings.setValue("script_file_dir", os.path.dirname(file_path))
            self._edit_btn.setEnabled(True)
            self._execute_btn.setEnabled(True)
            self._log_message(f"Selected script: {file_path}")

            # Update suggested log path if logging is enabled
            if self._log_checkbox.isChecked():
                script_dir = os.path.dirname(file_path)
                script_name = os.path.splitext(os.path.basename(file_path))[0]
                self._log_file_path = os.path.join(script_dir, f"{script_name}_log.txt")
                self._log_path_edit.setText(self._log_file_path)

    def _on_edit_clicked(self):
        """Open the script in the system's default editor."""
        if not self._script_path:
            return

        try:
            # Open with system default application for .py files
            self._open_with_system_editor(self._script_path)
            self._log_message(f"Opened {os.path.basename(self._script_path)} in default editor")
        except Exception as e:
            self._log_message(f"Error opening editor: {e}")

    def _on_execute_clicked(self):
        """Execute the selected script."""
        if not self._script_path:
            return

        if not os.path.exists(self._script_path):
            self._log_message(f"Error: Script file not found: {self._script_path}")
            return

        if self._worker is not None and self._worker.isRunning():
            self._log_message("A script is already running.")
            return

        # Clear script output only
        self._script_output_text.clear()

        # Setup logging if enabled
        if self._log_checkbox.isChecked():
            self._setup_log_file()

        # Update UI state
        self._execute_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("Running...")
        self._status_label.setStyleSheet("color: #0078d4;")

        # Log messages go to Log tab
        self._log_message(f"Script started: {os.path.basename(self._script_path)}")

        # Check if x2cscope is available
        x2cscope = self._app_state.x2cscope
        if x2cscope:
            self._log_message("x2cscope instance available")
        else:
            self._log_message("x2cscope not connected (variable will be None)")

        # Create and start worker thread
        self._worker = ScriptWorker(self._script_path, x2cscope, self)
        self._worker.output_ready.connect(self._on_script_output)
        self._worker.finished_with_code.connect(self._on_script_finished)
        self._worker.start()

        self.script_started.emit()

    def _on_script_output(self, text: str):
        """Handle output from the script worker - goes to Script Output tab."""
        self._append_script_output(text)

    def _on_script_finished(self, exit_code: int):
        """Handle script completion."""
        self._log_message(f"Script finished with exit code {exit_code}")

        # Close log file if open
        if self._log_file:
            self._log_file.close()
            self._log_file = None

        # Update UI state
        self._execute_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if exit_code == 0:
            self._status_label.setText("Completed")
            self._status_label.setStyleSheet("color: green;")
        else:
            self._status_label.setText(f"Finished (code {exit_code})")
            self._status_label.setStyleSheet("color: orange;")

        self._worker = None
        self.script_finished.emit(exit_code)

    def _on_stop_clicked(self):
        """Stop the running script."""
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._log_message("Stop requested (may not work for blocking operations)")
            self._status_label.setText("Stop requested...")
            self._status_label.setStyleSheet("color: orange;")

    def _log_message(self, message: str):
        """Add a timestamped message to the Log tab."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        cursor = self._log_output_text.textCursor()
        cursor.movePosition(cursor.End)
        if not self._log_output_text.toPlainText().endswith("\n") and self._log_output_text.toPlainText():
            cursor.insertText("\n")
        cursor.insertText(formatted)
        self._log_output_text.setTextCursor(cursor)
        self._log_output_text.ensureCursorVisible()

        # Also write to log file if enabled
        if self._log_file:
            try:
                self._log_file.write(f"{formatted}\n")
                self._log_file.flush()
            except Exception:
                pass

    def _append_script_output(self, text: str):
        """Append text to the Script Output tab."""
        cursor = self._script_output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self._script_output_text.setTextCursor(cursor)
        self._script_output_text.ensureCursorVisible()

        # Write to log file if enabled
        if self._log_file:
            try:
                self._log_file.write(text)
                self._log_file.flush()
            except Exception:
                pass

    def _setup_log_file(self):
        """Setup log file for script output."""
        if not self._log_file_path:
            self._log_message("Warning: No log file path specified")
            return

        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(self._log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            self._log_file = open(self._log_file_path, "a", encoding="utf-8")

            # Write header
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_file.write(f"\n{'='*60}\n")
            self._log_file.write(f"Script execution started: {timestamp}\n")
            self._log_file.write(f"Script: {self._script_path}\n")
            self._log_file.write(f"{'='*60}\n\n")
            self._log_file.flush()

            self._log_message(f"Logging to: {self._log_file_path}")
        except Exception as e:
            self._log_message(f"Warning: Could not create log file: {e}")
            self._log_file = None

    def on_connection_changed(self, connected: bool):
        """Handle connection state change."""
        # Update info about x2cscope availability
        if connected:
            self._status_label.setText("Ready (x2cscope available)")
            self._log_message("Connection established - x2cscope now available")
        else:
            self._status_label.setText("Ready (x2cscope not connected)")
            self._log_message("Disconnected - x2cscope not available")
