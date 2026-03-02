"""Variable selection dialog for searching and selecting variables."""

from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
)


class VariableSelectionDialog(QDialog):
    """Dialog for searching and selecting a variable from a list.

    Provides a search bar to filter variables and a list to select from.
    Double-clicking or pressing OK selects the highlighted variable.
    """

    def __init__(self, variables: List[str], parent=None):
        """Initialize the variable selection dialog.

        Args:
            variables: A list of available variable names to select from.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.variables = variables
        self.selected_variable: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Search Variable")
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self._filter_variables)
        layout.addWidget(self.search_bar)

        # Variable list
        self.variable_list = QListWidget(self)
        self.variable_list.addItems(self.variables)
        self.variable_list.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.variable_list)

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.button_box.accepted.connect(self._accept_selection)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _filter_variables(self, text: str):
        """Filter the variables based on user input in the search bar.

        Args:
            text: The input text to filter variables.
        """
        self.variable_list.clear()
        filtered_variables = [
            var for var in self.variables if text.lower() in var.lower()
        ]
        self.variable_list.addItems(filtered_variables)

    def _accept_selection(self):
        """Accept the selection when a variable is chosen from the list."""
        selected_items = self.variable_list.selectedItems()
        if selected_items:
            self.selected_variable = selected_items[0].text()
            self.accept()
