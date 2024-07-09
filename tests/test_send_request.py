import pytest
import requests

from npg_porch_cli import send_request
from npg_porch_cli.api import AuthException, ServerErrorException

url = "http://some.com"
var_name = "NPG_PORCH_TOKEN"
json_data = {"some_data": "delivered"}


class MockResponseOK:
    def __init__(self):
        self.status_code = 200
        self.reason = "OK"
        self.url = url
        self.ok = True

    def json(self):
        return json_data


class MockResponseNotFound:
    def __init__(self):
        self.status_code = 404
        self.reason = "NOT FOUND"
        self.url = url
        self.ok = False

    def json(self):
        return {"Error": "Not found"}


def mock_get_200(*args, **kwargs):
    return MockResponseOK()


def mock_get_404(*args, **kwargs):
    return MockResponseNotFound()


def test_sending_request(monkeypatch):

    monkeypatch.delenv(var_name, raising=False)

    with pytest.raises(ValueError) as e:
        send_request(validate_ca_cert=True, url=url, method="GET", auth_type="unknown")
    assert e.value.args[0] == "Authorization type unknown is not implemented"

    with pytest.raises(AuthException) as e:
        send_request(validate_ca_cert=True, url=url, method="GET")
    assert e.value.args[0] == "Authorization token is needed"

    with monkeypatch.context() as m:
        m.setattr(requests, "request", mock_get_200)
        assert (
            send_request(validate_ca_cert=True, url=url, method="GET", auth_type=None)
            == json_data
        )

    monkeypatch.setenv(var_name, "token_xyz")

    with monkeypatch.context() as m:
        m.setattr(requests, "request", mock_get_200)
        assert send_request(validate_ca_cert=False, url=url, method="GET") == json_data

    with monkeypatch.context() as m:
        m.setattr(requests, "request", mock_get_404)
        with pytest.raises(ServerErrorException) as e:
            send_request(validate_ca_cert=False, url=url, method="POST", data=json_data)
        assert e.value.args[0] == f'Status code 404 "NOT FOUND" received from {url}'

    monkeypatch.undo()
