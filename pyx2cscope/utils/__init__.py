"""Helper functions for scripts and the command line.

- :mod:`pyx2cscope.utils.config`: settings of ``config.ini`` (ELF file, COM port, host IP, CAN).
- :mod:`pyx2cscope.utils.project`: the MPLAB X or MPLAB VS Code project of a firmware.
- :mod:`pyx2cscope.utils.vscode`: the "Run pyX2Cscope" VS Code task (``--vscode-task``).

The functions of ``config`` and ``project`` are also available here, e.g.
``from pyx2cscope.utils import get_com_port, get_elf_file_path``.
"""

from pyx2cscope.utils.config import (
    get_can_config,
    get_com_port,
    get_config_file,
    get_elf_file_path,
    get_host_address,
)
from pyx2cscope.utils.project import get_project_name

__all__ = [
    "get_can_config",
    "get_com_port",
    "get_config_file",
    "get_elf_file_path",
    "get_host_address",
    "get_project_name",
]
