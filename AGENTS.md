# AGENTS.md

Instructions for AI coding agents working on **pyX2Cscope**. This is the Python implementation of the
Microchip X2Cscope tool and the LNet protocol, used to read, write and scope variables on a running
embedded target (dsPIC, PIC32, SAM/ARM, dsPIC33A). Human-facing docs live in `README.md` and `doc/`.

## Tech stack

- Python `>=3.10,<3.15` (CI tests 3.10, 3.12, 3.13, 3.14 on Ubuntu).
- Packaging: setuptools via `pyproject.toml` only (no setup.py, poetry or uv). Use `pip`.
- Core dependencies: `mchplnet` (LNet protocol and serial/CAN/TCP interfaces), `pyelftools` (DWARF/ELF
  parsing), `pyserial`, `python-can`, `numpy`, `pyyaml`.
- GUIs: PyQt5 + pyqtgraph (desktop) and Flask + Flask-SocketIO (web).
- Docs: Sphinx with `sphinx-autoapi`, `myst-parser`, `sphinx_rtd_theme`.
- Distribution: PyPI wheel, plus PyInstaller executables for Windows and Linux.

## Project layout

```
pyx2cscope/                 Package source
  __init__.py               __version__ and set_logger()
  __main__.py               CLI: build_parser() (argparse) and main(), launches the Qt or web GUI
  x2cscope.py               Public API: X2CScope class, TriggerConfig
  utils.py                  Reads/creates config.ini in the current working directory, get_project_name()
  vscode.py                 Writes the "Run pyX2Cscope" task to .vscode/tasks.json (--vscode-task)
  parser/                   ELF parsing: ElfParser (ABC), DummyParser, GenericParser (pyelftools)
  variable/                 Variable types (Int8..Uint64, Float, Enum) and VariableFactory (ELF/YAML/PKL)
  gui/qt/                   Qt GUI: main_window, controllers/, models/, tabs/, workers/, dialogs/
  gui/web/                  Flask GUI: app.py, scope.py (web_scope singleton), ws_handlers.py, views/,
                            templates/, static/
  gui/watchView/            Legacy matplotlib/PyQt5 GUI
  gui/resources/            Scripting tab help and template
  examples/                 Example scripts (all need real hardware)
tests/                      pytest suite; tests/data/ holds reference ELF files
doc/                        Sphinx sources (conf.py, *.rst, *.md)
scripts/                    build.py, update_version.py, startWebInterface.bat, rpi setup zip
mchplnet/                   Git submodule (upstream LNet library). Do not edit here.
pyx2cscope_win.spec         PyInstaller spec (Windows)
pyx2cscope_linux.spec       PyInstaller spec (Linux)
```

The communication interface is selected by keyword arguments to `X2CScope(...)`: `port=` gives serial,
`host=` gives TCP/IP, and `bustype=` gives CAN. Without any of them it uses serial with auto-detection:
it tries every available serial port and connects to the first one where an LNet device answers. The
same happens with `port="AUTO"`, `port=""` or `port=None`. If no device answers, it raises
`RuntimeError`. `X2CScope(elf_file=...)` alone is therefore a valid way to connect over serial.

## Setup and commands

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux/macOS
pip install -e ".[dev,docs,build]"
git submodule update --init       # only needed to browse mchplnet sources; runtime uses PyPI mchplnet
```

| Task | Command |
|---|---|
| Lint (must pass in CI) | `ruff check .` |
| Tests | `pytest` (on headless machines set `QT_QPA_PLATFORM=offscreen`) |
| Single test | `pytest tests/test_<name>.py -k <expr>` |
| Docs | `sphinx-build -M html doc build --keep-going` |
| Wheel/sdist | `python -m build` |
| Windows exe | `pyinstaller --noconfirm pyx2cscope_win.spec` or `python scripts/build.py` |
| Linux exe | `pyinstaller --noconfirm pyx2cscope_linux.spec` |
| CLI help | `pyx2cscope --help` |
| VS Code task for a firmware project | `pyx2cscope --vscode-task path/to/project` |
| Run Qt GUI | `pyx2cscope` or `python -m pyx2cscope` |
| Run web GUI | `pyx2cscope -w` (port 5000 by default) |

Before finishing a change, run `ruff check .` and `pytest`. If you changed docs or docstrings, also
build the docs.

## Coding conventions

- Ruff config is in `pyproject.toml`: line length 120, rule sets `D`, `I`, `N`, `F`, `PL`, and
  `PLR0913` is ignored. There is no auto-formatter, so match the surrounding style.
- Docstrings use **Google style** and are required on modules, classes and public functions
  (`Args:`, `Returns:`, `Raises:`).
- Imports are sorted isort-style (ruff `I`).
- Avoid magic numbers (ruff `PLR2004`). Use named constants, including in tests (e.g. `HTTP_OK = 200`).
- Use the stdlib `logging` module, not `print`, in library code.
- Keep the public API in `pyx2cscope/x2cscope.py` backward compatible. Examples, docs and user
  scripts depend on it.
- New features should come with tests in `tests/`, and with docs in `doc/` when they are user-facing.

## Testing rules

- Tests must not need hardware. Mock the transport with `tests/utils/serial_stub.py`
  (`fake_serial(mocker, 16 | 32, device_profile="dspic" | "pic32" | "arm" | "dspic33a")`).
  CAN tests patch `can.interface.Bus`.
- Use the committed ELF files in `tests/data/` and reference them through `tests.data`. Do not replace
  or regenerate them, because assertions depend on their exact contents.
- `tests/conftest.py` resets the web `web_scope` singleton after each test. Keep new web tests
  compatible with this.
- `tests/test_spec_imports.py` checks that every `hiddenimports` entry in the PyInstaller specs can be
  imported. Only add hidden imports for packages that are installed dependencies.

## Writing scripts that use X2CScope

Example scripts, user scripts and any code an agent generates for a target must run unchanged in three
environments:

1. As a plain Python program (`python my_script.py`).
2. In the **Scripting tab of the Qt GUI** (`pyx2cscope/gui/qt/tabs/scripting_tab.py`).
3. In the **Scripting tab of the web GUI** (`pyx2cscope/gui/web/ws_handlers.py`).

Both scripting tabs run the script with `exec()` in a worker thread. They inject these globals:

| Global | Content |
|---|---|
| `x2cscope` | The GUI's live `X2CScope` instance, or `None` when the GUI is not connected |
| `stop_requested` | Callable that returns `True` once the user presses **Stop** |
| `__name__` | `"__main__"` |
| `__file__` | Qt: full path of the script. Web: only the file name sent by the browser (e.g. `script.py`) |

`stdout`/`stderr` are redirected to the tab's output panel, so scripts report progress with `print()`.
`sys.exit()` is caught and shown as the exit code. This is the one place where `print` is preferred
over `logging`.

### Required rules

- **Reuse the injected instance.** Only create an `X2CScope` when none was injected:
  `if globals().get("x2cscope") is None:`. Never write `global x2cscope` followed by
  `if x2cscope is None:`; it raises `NameError` when the script runs standalone.
- **Only disconnect what you created.** Calling `x2cscope.disconnect()` on the injected instance
  closes the GUI's own connection. Remember whether the script owns the connection and disconnect only
  in that case.
- **Make every loop and wait stoppable.** Use `stop_requested = globals().get("stop_requested", lambda: False)`
  and check it in every loop. Do not use long `time.sleep()` calls; sleep in short slices and check
  `stop_requested()` between them.
- **Always time out when polling the scope.** `is_scope_data_ready()` stays `False` forever if the
  trigger never fires.
- **Restore what you write.** If the script changes target variables, save their original values first
  and write them back in a `finally:` block, so the target is left as it was after errors or Stop.
- **Check variables.** `get_variable()` returns `None` when the name is not in the ELF. Fail early with
  a clear message.
- **Don't open windows.** Scripts run in a worker thread and possibly on a headless server (Raspberry
  Pi service). If you plot, use `matplotlib.use("Agg")`, save figures and CSV files to disk, and never
  call `plt.show()`.
- **Build output paths from `__file__`** with `os.path.dirname(os.path.abspath(__file__))`. In the web
  GUI this resolves to the server's current working directory, and the files are written on the
  server, not on the browser's machine.
- **No hard-coded hardware settings.** Read the ELF path, COM port, host and CAN settings from
  `pyx2cscope.utils` (`get_elf_file_path()`, `get_com_port()`, `get_host_address()`,
  `get_can_config()`), which use `config.ini`. Put firmware-specific values (variable names, scope
  call frequency, trigger levels) in named constants at the top of the script.

### Variables

- `x2cscope.list_variables()` and `x2cscope.list_sfr()` return the names found in the ELF file.
- `x2cscope.get_variable("name")` returns a `Variable`, or `None` if the name is unknown. Struct
  members and array elements use C syntax: `"motor.apiData.velocityReference"`, `"my_array2D[1][0]"`.
  Use `get_variable("NAME", sfr=True)` for peripheral registers (SFRs).
- `var.get_value()` reads from the target. Arrays return a flat list. On a communication error it
  logs the error and returns `None`.
- `var.set_value(value)` writes to the target and raises `ValueError` if the value is outside the
  range of the variable's type. Array elements can also be written with `var[index] = value`.

### Scope: channels, sampling, triggers and data

The scope records samples into a buffer on the target, inside the firmware's X2Cscope update call
(usually an ISR). Configure everything **before** starting a capture:

1. **Channels:** `clear_all_scope_channel()`, then `add_scope_channel(var)` for each variable.
   `remove_scope_channel(var)` removes one. All channels share one buffer (up to 8 channels), so fewer
   and smaller variables give a longer capture.
2. **Sampling:** `set_sample_time(n)`. `1` stores every sample, `n` stores every n-th call of the
   firmware's scope update.
3. **Trigger:** either a free-running capture with `reset_scope_trigger()`, or a triggered one with
   `set_scope_trigger(TriggerConfig(var, trigger_level=..., trigger_mode=1, trigger_delay=..., trigger_edge=...))`.
   - `trigger_mode`: `1` triggered, `0` auto (free-running).
   - `trigger_edge`: `1` rising, `0` falling.
   - `trigger_level`: in the trigger variable's units. Values outside the variable's range are clamped.
   - `trigger_delay`: a number of samples. A positive value keeps that many
     samples from before the trigger event (pre-trigger history), e.g. `50`. A negative value is a
     post-trigger delay, and the data is then returned without rotation.
4. **Start:** `request_scope_data()` sends the configuration and starts the capture. If the script
   itself causes the trigger event (for example by writing a variable with `set_value()`), wait until
   the pre-trigger part of the buffer is filled first.
5. **Wait:** poll `is_scope_data_ready()` every 50 to 100 ms, with a timeout and a `stop_requested()`
   check.
6. **Read:** `get_scope_channel_data()` returns `{channel_name: [values, ...]}`. For triggered captures
   the data is already rotated, so the pre-trigger samples come first.
7. **Repeat:** for continuous captures, call `request_scope_data()` again after reading the data.

The time between two stored samples is `n / f_scope` seconds, where `n` is the sample factor and
`f_scope` the call frequency of the firmware's scope update (e.g. 20 kHz). Build the time axis as
`i * n / f_scope`. `get_scope_sample_time(t_us)` returns the total capture length in ms for a scope
call period of `t_us` microseconds.

### Script skeleton

```python
"""Capture one triggered scope buffer with pyX2Cscope (standalone, Qt or web Scripting tab)."""

import csv
import os
import time

from pyx2cscope.utils import get_elf_file_path
from pyx2cscope.x2cscope import TriggerConfig, X2CScope

CHANNEL_VARS = ["myModule.signalA", "myModule.signalB"]   # adapt to your firmware
TRIGGER_VAR = "myModule.signalA"
TRIGGER_LEVEL = 100
TRIGGER_EDGE = 1                # 1 rising, 0 falling
TRIGGER_DELAY = 50              # pre-trigger samples
SAMPLE_FACTOR = 1               # store every sample
SCOPE_FREQUENCY_HZ = 20_000     # call rate of the firmware scope update
CAPTURE_TIMEOUT_S = 10.0
POLL_S = 0.05

# Reuse the instance injected by the Scripting tab, otherwise create our own
owns_connection = globals().get("x2cscope") is None
if owns_connection:
    x2cscope = X2CScope(elf_file=get_elf_file_path())
stop_requested = globals().get("stop_requested", lambda: False)


def get_var(name):
    """Return a variable or stop the script with a clear message."""
    var = x2cscope.get_variable(name)
    if var is None:
        raise SystemExit(f"Variable '{name}' not found in the ELF file.")
    return var


try:
    x2cscope.clear_all_scope_channel()
    for name in CHANNEL_VARS:
        x2cscope.add_scope_channel(get_var(name))
    x2cscope.set_sample_time(SAMPLE_FACTOR)
    x2cscope.set_scope_trigger(TriggerConfig(
        get_var(TRIGGER_VAR), trigger_level=TRIGGER_LEVEL, trigger_mode=1,
        trigger_delay=TRIGGER_DELAY, trigger_edge=TRIGGER_EDGE,
    ))

    x2cscope.request_scope_data()
    deadline = time.time() + CAPTURE_TIMEOUT_S
    while not x2cscope.is_scope_data_ready():
        if stop_requested():
            raise SystemExit("Stopped by user.")
        if time.time() > deadline:
            raise SystemExit("Scope capture timed out: the trigger did not fire.")
        time.sleep(POLL_S)

    data = x2cscope.get_scope_channel_data()
    dt = SAMPLE_FACTOR / SCOPE_FREQUENCY_HZ
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture.csv")
    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", *data.keys()])
        for i, row in enumerate(zip(*data.values())):
            writer.writerow([i * dt, *row])
    print(f"Saved {len(next(iter(data.values()), []))} samples to {out_file}")
finally:
    if owns_connection:
        x2cscope.disconnect()
```

If the script writes variables, read their original values before the `try:` work starts and write them
back at the top of the `finally:` block.

## Starting pyX2Cscope from a VS Code firmware project

When you work in a firmware project built with the MPLAB extension for VS Code (it has
`.vscode/<project>.mplab.json`) and the user wants to run pyX2Cscope or a script against that firmware,
check whether `.vscode/tasks.json` already has a task labelled `Run pyX2Cscope`. If it does not, create it
with the CLI instead of writing it by hand:

```bash
pyx2cscope --vscode-task path/to/project            # Qt GUI, serial port AUTO
pyx2cscope --vscode-task path/to/project -w         # Web GUI
pyx2cscope --vscode-task path/to/project -p COM3    # fixed serial port
```

Use the same program the user runs pyX2Cscope with (`pyX2Cscope.exe` for the standalone executable,
`pyx2cscope` or `python -m pyx2cscope` for a pip install), because the task starts that program.

- The ELF file of each build configuration is read from `imagePath` in `.mplab.json`
  (e.g. `./out/<project>/default.elf`). Several configurations give one task each,
  `Run pyX2Cscope (<configuration>)`.
- Paths use `${workspaceFolder:<project>}` and stay relative when pyX2Cscope is inside or next to the
  project folder, otherwise they are absolute.
- Existing tasks are kept and a task with the same label is replaced. A `tasks.json` with comments is
  rewritten without them and the original is saved as `tasks.json.bak`; tell the user about it.
- The user runs the task with **Terminal > Run Task > Run pyX2Cscope**. The task starts the GUI and
  connects with `-p` and `-e`.
- Projects without `.mplab.json` (e.g. MPLAB X only) are rejected with an error. For those, describe the
  manual task from `doc/vscode.rst` instead.

## Versioning, branches and PRs

- The version source of truth is `pyproject.toml` (`[project] version`). After bumping it, run
  `python scripts/update_version.py`, which syncs `pyx2cscope/__init__.py`. The pre-commit hook does
  the same. Do not edit `__version__` by hand.
- Branch from `develop` and name the branch `feature/<issue-number>-<short-slug>`. PRs target
  `develop`. `main` is for releases only: merging to `main` publishes docs to gh-pages and the package
  to PyPI.
- PRs into `main` must bump the version (CI `version-check`).
- Commit messages are short, imperative subject lines. Reference the issue or PR number when there is
  one.

## Boundaries and pitfalls

- **Do not edit** `mchplnet/` (submodule, changes go upstream), vendored third-party assets in
  `pyx2cscope/gui/web/static/js` and `static/css`, or the files in `tests/data/`.
- **Never commit** `config.ini`, `*.log`, `build/`, `dist/`, or `pyx2cscope/gui/web/upload/`. These
  are created at runtime and are gitignored. `config.ini` is written to the current working directory
  by `pyx2cscope.utils`.
- Creating `X2CScope(...)` talks to the target right away. Without hardware or a mock it fails, so do
  not run `examples/` scripts as a way to verify a change.
- Importing `pyx2cscope.x2cscope` calls `logging.basicConfig` and writes `pyx2cscope.x2cscope.log`.
  Running `__main__` resets the root log handlers.
- `pyx2cscope/__main__.py:main()` is the single entry point for the `pyx2cscope` console script,
  `python -m pyx2cscope` and the PyInstaller executables. Importing the module must not start a GUI.
  `--install` is handled before argparse; all other options are defined in `build_parser()`. When you
  add or change an option, update `doc/cli.rst` and `tests/test_cli.py`, which test the real parser.
- Qt code needs a display. Use `QT_QPA_PLATFORM=offscreen` for tests. Linux CI also uses Xvfb.
- The web server uses CORS `*`. Binding it with `--host 0.0.0.0` exposes it on the network, and the
  scripting tabs (Qt and web) run arbitrary Python. Do not weaken these defaults further.
- The PyInstaller specs are tracked even though `.gitignore` contains `*.spec`. Edit the existing
  files; do not recreate them.
- The code is cross-platform (Windows, Linux, Raspberry Pi). Do not hard-code paths or COM ports.
  Use `pathlib`/`os.path`.
- `scripts/pyx2cscope-rpi-setup.zip` holds the Raspberry Pi installer (`install.sh`, `configure.sh`,
  `uninstall.sh`, systemd service running `python -m pyx2cscope -w --host 0.0.0.0`). It is a binary
  archive: unpack it, change it, and re-zip it rather than editing it in place.
