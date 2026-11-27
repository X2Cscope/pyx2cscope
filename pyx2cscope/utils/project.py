"""Find the MPLAB X or MPLAB VS Code project of a firmware.

Functions:
    get_project_name(file_path) -> str: Derives the project name from an ELF/YML/PKL file path.
    find_vscode_project_files(folder) -> list[Path]: Lists the MPLAB VS Code project files of a folder.
"""

from pathlib import Path

# How many parent folders are searched for an MPLAB X or VS Code project folder.
_PROJECT_ROOT_SEARCH_DEPTH = 6
# Suffix of the MPLAB X project folder, e.g. "my_project.X" (compared in lower case).
MPLABX_PROJECT_SUFFIX = ".x"
# Folder of the VS Code settings in a project.
VSCODE_DIR_NAME = ".vscode"
# Suffix of the project file the MPLAB extension for VS Code creates in ".vscode".
MPLAB_PROJECT_SUFFIX = ".mplab.json"


def find_vscode_project_files(folder: Path) -> list[Path]:
    """Return the MPLAB VS Code project files ``.vscode/*.mplab.json`` of a folder.

    Args:
        folder (Path): The folder that may contain a VS Code project.

    Returns:
        list[Path]: The project files sorted by name; empty if there are none or the folder cannot be read.
    """
    vscode_dir = Path(folder) / VSCODE_DIR_NAME
    try:
        if not vscode_dir.is_dir():
            return []
        return sorted(
            entry for entry in vscode_dir.iterdir() if entry.name.lower().endswith(MPLAB_PROJECT_SUFFIX)
        )
    except OSError:
        return []


def vscode_project_name(project_file: Path) -> str:
    """Return the project name of an MPLAB VS Code project file, e.g. ``my_project.mplab.json`` gives ``my_project``."""
    return project_file.name[: -len(MPLAB_PROJECT_SUFFIX)]


def _find_ide_project_name(path: Path) -> str:
    """Return the name of the MPLAB X or VS Code project folder that contains the file.

    Args:
        path (Path): Path of the ELF, YML or PKL file.

    Returns:
        str: The project name, or an empty string if no project folder is found.
    """
    # Only folders that are part of the given path; a bare file name has no project folder.
    folders = [folder for folder in path.parents if folder != Path(".")]
    for folder in folders[:_PROJECT_ROOT_SEARCH_DEPTH]:
        # MPLAB X project folder, e.g. "my_project.X/dist/default/production/my_project.X.production.elf"
        if folder.name.lower().endswith(MPLABX_PROJECT_SUFFIX):
            return folder.name[: -len(MPLABX_PROJECT_SUFFIX)]
        # VS Code project with the MPLAB extension: ".vscode/my_project.mplab.json"
        project_files = find_vscode_project_files(folder)
        if project_files:
            return vscode_project_name(project_files[0])
    return ""


def get_project_name(file_path: str) -> str:
    """Derive the project name from the path of an ELF, YML or PKL file.

    The name is the MPLAB X or VS Code project that generated the file:

    1. MPLAB X: the project folder ``my_project.X`` gives ``my_project``.
    2. VS Code with the MPLAB extension: the project file ``.vscode/my_project.mplab.json``
       gives ``my_project``.
    3. If no project is found, the file name without extension, e.g. ``firmware.elf`` gives ``firmware``.

    Args:
        file_path (str): Path of the ELF, YML or PKL file. May be only a file name.

    Returns:
        str: The project name, or an empty string if no path is given.
    """
    if not file_path:
        return ""
    path = Path(file_path)
    return _find_ide_project_name(path) or path.stem
