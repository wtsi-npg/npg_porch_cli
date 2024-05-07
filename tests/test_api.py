import json

import pytest
import requests

from npg_porch_cli.api import (
    AuthException,
    InvalidValueException,
    Pipeline,
    PorchAction,
    ServerErrorException,
    get_token,
    list_client_actions,
    send,
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


def test_retrieving_token(monkeypatch):

    monkeypatch.delenv(var_name, raising=False)
    with pytest.raises(AuthException) as e:
        get_token()
    assert e.value.args[0] == "Authorization token is needed"

    monkeypatch.setenv(var_name, "token_xyz")
    assert get_token() == "token_xyz"

    monkeypatch.undo()


def test_listing_actions():
    assert list_client_actions() == [
        "add_pipeline",
        "add_task",
        "claim_task",
        "list_pipelines",
        "list_tasks",
        "update_task",
    ]


def test_pipeline_class():

    with pytest.raises(InvalidValueException) as e:
        Pipeline(name=None, uri="http://some.come", version="1.0")
    assert e.value.args[0] == "Pipeline name, uri and version should be defined"


def test_porch_action_class(monkeypatch):

    with pytest.raises(InvalidValueException) as e:
        PorchAction(porch_url=None, action="list_tasks")
    assert e.value.args[0] == "'porch_url' attribute should be defined"

    with pytest.raises(InvalidValueException) as e:
        PorchAction(porch_url="http://some.come", action=None)
    assert e.value.args[0] == "'action' attribute should be defined"

    with pytest.raises(InvalidValueException) as e:
        PorchAction(porch_url=url, action="list_tools")
    assert (
        e.value.args[0] == "Action 'list_tools' is not valid. "
        "Valid actions: add_pipeline, add_task, claim_task, list_pipelines, "
        "list_tasks, update_task"
    )

    pa = PorchAction(porch_url=url, action="list_tasks")
    assert pa.validate_ca_cert is True
    assert pa.task_input is None
    assert pa.task_status is None

    with pytest.raises(InvalidValueException) as e:
        pa = PorchAction(
            porch_url=url,
            action="add_task",
            task_json='{"id_run": 5}',
            task_input={"id_run": 5},
        )
        assert e.value.args[0] == "task_json and task_input cannot be both set"
    pa = PorchAction(
        validate_ca_cert=False,
        porch_url=url,
        action="add_task",
        task_json='{"id_run": 5}',
    )
    assert pa.task_input == {"id_run": 5}
    assert pa.validate_ca_cert is False
    pa = PorchAction(porch_url=url, action="add_task", task_input={"id_run": 5})
    assert pa.task_input == {"id_run": 5}

    with monkeypatch.context() as m:

        def mock_get_200(*args, **kwargs):
            f = open("tests/data/porch_openapi.json")
            r = MockPorchResponse(json.load(f), 200)
            f.close()
            return r

        m.setattr(requests, "request", mock_get_200)
        pa = PorchAction(
            task_status="FAILED",
            action="update_task",
            task_input='{"id_run": 5}',
            porch_url=url,
        )
        assert pa.task_status == "FAILED"
        pa = PorchAction(
            task_status="FAILED",
            action="update_task",
            task_input='{"id_run": 5}',
            porch_url=url,
        )
        assert pa.task_status == "FAILED"
        with pytest.raises(InvalidValueException) as e:
            PorchAction(
                task_status="Swimming",
                action="update_task",
                task_input='{"id_run": 5}',
                porch_url=url,
            )
        assert (
            e.value.args[0] == "Task status 'Swimming' is not valid. "
            "Valid statuses: CANCELLED, CLAIMED, DONE, FAILED, PENDING, RUNNING"
        )

    with monkeypatch.context() as mk:

        def mock_get_404(*args, **kwargs):
            return MockPorchResponse({"Error": "Not found"}, 404)

        mk.setattr(requests, "request", mock_get_404)
        with pytest.raises(ServerErrorException) as e:
            PorchAction(
                task_status="FAILED",
                action="update_task",
                task_input='{"id_run": 5}',
                porch_url=url,
            )
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
        with pytest.raises(Exception) as e:
            PorchAction(
                task_status="FAILED",
                action="update_task",
                task_input='{"id_run": 5}',
                porch_url=url,
            )
        assert e.value.args[0].startswith(
            f"Failed to get enumeration of valid statuses from {url}"
        )


def test_request_validation():

    p = Pipeline(uri=url, version="1.0", name="p1")

    pa = PorchAction(porch_url=url, action="add_task")
    with pytest.raises(InvalidValueException) as e:
        send(action=pa, pipeline=p)
    assert e.value.args[0] == "task_input should be defined for action 'add_task'"

    pa = PorchAction(porch_url=url, action="update_task")
    with pytest.raises(InvalidValueException) as e:
        send(action=pa, pipeline=p)
    assert e.value.args[0] == "task_input should be defined for action 'update_task'"
    pa = PorchAction(porch_url=url, action="update_task", task_input={"id_run": 5})
    with pytest.raises(InvalidValueException) as e:
        send(action=pa, pipeline=p)
    assert e.value.args[0] == "task_status should be defined for action 'update_task'"


def test_sending_request(monkeypatch):

    monkeypatch.delenv(var_name, raising=False)
    monkeypatch.setenv(var_name, "MY_TOKEN")

    def all_valid(*args, **kwargs):
        return "PENDING"

    monkeypatch.setattr(PorchAction, "_validate_status", all_valid)

    p = Pipeline(uri=url, version="0.1", name="p1")
    task = {"id_run": 5}
    response_data = {
        "pipeline": p,
        "task_input_id": "8d505b17b4f",
        "task_input": task,
        "status": "PENDING",
    }

    with monkeypatch.context() as m:

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        m.setattr(requests, "request", mock_get_200)

        pa = PorchAction(porch_url=url, action="add_task", task_input=task)
        assert send(action=pa, pipeline=p) == response_data

    with monkeypatch.context() as mk:
        response_data["status"] = "CLAIMED"

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        mk.setattr(requests, "request", mock_get_200)

        pa = PorchAction(porch_url=url, action="claim_task")
        assert send(action=pa, pipeline=p) == response_data

    with monkeypatch.context() as mkp:
        response_data["status"] = "DONE"

        def mock_get_200(*args, **kwargs):
            return MockPorchResponse(response_data, 200)

        mkp.setattr(requests, "request", mock_get_200)

        pa = PorchAction(
            porch_url=url, action="update_task", task_input=task, task_status="DONE"
        )
        assert send(action=pa, pipeline=p) == response_data
