import configparser
import json
import pathlib
from dataclasses import dataclass

"""Common utility functions for the package."""

DEFAULT_CONF_FILE_TYPE = "ini"


def get_config_data(conf_file_path: str, conf_file_section: str = None):
    """
    Parses a configuration file and returns its content.

    Allows for two types of configuration files, 'ini' and 'json'. The type of
    the file is determined from the extension of the file name. In case of no
    extension an 'ini' type is assumed.

    The content of the file is not cached, so subsequent calls to get data from
    the same configuration file result in re-reading and re-parsing of the file.

    Args:

      conf_file_path:
        A configuration file with database connection details.
      conf_file_section:
        The section of the configuration file. Optional. Should be defined
        for 'ini' files.

    Returns:
      For an 'ini' file returns the content of the given section of the file as
      a dictionary.
      For a 'json' file, if the conf_file_section argument is not defined, the
      content of a file as a Python object is returned. If the conf_file_section
      argument is defined, the object returned by the parser is assumed to be
      a dictionary that has the value of the 'conf_file_section' argument as a key.
      The value corresponding to this key is returned.
    """

    path = pathlib.Path(conf_file_path)

    conf_file_extension = path.suffix
    if conf_file_extension:
        conf_file_extension = conf_file_extension[1:]
    else:
        conf_file_extension = DEFAULT_CONF_FILE_TYPE

    if conf_file_extension == DEFAULT_CONF_FILE_TYPE:
        if not conf_file_section:
            raise Exception(
                "'conf_file_section' argument is not given, "
                "it should be defined for '{DEFAULT_CONF_FILE_TYPE}' "
                "configuration file."
            )

        config = configparser.ConfigParser()
        with open(conf_file_path) as cf:
            if not cf.readable():
                raise Exception(f"{path} has a permissions issue")

            config.read_file(cf)

        return {i[0]: i[1] for i in config[conf_file_section].items()}

    elif conf_file_extension == "json":
        conf: dict = json.load(conf_file_path)
        if conf_file_section:
            if isinstance(conf, dict) is False:
                raise Exception(f"{conf_file_path} does not have sections.")
            if conf_file_section in conf.keys:
                conf = conf[conf_file_section]
            else:
                raise Exception(
                    f"{conf_file_path} does not contain {conf_file_section} key"
                )

        return conf

    else:
        raise Exception(f"Parsing for '{conf_file_extension}' files is not implemented")


@dataclass(frozen=True, kw_only=True)
class PorchClientConfig:
    """
    Suggested config file content for interacting with a Porch server instance
    """

    api_url: str
    pipeline_name: str
    pipeline_uri: str
    pipeline_version: str
    npg_porch_token: str

    @classmethod
    def from_config_file(cls, conf_file_path: str, conf_file_section: str = "PORCH"):
        conf = get_config_data(conf_file_path, conf_file_section=conf_file_section)
        return cls(**conf)
