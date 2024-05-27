from configparser import ConfigParser
import os

def get_config_file() -> ConfigParser:
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
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        print(f"Config file '{config_file}' created with default values")
    return config

def get_elf_file_path(key="path") -> str:
    config = get_config_file()
    return config["ELF_FILE"][key]

def get_com_port(key="com_port") -> str:
    config = get_config_file()
    return config["COM_PORT"][key]
