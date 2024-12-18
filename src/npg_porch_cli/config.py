from dataclasses import dataclass
from os import R_OK, access
from os.path import isfile

from npg.conf import IniData


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


def get_config_data(
    conf_file_path: str, conf_file_section: str = "PORCH"
) -> PorchClientConfig:
    """
    Parses a configuration file and returns its content.

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

    if isfile(conf_file_path) and access(conf_file_path, R_OK):
        porch_conf = IniData(PorchClientConfig).from_file(
            conf_file_path, conf_file_section
        )
    else:
        raise FileNotFoundError(f"{conf_file_path} is not present or cannot be read")

    return porch_conf
