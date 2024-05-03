# Copyright (c) 2024 Genome Research Ltd.
#
# Authors: Marina Gourtovaia <mg8@sanger.ac.uk>
#          Jennifer Liddle <js10@sanger.ac.uk>
#
# This file is part of npg_porch_cli project.
#
# npg_porch_cli is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import inspect
import json
import os
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin

import requests

PORCH_CLIENT_ACTIONS = [
    "list_tasks",
    "list_pipelines",
    "add_pipeline",
    "add_task",
    "claim_task",
    "update_task",
]
PORCH_OPENAPI_SCHEMA_URL = "api/v1/openapi.json"
PORCH_TASK_STATUS_ENUM_NAME = "TaskStateEnum"

PORCH_STATUSES = ["PENDING", "CLAIMED", "RUNNING", "DONE", "FAILED", "CANCELLED"]

CLIENT_TIMEOUT = (10, 60)

NPG_PORCH_TOKEN_ENV_VAR = "NPG_PORCH_TOKEN"


class AuthException(Exception):
    pass


class InvalidValueException(Exception):
    pass


class ServerErrorException(Exception):
    pass


@dataclass
class Pipeline:
    name: str
    uri: str
    version: str


@dataclass
class PorchAction:

    porch_url: str
    action: str
    validate_ca_cert: bool = field(default=True)
    task_json: str | None = field(default=None, repr=False)
    task_input: dict = field(default=None)
    task_status: str | None = field(default=None)

    def __post_init__(self):
        "Post-constructor hook. Ensures validity of data."

        if self.task_json is not None:
            if self.task_input is not None:
                raise InvalidValueException(
                    "task_json and task_input cannot be both set"
                )
            self.task_input = json.loads(self.task_json)

        self._validate_action_name()
        self.task_status = self._validate_status()

    def _validate_action_name(self):
        if self.action not in PORCH_CLIENT_ACTIONS:
            raise InvalidValueException(
                f"Action '{self.action}' is not valid. "
                "Valid actions: " + ", ".join(sorted(PORCH_CLIENT_ACTIONS))
            )

    def _validate_status(self) -> str | None:
        """
        Retrieves OpenAPI schema for the porch server and validates the given
        task status value against the values listed in the schema document.

        Returns a validated task status value. The case of this string can be
        different from the input string.
        """

        if self.task_status is None:
            return None

        url = urljoin(self.porch_url, PORCH_OPENAPI_SCHEMA_URL)
        response = requests.request("GET", url, verify=self.validate_ca_cert)
        if not response.ok:
            raise ServerErrorException(
                f"Failed to get OpenAPI Schema. "
                f'Status code {response.status_code} "{response.reason}" '
                f"received from {response.url}"
            )

        status = self.task_status.upper()
        valid_statuses = []
        error_message = f"Failed to get enumeration of valid statuses from {url}"
        try:
            valid_statuses = response.json()["components"]["schemas"][
                PORCH_TASK_STATUS_ENUM_NAME
            ]["enum"]
        except Exception as e:
            raise Exception(f"{error_message}: " + e.__str__())

        if len(valid_statuses) == 0:
            raise Exception(error_message)

        if status not in valid_statuses:
            raise InvalidValueException(
                f"Task status '{self.task_status}' is not valid. "
                "Valid statuses: " + ", ".join(sorted(valid_statuses))
            )

        return status


def get_token():
    if NPG_PORCH_TOKEN_ENV_VAR not in os.environ:
        raise AuthException("Authorization token is needed")
    return os.environ[NPG_PORCH_TOKEN_ENV_VAR]


def _send_request(validate_ca_cert: bool, url: str, method: str, data: dict = None):

    headers = {
        "Authorization": "Bearer " + get_token(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    request_args = {
        "headers": headers,
        "timeout": CLIENT_TIMEOUT,
        "verify": validate_ca_cert,
    }
    if data is not None:
        request_args["json"] = data

    response = requests.request(method, url, **request_args)
    if not response.ok:
        action_name = inspect.stack()[1].function
        raise ServerErrorException(
            f"Action {action_name} failed. "
            f'Status code {response.status_code} "{response.reason}" '
            f"received from {response.url}"
        )

    return response.json()


def send(action: PorchAction, pipeline: Pipeline = None) -> dict:
    """
    Sends a request to the porch API server to perform an action defined
    by the `action` attribute of the `action` argument. The context of the
    query is defined by the pipeline argument.

    The server's response is returned as a dictionary.
    """

    functions = {
        "list_tasks": list_tasks,
        "list_pipelines": list_pipelines,
        "add_pipeline": add_pipeline,
        "add_task": add_task,
        "claim_task": claim_task,
        "update_task": update_task,
    }

    # call the function
    return functions[action.action](action=action, pipeline=pipeline)


def list_pipelines(action: PorchAction):
    "Returns a listing of all pipelines registered with the porch server."

    return _send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "pipelines"),
        method="GET",
    )


def list_tasks(action: PorchAction, pipeline: Pipeline = None):
    """
    In the pipeline argument is not defined, returns a listing of all tasks
    registered with the porch server. If the pipeline argument is defined,
    only tasks belonging to this pipeline are listed.
    """

    response_obj = _send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks"),
        method="GET",
    )
    if pipeline is not None:
        pipeline_dict = asdict(pipeline)
        response_obj = [o for o in response_obj if o["pipeline"] == pipeline_dict]
    return response_obj


def add_pipeline(action: PorchAction, pipeline: Pipeline):
    "Registers a new pipeline with the porch server."

    return _send_request(
        validate_ca_cert=action.validate_ca_cert,
        method="POST",
        url=urljoin(action.porch_url, "pipelines"),
        data=asdict(pipeline),
    )


def add_task(action: PorchAction, pipeline: Pipeline):
    "Registers a new task with the porch server."

    if action.task_input is None:
        raise InvalidValueException(
            f"task_input should be defined for action '{action.action}'"
        )
    return _send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks"),
        method="POST",
        data={"pipeline": asdict(pipeline), "task_input": action.task_input},
    )


def claim_task(action: PorchAction, pipeline: Pipeline):
    "Claims a task that belongs to the previously registered pipeline."

    return _send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks/claim"),
        method="POST",
        data=asdict(pipeline),
    )


def update_task(action: PorchAction, pipeline: Pipeline):
    "Updates a status of a task."

    if action.task_input is None:
        raise InvalidValueException(
            f"task_input should be defined for action '{action.action}'"
        )
    if action.task_status is None:
        raise InvalidValueException(
            f"task_status should be defined for action '{action.action}'"
        )
    return _send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks"),
        method="PUT",
        data={
            "pipeline": asdict(pipeline),
            "task_input": action.task_input,
            "status": action.task_status,
        },
    )
