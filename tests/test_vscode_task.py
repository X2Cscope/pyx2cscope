"""Tests for creating the VS Code "Run pyX2Cscope" task (pyx2cscope.vscode and --vscode-task).

Tests cover:
- Finding the MPLAB VS Code project file and its ELF configurations
- Building the task (command, args, cwd, relative and absolute paths)
- Merging into an existing tasks.json, including JSON with comments
- The --vscode-task command-line option
"""

import json
import os

import pytest

from pyx2cscope import __main__ as cli
from pyx2cscope import vscode

PROJECT = "LAB1_HALL"
FOLDER_VAR = "${workspaceFolder:" + PROJECT + "}"
ELF_ARG = f"{FOLDER_VAR}/out/{PROJECT}/default.elf"
TWO_CONFIGS = 2


def _make_project(base, configurations=None, name=PROJECT):
    """Create an MPLAB VS Code project folder with a .mplab.json file."""
    if configurations is None:
        configurations = [{"name": "default", "imagePath": f"./out/{name}/default.elf"}]
    project_dir = base / name
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / f"{name}.mplab.json").write_text(
        json.dumps({"version": "1.9", "configurations": configurations}), encoding="utf-8"
    )
    return project_dir


def _exe_next_to(project_dir):
    """Return the path of a standalone executable in a pyX2Cscope folder next to the project."""
    return str(project_dir.parent / "pyX2Cscope" / "pyX2Cscope.exe")


def _read_tasks(project_dir):
    """Read the tasks of .vscode/tasks.json."""
    return json.loads((project_dir / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]


class TestFindProject:
    """Tests for finding the MPLAB VS Code project."""

    def test_no_project(self, tmp_path):
        """Test a folder without .vscode/*.mplab.json is rejected."""
        with pytest.raises(vscode.VSCodeTaskError, match="No MPLAB VS Code project"):
            vscode.find_mplab_project(tmp_path)

    def test_prefers_file_named_after_folder(self, tmp_path):
        """Test the project file named after the folder is used when there are several."""
        project_dir = _make_project(tmp_path)
        (project_dir / ".vscode" / "aaa_other.mplab.json").write_text("{}", encoding="utf-8")

        assert vscode.find_mplab_project(project_dir).name == f"{PROJECT}.mplab.json"

    def test_elf_images(self, tmp_path):
        """Test the configurations and their ELF files are read."""
        project_dir = _make_project(tmp_path)

        images = vscode.get_elf_images(vscode.find_mplab_project(project_dir))

        assert images == [("default", f"./out/{PROJECT}/default.elf")]

    def test_no_image_path(self, tmp_path):
        """Test a project without imagePath is rejected."""
        project_dir = _make_project(tmp_path, configurations=[{"name": "default"}])

        with pytest.raises(vscode.VSCodeTaskError, match="imagePath"):
            vscode.get_elf_images(vscode.find_mplab_project(project_dir))


class TestBuildTasks:
    """Tests for building the task."""

    def test_standalone_executable_next_to_project(self, tmp_path):
        """Test the task matches the hand-written lab task for an executable next to the project."""
        project_dir = _make_project(tmp_path)

        tasks = vscode.build_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)

        assert tasks == [{
            "label": "Run pyX2Cscope",
            "type": "process",
            "command": f"{FOLDER_VAR}/../pyX2Cscope/pyX2Cscope.exe",
            "args": ["-p", "AUTO", "-e", ELF_ARG],
            "options": {"cwd": f"{FOLDER_VAR}/../pyX2Cscope"},
            "presentation": {"reveal": "always", "panel": "new"},
            "problemMatcher": [],
        }]

    def test_python_interpreter_uses_module(self, tmp_path):
        """Test a Python interpreter starts pyX2Cscope with -m pyx2cscope."""
        project_dir = _make_project(tmp_path)
        python = str(tmp_path / "venv" / "python.exe")

        task = vscode.build_tasks(project_dir, executable=python, frozen=False)[0]

        assert task["args"][:2] == ["-m", "pyx2cscope"]

    def test_far_away_executable_is_absolute(self, tmp_path):
        """Test an executable more than one folder above the project is written as an absolute path."""
        project_dir = _make_project(tmp_path / "a" / "b")
        exe = tmp_path / "tools" / "pyX2Cscope.exe"

        task = vscode.build_tasks(project_dir, executable=str(exe), frozen=True)[0]

        assert task["command"] == exe.resolve().as_posix()
        assert task["options"]["cwd"] == exe.resolve().parent.as_posix()

    def test_gui_args(self, tmp_path):
        """Test the given pyX2Cscope arguments are used before the ELF file."""
        project_dir = _make_project(tmp_path)

        task = vscode.build_tasks(project_dir, ["-p", "COM3", "-w"], _exe_next_to(project_dir), frozen=True)[0]

        assert task["args"] == ["-p", "COM3", "-w", "-e", ELF_ARG]

    def test_one_task_per_configuration(self, tmp_path):
        """Test every configuration gets its own task, labelled with the configuration name."""
        project_dir = _make_project(tmp_path, configurations=[
            {"name": "default", "imagePath": "./out/LAB1_HALL/default.elf"},
            {"name": "debug", "imagePath": "./out/LAB1_HALL/debug.elf"},
        ])

        tasks = vscode.build_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)

        assert [t["label"] for t in tasks] == ["Run pyX2Cscope (default)", "Run pyX2Cscope (debug)"]
        assert tasks[1]["args"][-1] == f"{FOLDER_VAR}/out/{PROJECT}/debug.elf"


class TestWriteTasks:
    """Tests for writing .vscode/tasks.json."""

    def test_creates_tasks_file(self, tmp_path):
        """Test a new tasks.json is created."""
        project_dir = _make_project(tmp_path)

        tasks_file, tasks = vscode.write_vscode_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)

        content = json.loads(tasks_file.read_text(encoding="utf-8"))
        assert content["version"] == "2.0.0"
        assert content["tasks"] == tasks

    def test_keeps_other_tasks_and_replaces_same_label(self, tmp_path):
        """Test existing tasks are kept and an old 'Run pyX2Cscope' task is replaced in place."""
        project_dir = _make_project(tmp_path)
        existing = {"version": "2.0.0", "tasks": [
            {"label": "Build", "type": "shell", "command": "make"},
            {"label": "Run pyX2Cscope", "type": "process", "command": "old.exe"},
            {"label": "Flash", "type": "shell", "command": "flash"},
        ]}
        (project_dir / ".vscode" / "tasks.json").write_text(json.dumps(existing), encoding="utf-8")

        vscode.write_vscode_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)

        tasks = _read_tasks(project_dir)
        assert [t["label"] for t in tasks] == ["Build", "Run pyX2Cscope", "Flash"]
        assert tasks[1]["command"] == f"{FOLDER_VAR}/../pyX2Cscope/pyX2Cscope.exe"

    def test_tasks_file_with_comments(self, tmp_path):
        """Test a tasks.json with comments and trailing commas is read and backed up."""
        project_dir = _make_project(tmp_path)
        original = (
            '{\n  // VS Code tasks\n  "version": "2.0.0",\n  "tasks": [\n'
            '    {"label": "Build", "command": "http://example//path", /* inline */},\n  ],\n}\n'
        )
        (project_dir / ".vscode" / "tasks.json").write_text(original, encoding="utf-8")

        vscode.write_vscode_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)

        tasks = _read_tasks(project_dir)
        assert tasks[0] == {"label": "Build", "command": "http://example//path"}
        assert (project_dir / ".vscode" / "tasks.json.bak").read_text(encoding="utf-8") == original

    def test_invalid_tasks_file_is_not_overwritten(self, tmp_path):
        """Test an unreadable tasks.json is reported and left unchanged."""
        project_dir = _make_project(tmp_path)
        tasks_file = project_dir / ".vscode" / "tasks.json"
        tasks_file.write_text("{ not json", encoding="utf-8")

        with pytest.raises(vscode.VSCodeTaskError, match="Cannot read"):
            vscode.write_vscode_tasks(project_dir, executable=_exe_next_to(project_dir), frozen=True)
        assert tasks_file.read_text(encoding="utf-8") == "{ not json"


class TestVSCodeTaskCLI:
    """Tests for the --vscode-task command-line option."""

    @pytest.fixture(autouse=True)
    def _no_gui(self, mocker):
        """Fail if a GUI would be started."""
        self.execute_qt = mocker.patch("pyx2cscope.gui.execute_qt")
        self.execute_web = mocker.patch("pyx2cscope.gui.execute_web")

    def test_help_lists_option(self):
        """Test --vscode-task is listed in the help."""
        assert "--vscode-task" in cli.build_parser().format_help()

    def test_writes_task_without_gui(self, tmp_path, monkeypatch, capsys):
        """Test --vscode-task writes the task, prints it and starts no GUI or config.ini."""
        project_dir = _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        cli.main(["--vscode-task", str(project_dir)])

        assert _read_tasks(project_dir)[0]["label"] == "Run pyX2Cscope"
        assert "Run pyX2Cscope" in capsys.readouterr().out
        assert not (tmp_path / "config.ini").exists()
        self.execute_qt.assert_not_called()
        self.execute_web.assert_not_called()

    def test_default_is_current_folder(self, tmp_path, monkeypatch):
        """Test --vscode-task without a folder uses the current folder."""
        project_dir = _make_project(tmp_path)
        monkeypatch.chdir(project_dir)

        cli.main(["--vscode-task"])

        assert (project_dir / ".vscode" / "tasks.json").exists()

    def test_gui_options_copied(self, tmp_path):
        """Test -p, -w, -wp and --host are copied into the task."""
        project_dir = _make_project(tmp_path)

        cli.main(["--vscode-task", str(project_dir), "-p", "COM3", "-w", "-wp", "8080", "--host", "0.0.0.0"])

        args = _read_tasks(project_dir)[0]["args"]
        start = args.index("-p")
        assert args[start:] == ["-p", "COM3", "-w", "-wp", "8080", "--host", "0.0.0.0", "-e", ELF_ARG]

    def test_not_a_project(self, tmp_path):
        """Test a folder without MPLAB VS Code project ends with an error message."""
        with pytest.raises(SystemExit) as exc:
            cli.main(["--vscode-task", str(tmp_path)])

        assert "No MPLAB VS Code project" in str(exc.value.code)
        assert not os.path.exists(tmp_path / ".vscode" / "tasks.json")
