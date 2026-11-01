"""Create a VS Code task that starts pyX2Cscope for an MPLAB VS Code project.

The MPLAB extension for VS Code stores the project in ``.vscode/<project>.mplab.json``. Each
build configuration in that file has an ``imagePath`` with the ELF file it generates, e.g.
``./out/my_project/default.elf``. :func:`write_vscode_tasks` adds a "Run pyX2Cscope" task for
every configuration to ``.vscode/tasks.json``, so pyX2Cscope can be started from
**Terminal > Run Task** with the right ELF file and connection settings.

Typical usage from the command line::

    pyX2Cscope --vscode-task path/to/my_project
"""

import json
import os
import sys
from pathlib import Path

TASK_LABEL = "Run pyX2Cscope"
TASKS_FILE_NAME = "tasks.json"
TASKS_VERSION = "2.0.0"
MPLAB_PROJECT_SUFFIX = ".mplab.json"
VSCODE_DIR_NAME = ".vscode"
BACKUP_SUFFIX = ".bak"
DEFAULT_PORT = "AUTO"
# Paths up to this many folders above the project are written relative to it, others absolute.
_MAX_PARENT_LEVELS = 1


class VSCodeTaskError(Exception):
    """Raised when the VS Code task cannot be created."""


def _scan_json(text: str, handle_outside):
    """Walk through JSON text and let a callback handle every position outside of strings.

    Args:
        text (str): The text to scan.
        handle_outside: Callback ``(text, index) -> (output, next_index)`` for positions outside strings.

    Returns:
        str: The text built from the strings and the callback output.
    """
    result = []
    i, length = 0, len(text)
    in_string = False
    while i < length:
        char = text[i]
        if in_string:
            result.append(char)
            if char == "\\" and i + 1 < length:
                result.append(text[i + 1])
                i += 1
            elif char == '"':
                in_string = False
            i += 1
        elif char == '"':
            in_string = True
            result.append(char)
            i += 1
        else:
            output, i = handle_outside(text, i)
            result.append(output)
    return "".join(result)


def _skip_comment(text: str, i: int) -> tuple[str, int]:
    """Drop a ``//`` or ``/* */`` comment starting at index i, keep any other character."""
    if text.startswith("//", i):
        end = text.find("\n", i)
        return "", len(text) if end == -1 else end
    if text.startswith("/*", i):
        end = text.find("*/", i + 2)
        return "", len(text) if end == -1 else end + 2
    return text[i], i + 1


def _skip_trailing_comma(text: str, i: int) -> tuple[str, int]:
    """Drop a comma at index i if only whitespace follows before a closing bracket."""
    if text[i] == ",":
        j = i + 1
        while j < len(text) and text[j].isspace():
            j += 1
        if j < len(text) and text[j] in "}]":
            return "", i + 1
    return text[i], i + 1


def _strip_jsonc(text: str) -> str:
    """Remove comments and trailing commas from JSON with comments (JSONC), as used by VS Code.

    Args:
        text (str): The JSONC text.

    Returns:
        str: Plain JSON text.
    """
    return _scan_json(_scan_json(text, _skip_comment), _skip_trailing_comma)


def _load_jsonc(path: Path) -> tuple[dict, bool]:
    """Load a JSON file that may contain comments.

    Args:
        path (Path): The file to read.

    Returns:
        tuple[dict, bool]: The parsed content and True if comments or trailing commas were removed.

    Raises:
        VSCodeTaskError: If the file is not valid JSON or JSONC.
    """
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text), False
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_strip_jsonc(text)), True
    except json.JSONDecodeError as e:
        raise VSCodeTaskError(f"Cannot read {path}: {e}") from e


def find_mplab_project(project_dir: Path) -> Path:
    """Find the MPLAB VS Code project file ``.vscode/<project>.mplab.json``.

    Args:
        project_dir (Path): The VS Code project folder.

    Returns:
        Path: The project file. If there are several, the one named after the folder is preferred.

    Raises:
        VSCodeTaskError: If no project file is found.
    """
    vscode_dir = project_dir / VSCODE_DIR_NAME
    candidates = sorted(vscode_dir.glob(f"*{MPLAB_PROJECT_SUFFIX}")) if vscode_dir.is_dir() else []
    if not candidates:
        raise VSCodeTaskError(
            f"No MPLAB VS Code project found: {vscode_dir / ('*' + MPLAB_PROJECT_SUFFIX)} does not exist."
        )
    for candidate in candidates:
        if candidate.name[: -len(MPLAB_PROJECT_SUFFIX)].lower() == project_dir.name.lower():
            return candidate
    return candidates[0]


def get_elf_images(mplab_file: Path) -> list[tuple[str, str]]:
    """Read the build configurations and their ELF files from an MPLAB VS Code project file.

    Args:
        mplab_file (Path): The ``.mplab.json`` project file.

    Returns:
        list[tuple[str, str]]: (configuration name, imagePath) for every configuration with an ELF file.

    Raises:
        VSCodeTaskError: If no configuration with an ``imagePath`` is found.
    """
    project, _ = _load_jsonc(mplab_file)
    images = []
    for config in project.get("configurations", []):
        image_path = config.get("imagePath")
        if image_path:
            images.append((config.get("name", "default"), image_path))
    if not images:
        raise VSCodeTaskError(f"No configuration with an 'imagePath' found in {mplab_file}.")
    return images


def _get_launcher(executable: str | None = None, frozen: bool | None = None) -> tuple[Path, list]:
    """Return the program that starts pyX2Cscope and its leading arguments.

    Args:
        executable (str, optional): Program to use. Defaults to the running interpreter or executable.
        frozen (bool, optional): True for the standalone executable. Defaults to the running program.

    Returns:
        tuple[Path, list]: The program and the arguments that start pyX2Cscope with it.
    """
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    program = Path(executable or sys.executable).resolve()
    return program, ([] if frozen else ["-m", "pyx2cscope"])


def _to_task_path(path: Path, project_dir: Path, folder_var: str) -> str:
    """Express a path relative to the workspace folder if it is inside or next to it, else absolute.

    A relative path keeps a project and a pyX2Cscope folder next to it portable, e.g.
    ``${workspaceFolder:name}/../pyX2Cscope/pyX2Cscope.exe``.

    Args:
        path (Path): The absolute path.
        project_dir (Path): The VS Code project folder.
        folder_var (str): The VS Code variable of the project folder, e.g. ``${workspaceFolder:name}``.

    Returns:
        str: The path with forward slashes, as used in tasks.json.
    """
    try:
        relative = Path(os.path.relpath(path, project_dir))
    except ValueError:
        # Different drives on Windows: a relative path is not possible
        return path.as_posix()
    if relative.parts.count("..") > _MAX_PARENT_LEVELS:
        return path.as_posix()
    return f"{folder_var}/{relative.as_posix()}"


def build_tasks(
    project_dir: Path,
    gui_args: list | None = None,
    executable: str | None = None,
    frozen: bool | None = None,
) -> list[dict]:
    """Build one "Run pyX2Cscope" task per build configuration of the MPLAB VS Code project.

    Args:
        project_dir (Path): The VS Code project folder.
        gui_args (list, optional): pyX2Cscope arguments for the task. Defaults to ``["-p", "AUTO"]``.
        executable (str, optional): Program that starts pyX2Cscope. Defaults to the running one.
        frozen (bool, optional): True if ``executable`` is the standalone executable.

    Returns:
        list[dict]: The tasks.

    Raises:
        VSCodeTaskError: If the project file or its ELF configurations are not found.
    """
    project_dir = Path(project_dir).resolve()
    gui_args = ["-p", DEFAULT_PORT] if gui_args is None else list(gui_args)
    images = get_elf_images(find_mplab_project(project_dir))
    folder_var = "${workspaceFolder:" + project_dir.name + "}"
    program, launcher_args = _get_launcher(executable, frozen)

    tasks = []
    for config_name, image_path in images:
        elf = image_path[2:] if image_path.startswith("./") else image_path
        label = TASK_LABEL if len(images) == 1 else f"{TASK_LABEL} ({config_name})"
        tasks.append({
            "label": label,
            "type": "process",
            "command": _to_task_path(program, project_dir, folder_var),
            "args": [*launcher_args, *gui_args, "-e", f"{folder_var}/{elf}"],
            "options": {"cwd": _to_task_path(program.parent, project_dir, folder_var)},
            "presentation": {"reveal": "always", "panel": "new"},
            "problemMatcher": [],
        })
    return tasks


def write_vscode_tasks(
    project_dir: str | Path = ".",
    gui_args: list | None = None,
    executable: str | None = None,
    frozen: bool | None = None,
) -> tuple[Path, list[dict]]:
    """Add the "Run pyX2Cscope" tasks to ``.vscode/tasks.json`` of an MPLAB VS Code project.

    Existing tasks are kept; tasks with the same label are replaced. If the existing file
    contains comments, they cannot be kept and the original file is saved as ``tasks.json.bak``.

    Args:
        project_dir (str | Path): The VS Code project folder. Defaults to the current folder.
        gui_args (list, optional): pyX2Cscope arguments for the task. Defaults to ``["-p", "AUTO"]``.
        executable (str, optional): Program that starts pyX2Cscope. Defaults to the running one.
        frozen (bool, optional): True if ``executable`` is the standalone executable.

    Returns:
        tuple[Path, list[dict]]: The tasks.json file and the tasks that were written.

    Raises:
        VSCodeTaskError: If the project is not an MPLAB VS Code project or tasks.json cannot be read.
    """
    project_dir = Path(project_dir).resolve()
    new_tasks = build_tasks(project_dir, gui_args, executable, frozen)
    tasks_file = project_dir / VSCODE_DIR_NAME / TASKS_FILE_NAME

    content = {"version": TASKS_VERSION, "tasks": []}
    if tasks_file.exists():
        content, had_comments = _load_jsonc(tasks_file)
        if not isinstance(content, dict) or not isinstance(content.get("tasks", []), list):
            raise VSCodeTaskError(f"Unexpected content in {tasks_file}.")
        if had_comments:
            backup = tasks_file.with_name(TASKS_FILE_NAME + BACKUP_SUFFIX)
            backup.write_text(tasks_file.read_text(encoding="utf-8"), encoding="utf-8")
        content.setdefault("version", TASKS_VERSION)

    # Replace tasks with the same label in place, append the others
    pending = {task["label"]: task for task in new_tasks}
    merged = []
    for task in content.get("tasks", []):
        label = task.get("label") if isinstance(task, dict) else None
        merged.append(pending.pop(label) if label in pending else task)
    content["tasks"] = merged + list(pending.values())

    tasks_file.write_text(json.dumps(content, indent=4) + "\n", encoding="utf-8")
    return tasks_file, new_tasks
