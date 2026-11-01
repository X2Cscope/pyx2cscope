"""This module provides utility functions for handling configuration settings.

Functions:
    get_config_file() -> ConfigParser: Retrieves the configuration file.
    get_elf_file_path(key="path") -> str: Gets the path to the ELF file from the configuration.
    get_com_port(key="com_port") -> str: Gets the COM port from the configuration.
    get_host_address(key="host_ip") -> str: Gets the host IP address from the configuration.
    get_can_config() -> dict: Gets the CAN interface configuration parameters.
    get_project_name(file_path) -> str: Derives the project name from an ELF/YML/PKL file path.
"""
import logging
import os
from configparser import ConfigParser
from pathlib import Path

# How many parent folders are searched for an MPLAB X or VS Code project folder.
_PROJECT_ROOT_SEARCH_DEPTH = 6
# Suffix of the MPLAB X project folder, e.g. "my_project.X".
_MPLABX_PROJECT_SUFFIX = ".x"
# Suffix of the project file the MPLAB extension for VS Code creates in ".vscode".
_VSCODE_PROJECT_SUFFIX = ".mplab.json"


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
        if folder.name.lower().endswith(_MPLABX_PROJECT_SUFFIX):
            return folder.name[: -len(_MPLABX_PROJECT_SUFFIX)]
        # VS Code project with the MPLAB extension: ".vscode/my_project.mplab.json"
        vscode_dir = folder / ".vscode"
        try:
            if vscode_dir.is_dir():
                for entry in sorted(vscode_dir.iterdir()):
                    if entry.name.lower().endswith(_VSCODE_PROJECT_SUFFIX):
                        return entry.name[: -len(_VSCODE_PROJECT_SUFFIX)]
        except OSError:
            continue
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


def get_config_file() -> ConfigParser:
    """Retrieves the configuration file. If the configuration file does not exist, it creates one with default values.

    Returns:
        ConfigParser: The configuration parser object.
    """
    config_file = "config.ini"
    default_path = {"path": "path_to_your_elf_file"}
    default_com = {"com_port": "your_com_port, ex:COM3"}
    default_host_ip = {"host_ip": "your_host_ip, ex:192.168.1.100"}
    default_can = {
        "bustype": "pcan_usb",
        "channel": "1",
        "baud_rate": "500000",
        "id_tx": "0x110",
        "id_rx": "0x100",
        "mode": "standard"
    }
    config = ConfigParser()
    if os.path.exists(config_file):
        config.read(config_file)
    else:
        # Create the config file with the default value
        config["ELF_FILE"] = default_path
        config["COM_PORT"] = default_com
        config["HOST_IP"] = default_host_ip
        config["CAN"] = default_can
        with open(config_file, "w") as configfile:
            config.write(configfile)
        logging.debug(f"Config file '{config_file}' created with default values")
    return config


def get_elf_file_path(key="path") -> str:
    """Gets the path to the ELF file from the configuration.

    Args:
        key (str): The key for the ELF file path in the configuration. Default is "path".

    Returns:
        str: The path to the ELF file.
    """
    config = get_config_file()
    if not config["ELF_FILE"][key] or "your" in config["ELF_FILE"][key]:
        return ""
    return config["ELF_FILE"][key]


def get_com_port(key="com_port") -> str:
    """Gets the COM port from the configuration.

    Args:
        key (str): The key for the COM port in the configuration. Default is "com_port".

    Returns:
        str: The COM port.
    """
    config = get_config_file()
    if not config["COM_PORT"][key] or "your" in config["COM_PORT"][key]:
        return ""
    return config["COM_PORT"][key]

def get_host_address(key="host_ip") -> str:
    """Gets the Host IP Address from the configuration.

    Args:
        key (str): The key for the Host IP Address in the configuration. Default is "host_ip".

    Returns:
        str: The IP address.
    """
    config = get_config_file()
    if not config["HOST_IP"][key] or "your" in config["HOST_IP"][key]:
        return ""
    return config["HOST_IP"][key]


def get_can_config() -> dict:
    """Gets the CAN interface configuration parameters from the configuration file.

    Returns a dictionary with all CAN interface parameters including bustype, channel,
    baud_rate, id_tx, id_rx, and mode. If values are not properly configured,
    returns default values.

    Returns:
        dict: Dictionary containing CAN configuration parameters:
            - bustype (str): CAN interface type (default: 'pcan_usb')
            - channel (int): CAN channel number (default: 1)
            - baud_rate (int): CAN baud rate in bps (default: 500000)
            - id_tx (int): TX arbitration ID (default: 0x110)
            - id_rx (int): RX arbitration ID (default: 0x100)
            - mode (str): CAN ID mode 'standard' or 'extended' (default: 'standard')

    Example:
        >>> can_config = get_can_config()
        >>> x2c = X2CScope(elf_file="firmware.elf", **can_config)
    """
    config = get_config_file()

    # Default values
    defaults = {
        "bustype": "pcan_usb",
        "channel": 1,
        "baud_rate": 500000,
        "id_tx": 0x110,
        "id_rx": 0x100,
        "mode": "standard"
    }

    # Check if CAN section exists
    if "CAN" not in config:
        return defaults

    can_section = config["CAN"]
    result = {}

    # Get bustype
    bustype = can_section.get("bustype", defaults["bustype"])
    result["bustype"] = bustype if bustype and "your" not in bustype else defaults["bustype"]

    # Get channel (convert to int)
    try:
        result["channel"] = int(can_section.get("channel", defaults["channel"]))
    except (ValueError, TypeError):
        result["channel"] = defaults["channel"]

    # Get baud_rate (convert to int)
    try:
        result["baud_rate"] = int(can_section.get("baud_rate", defaults["baud_rate"]))
    except (ValueError, TypeError):
        result["baud_rate"] = defaults["baud_rate"]

    # Get id_tx (convert hex string to int)
    try:
        id_tx_str = can_section.get("id_tx", hex(defaults["id_tx"]))
        result["id_tx"] = int(id_tx_str, 16) if "0x" in id_tx_str.lower() else int(id_tx_str)
    except (ValueError, TypeError):
        result["id_tx"] = defaults["id_tx"]

    # Get id_rx (convert hex string to int)
    try:
        id_rx_str = can_section.get("id_rx", hex(defaults["id_rx"]))
        result["id_rx"] = int(id_rx_str, 16) if "0x" in id_rx_str.lower() else int(id_rx_str)
    except (ValueError, TypeError):
        result["id_rx"] = defaults["id_rx"]

    # Get mode
    mode = can_section.get("mode", defaults["mode"])
    result["mode"] = mode if mode and mode.lower() in ["standard", "extended", "ext", "29bit"] else defaults["mode"]

    return result
