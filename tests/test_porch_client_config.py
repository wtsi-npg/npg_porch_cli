from pytest import raises

from npg_porch_cli.config import PorchClientConfig, get_config_data


def test_config_file_reading():
    conf = get_config_data(
        conf_file_path="tests/data/conf.ini", conf_file_section="STUFF"
    )

    assert conf == {"logging": "INFO"}


def test_conf_obj():
    config_obj = PorchClientConfig.from_config_file("tests/data/conf.ini")
    assert config_obj.pipeline_name == "test_pipeline"
    assert config_obj.pipeline_version == "9.9.9"

    with raises(KeyError, match="ABSENT"):
        PorchClientConfig.from_config_file(
            "tests/data/conf.ini", conf_file_section="ABSENT"
        )

    with raises(FileNotFoundError, match="No such file or directory: 'notafile'"):
        PorchClientConfig.from_config_file("notafile", conf_file_section="ABSENT")

    with raises(TypeError, match="unexpected keyword argument 'logging'"):
        PorchClientConfig.from_config_file(
            "tests/data/conf.ini", conf_file_section="STUFF"
        )

    with raises(TypeError, match="missing 2 required keyword-only arguments"):
        PorchClientConfig.from_config_file(
            "tests/data/conf.ini", conf_file_section="PARTIALPORCH"
        )
