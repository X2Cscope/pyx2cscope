"""Resources for the Qt GUI."""

import os

RESOURCES_DIR = os.path.dirname(__file__)


def get_resource_path(filename: str) -> str:
    """Get the full path to a resource file."""
    return os.path.join(RESOURCES_DIR, filename)
