from pytest import raises

from npg_porch_cli.config import PorchClientConfig, get_config_data


def test_conf_obj():
    config_obj = get_config_data("tests/data/conf.ini")
    assert config_obj.pipeline_name == "test_pipeline"
    assert config_obj.pipeline_version == "9.9.9"

    assert type(config_obj) is PorchClientConfig

    with raises(FileNotFoundError, match="notafile is not present or cannot be read"):
        get_config_data("notafile", conf_file_section="ABSENT")

    with raises(TypeError, match="missing 2 required keyword-only arguments"):
        get_config_data("tests/data/conf.ini", conf_file_section="PARTIALPORCH")
