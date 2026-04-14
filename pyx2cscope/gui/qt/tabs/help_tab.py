"""Help tab for the Qt GUI application."""

import platform
import subprocess
import sys
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QFont, QDesktopServices

import pyx2cscope


class HelpTab(QWidget):
    """Help tab containing links to GitHub, release notes, and version info."""

    def __init__(self, parent=None):
        """Initialize the help tab."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Release Notes Section
        release_group = QGroupBox("Release Notes and Documentation")
        release_layout = QVBoxLayout(release_group)

        release_info = QLabel(
            "View the latest release notes, changelog, and documentation."
        )
        release_info.setWordWrap(True)
        release_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        release_layout.addWidget(release_info)

        release_button_layout = QHBoxLayout()

        self.release_notes_btn = QPushButton("View Release Notes")
        self.release_notes_btn.clicked.connect(self._open_release_notes)
        release_button_layout.addWidget(self.release_notes_btn)

        self.documentation_btn = QPushButton("Documentation")
        self.documentation_btn.clicked.connect(self._open_documentation)
        release_button_layout.addWidget(self.documentation_btn)
        release_button_layout.addStretch()

        release_layout.addLayout(release_button_layout)
        layout.addWidget(release_group)

        # GitHub Issues Section
        github_group = QGroupBox("Report Issues and Request Features")
        github_layout = QVBoxLayout(github_group)

        github_info = QLabel(
            "If you encounter bugs, have feature requests, or need help, "
            "please open an issue on our GitHub repository."
        )
        github_info.setWordWrap(True)
        github_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        github_layout.addWidget(github_info)

        github_button_layout = QHBoxLayout()

        self.github_issues_btn = QPushButton("Open GitHub Issues")
        self.github_issues_btn.clicked.connect(self._open_github_issues)
        github_button_layout.addWidget(self.github_issues_btn)

        self.github_repo_btn = QPushButton("Visit Repository")
        self.github_repo_btn.clicked.connect(self._open_github_repo)
        github_button_layout.addWidget(self.github_repo_btn)
        github_button_layout.addStretch()

        github_layout.addLayout(github_button_layout)
        layout.addWidget(github_group)

        # Software Versions Section
        version_group = QGroupBox("Software Versions")
        version_layout = QVBoxLayout(version_group)

        version_info = QLabel("Current software and dependency versions:")
        version_info.setStyleSheet("color: #666; margin-bottom: 10px;")
        version_layout.addWidget(version_info)

        self.version_text = QTextEdit()
        self.version_text.setReadOnly(True)
        self.version_text.setMaximumHeight(250)
        self.version_text.setStyleSheet(
            "QTextEdit { "
            "background-color: #f8f9fa; "
            "border: 1px solid #dee2e6; "
            "border-radius: 4px; "
            "padding: 10px; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 10pt; "
            "}"
        )
        self._populate_version_info()
        version_layout.addWidget(self.version_text)

        layout.addWidget(version_group)

        # Additional Resources
        resources_group = QGroupBox("Additional Resources")
        resources_layout = QVBoxLayout(resources_group)

        resources_text = QLabel(
            "For additional support and resources:\n"
            "• Check the examples directory for usage examples\n"
            "• Review the README file for installation instructions\n"
            "• Join our community discussions on GitHub\n"
            "• Visit the documentation for detailed guides"
        )
        resources_text.setWordWrap(True)
        resources_text.setStyleSheet("color: #666; line-height: 1.8; padding: 5px;")
        resources_layout.addWidget(resources_text)

        layout.addWidget(resources_group)

        # Add stretch to push everything to the top
        layout.addStretch()

    def _open_github_issues(self):
        """Open GitHub issues page in default browser."""
        url = QUrl("https://github.com/X2Cscope/pyx2cscope/issues")
        QDesktopServices.openUrl(url)

    def _open_github_repo(self):
        """Open GitHub repository page in default browser."""
        url = QUrl("https://github.com/X2Cscope/pyx2cscope")
        QDesktopServices.openUrl(url)

    def _open_release_notes(self):
        """Open GitHub releases page in default browser."""
        url = QUrl("https://github.com/X2Cscope/pyx2cscope/releases")
        QDesktopServices.openUrl(url)

    def _open_documentation(self):
        """Open documentation in default browser."""
        url = QUrl("https://x2cscope.github.io/pyx2cscope/")
        QDesktopServices.openUrl(url)

    def _populate_version_info(self):
        """Populate the version information text area."""
        version_info = []

        # Application Versions Section
        version_info.append("=== Application ===")
        version_info.append(f"pyX2Cscope: {pyx2cscope.__version__}")

        # Core Dependencies Section
        version_info.append("\n=== Core Dependencies ===")

        # mchplnet version (important dependency)
        try:
            import mchplnet
            version_info.append(f"mchplnet: {mchplnet.__version__}")
        except (ImportError, AttributeError):
            version_info.append("mchplnet: Not installed")

        # mchplnet dependencies
        mchplnet_deps = [
            ("can", "python-can"),
        ]

        for import_name, display_name in mchplnet_deps:
            try:
                module = __import__(import_name)
                version = getattr(module, "__version__", "Unknown")
                version_info.append(f"{display_name}: {version}")
            except (ImportError, AttributeError):
                version_info.append(f"{display_name}: Not installed")

        # Try to get other dependency versions
        dependencies = [
            ("numpy", "numpy"),
            ("matplotlib", "matplotlib"),
            ("serial", "pyserial"),  # pyserial is imported as 'serial'
            ("elftools", "pyelftools")
        ]

        for import_name, display_name in dependencies:
            try:
                module = __import__(import_name)
                if display_name == "pyserial":
                    version = getattr(module, "VERSION", "Unknown")
                else:
                    version = getattr(module, "__version__", "Unknown")
                version_info.append(f"{display_name}: {version}")
            except (ImportError, AttributeError):
                version_info.append(f"{display_name}: Not installed")

        # GUI Framework Section
        version_info.append("\n=== GUI Framework ===")
        try:
            from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            version_info.append(f"Qt: {QT_VERSION_STR}")
            version_info.append(f"PyQt5: {PYQT_VERSION_STR}")
        except ImportError:
            version_info.append("PyQt5: Not available")

        # System Information Section
        version_info.append("\n=== System Information ===")
        version_info.append(f"Python: {sys.version.split()[0]}")  # Show version without extra info
        version_info.append(f"Platform: {platform.platform()}")
        version_info.append(f"Architecture: {platform.architecture()[0]}")

        processor = platform.processor()
        if processor:  # Only show if available
            version_info.append(f"Processor: {processor}")

        self.version_text.setPlainText("\n".join(version_info))
