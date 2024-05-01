import json

import pytest
import requests

from npg_porch_cli.api import (
    AuthException,
    InvalidValueException,
    PorchRequest,
    ServerErrorException,
)

url = "http://some.com"
var_name = "NPG_PORCH_TOKEN"


class MockPorchResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.reason = "Some reason"
        self.url = url
        self.ok = True if self.status_code == 200 else False

    def json(self):
        return self.json_data


def test_request_validation():

    r = PorchRequest(porch_url=url)

    with pytest.raises(InvalidValueException) as e:
        r._validate_request(action="list_tools", task_status=None, task_input=None)
    assert (
        e.value.args[0] == "Action 'list_tools' is not valid. "
        "Valid actions: add_pipeline, add_task, claim_task, list_pipelines, "
        "list_tasks, update_task"
    )
    assert (
        r._validate_request(action="list_tasks", task_status=None, task_input=None)
        is True
    )

    with pytest.raises(InvalidValueException) as e:
        r._validate_request(action="claim_task", task_status=None, task_input=None)
    assert (
        e.value.args[0]
        == "Full pipeline details should be defined for action 'claim_task'"
    )
    r = PorchRequest(
        porch_url=url,
        pipeline_name="p1",
        pipeline_version="0.1",
        pipeline_url="https//:p1.com",
    )
    assert (
        r._validate_request(action="claim_task", task_status=None, task_input=None)
        is True
    )

    with pytest.raises(InvalidValueException) as e:
        r._validate_request(action="add_task", task_status=None, task_input=None)
    assert (
        e.value.args[0] == "task_input argument should be defined for action 'add_task'"
    )
    assert (
        r._validate_request(
            action="add_task", task_status=None, task_input={"id_run": 5}
        )
        is True
    )

    with pytest.raises(InvalidValueException) as e:
        r._validate_request(
            action="update_task", task_status=None, task_input={"id_run": 5}
        )
    assert (
        e.value.args[0]
        == "task_status argument should be defined for action 'update_task'"
    )
    assert (
        r._validate_request(
            action="update_task", task_status="PENDING", task_input={"id_run": 5}
        )
        is True
    )


def test_url_generation():

    r = PorchRequest(porch_url=url)
    assert r._generate_request_url(action="list_tasks") == "/".join([url, "tasks"])


def test_header_generation(monkeypatch):

    r = PorchRequest(porch_url=url)

    monkeypatch.delenv(var_name, raising=False)
    with pytest.raises(AuthException) as e:
        r._get_request_headers(action="list_tasks")
    assert e.value.args[0] == "Authorization token is needed"

    monkeypatch.setenv(var_name, "token_xyz")
    assert r._get_request_headers(action="list_tasks") == {
        "Authorization": "Bearer token_xyz"
    }
    assert r._get_request_headers(action="add_tasks") == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token_xyz",
    }
    monkeypatch.undo()


def test_status_validation(monkeypatch):

    with monkeypatch.context() as m:

        def mock_get_200(*args, **kwargs):
            f = open("tests/data/porch_openapi.json")
            r = MockPorchResponse(json.load(f), 200)
            f.close()
            return r

        m.setattr(requests, "request", mock_get_200)
        r = PorchRequest(porch_url=url)
        assert r.validate_status("FAILED") == "FAILED"
        assert r.validate_status("Failed") == "FAILED"
        with pytest.raises(InvalidValueException) as e:
            r.validate_status("Swimming")
        assert (
            e.value.args[0] == "Task status 'Swimming' is not valid. "
            "Valid statuses: CANCELLED, CLAIMED, DONE, FAILED, PENDING, RUNNING"
        )

    with monkeypatch.context() as mk:

        def mock_get_404(*args, **kwargs):
            return MockPorchResponse({"Error": "Not found"}, 404)

        mk.setattr(requests, "request", mock_get_404)
        r = PorchRequest(porch_url=url)
        with pytest.raises(ServerErrorException) as e:
            r.validate_status("FAILED")
        assert (
            e.value.args[0] == "Failed to get OpenAPI Schema. Status code 404 "
            '"Some reason" received from http://some.com'
        )

    with monkeypatch.context() as mkp:

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(
                {"openapi": "3.1.0", "info": {"title": "Pipeline", "version": "0.1.0"}},
                200,
            )

        mkp.setattr(requests, "request", mock_get_200)
        r = PorchRequest(porch_url=url)
        with pytest.raises(Exception) as e:
            r.validate_status("FAILED")
        assert e.value.args[0].startswith(
            f"Failed to get enumeration of valid statuses from {url}"
        )


def test_sending_request(monkeypatch):
    class MockPorchRequest(PorchRequest):
        # Mock status validation.
        def validate_status(self, task_status: str):
            return task_status

    r = MockPorchRequest(
        porch_url=url,
        pipeline_name="p1",
        pipeline_version="0.1",
        pipeline_url="https//:p1.com",
    )

    task = {
        "id_run": 40954,
    }
    response_data = {
        "pipeline": {
            "name": "p1",
            "uri": "https//:p1.com",
            "version": "0.1",
        },
        "task_input_id": "8d505b17b4f",
        "task_input": task,
        "status": "PENDING",
    }

    monkeypatch.delenv(var_name, raising=False)
    monkeypatch.setenv(var_name, "MY_TOKEN")

    with monkeypatch.context() as m:

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        m.setattr(requests, "request", mock_get_200)
        assert r.send(action="add_task", task_input=task) == response_data

    with monkeypatch.context() as mk:
        response_data["status"] = "CLAIMED"

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        mk.setattr(requests, "request", mock_get_200)
        assert r.send(action="claim_task") == response_data

    with monkeypatch.context() as mkp:
        response_data["status"] = "DONE"

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        mkp.setattr(requests, "request", mock_get_200)
        assert (
            r.send(action="update_task", task_input=task, task_status="DONE")
            == response_data
        )
