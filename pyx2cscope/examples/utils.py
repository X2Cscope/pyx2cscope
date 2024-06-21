"""This module provides utility functions for handling configuration settings.

Functions:
    get_config_file() -> ConfigParser: Retrieves the configuration file.
    get_elf_file_path(key="path") -> str: Gets the path to the ELF file from the configuration.
    get_com_port(key="com_port") -> str: Gets the COM port from the configuration.
"""

import os
from configparser import ConfigParser


def get_config_file() -> ConfigParser:
    """Retrieves the configuration file. If the configuration file does not exist, it creates one with default values.

    Returns:
        ConfigParser: The configuration parser object.
    """
    config_file = "config.ini"
    default_path = {"path": "'path_to_your_elf_file'"}
    default_com = {"com_port": "your_com_port, ex:'COM3'"}
    config = ConfigParser()
    if os.path.exists(config_file):
        config.read(config_file)
    else:
        # Create the config file with the default value
        config["ELF_FILE"] = default_path
        config["COM_PORT"] = default_com
        with open(config_file, "w") as configfile:
            config.write(configfile)
        print(f"Config file '{config_file}' created with default values")
    return config


def get_elf_file_path(key="path") -> str:
    """Gets the path to the ELF file from the configuration.

    Args:
        key (str): The key for the ELF file path in the configuration. Default is "path".

    Returns:
        str: The path to the ELF file.
    """
    config = get_config_file()
    return config["ELF_FILE"][key]


def get_com_port(key="com_port") -> str:
    """Gets the COM port from the configuration.

    Args:
        key (str): The key for the COM port in the configuration. Default is "com_port".

    Returns:
        str: The COM port.
    """
    config = get_config_file()
    return config["COM_PORT"][key]
