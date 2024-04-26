import pytest

from npg_porch_cli.api import AuthException, InvalidValueException, PorchRequest

url = "http://some.com"


def test_validation():

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
        r._validate_request(action="list_tasks", task_status="Some", task_input=None)
    assert (
        e.value.args[0] == "Task status 'Some' is not valid. "
        "Valid statuses: PENDING, CLAIMED, RUNNING, DONE, FAILED, CANCELLED"
    )
    with pytest.raises(InvalidValueException) as e:
        r._validate_request(action="list_tasks", task_status="Running", task_input=None)
    assert (
        e.value.args[0] == "Task status 'Running' is not valid. "
        "Valid statuses: PENDING, CLAIMED, RUNNING, DONE, FAILED, CANCELLED"
    )


def test_url_generation():

    r = PorchRequest(porch_url=url)
    assert r._generate_request_url(action="list_tasks") == "/".join([url, "tasks"])


def test_header_generation(monkeypatch):

    var_name = "NPG_PORCH_TOKEN"
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
