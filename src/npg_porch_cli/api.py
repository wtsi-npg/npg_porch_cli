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

import json
import os
from dataclasses import InitVar, asdict, dataclass, field
from urllib.parse import urljoin

import requests

PORCH_OPENAPI_SCHEMA_URL = "api/v1/openapi.json"
PORCH_TASK_STATUS_ENUM_NAME = "TaskStateEnum"

PORCH_STATUSES = ["PENDING", "CLAIMED", "RUNNING", "DONE", "FAILED", "CANCELLED"]

CLIENT_TIMEOUT = (10, 60)

NPG_PORCH_TOKEN_ENV_VAR = "NPG_PORCH_TOKEN"


class AuthException(Exception):
    pass


class ServerErrorException(Exception):
    pass


@dataclass(kw_only=True)
class Pipeline:
    name: str
    uri: str
    version: str

    def __post_init__(self):
        "Post-constructor hook. Ensures all fields are defined."
        if not (self.name and self.uri and self.version):
            raise TypeError("Pipeline name, uri and version should be defined")


@dataclass(kw_only=True)
class PorchAction:
    porch_url: str
    action: str
    validate_ca_cert: bool = field(default=True)
    task_json: InitVar[str | None] = field(default=None, repr=False)
    task_input: dict = field(default=None)
    task_status: str | None = field(default=None)

    def __post_init__(self, task_json):
        "Post-constructor hook. Ensures integrity and validity of attributes."

        if self.porch_url is None:
            raise TypeError("'porch_url' attribute cannot be None")

        if task_json is not None:
            if self.task_input is not None:
                raise ValueError("task_json and task_input cannot be both set")
            self.task_input = json.loads(task_json)

        self._validate_action_name()
        self.task_status = self._validate_status()

    def _validate_action_name(self):
        if self.action is None:
            raise TypeError("'action' attribute cannot be None")
        if self.action not in _PORCH_CLIENT_ACTIONS:
            raise ValueError(
                f"Action '{self.action}' is not valid. "
                "Valid actions: " + ", ".join(list_client_actions())
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
            raise ValueError(
                f"Task status '{self.task_status}' is not valid. "
                "Valid statuses: " + ", ".join(sorted(valid_statuses))
            )

        return status


def get_token():
    if NPG_PORCH_TOKEN_ENV_VAR not in os.environ:
        raise AuthException("Authorization token is needed")
    return os.environ[NPG_PORCH_TOKEN_ENV_VAR]


def list_client_actions() -> list:
    """Returns a sorted list of currently implemented client actions."""

    return sorted(_PORCH_CLIENT_ACTIONS.keys())


def send(action: PorchAction, pipeline: Pipeline = None) -> dict | list:
    """
    Sends a request to the porch API server to perform an action defined
    by the `action` attribute of the `action` argument. The context of the
    query is defined by the pipeline argument.

    The server's response is returned as a dictionary or as a list.
    """

    # Get function's definition and then call the function.
    function = _PORCH_CLIENT_ACTIONS[action.action]
    if action.action == "list_pipelines":
        return function(action=action)
    return function(action=action, pipeline=pipeline)


def list_pipelines(action: PorchAction) -> list:
    "Returns a listing of all pipelines registered with the porch server."

    return send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "pipelines"),
        method="GET",
    )


def list_tasks(action: PorchAction, pipeline: Pipeline = None) -> list:
    """
    In the pipeline argument is not defined, returns a listing of all tasks
    registered with the porch server. If the pipeline argument is defined,
    only tasks belonging to this pipeline are listed.
    """

    response_obj = send_request(
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

    return send_request(
        validate_ca_cert=action.validate_ca_cert,
        method="POST",
        url=urljoin(action.porch_url, "pipelines"),
        data=asdict(pipeline),
    )


def add_task(action: PorchAction, pipeline: Pipeline):
    "Registers a new task with the porch server."

    if action.task_input is None:
        raise TypeError(f"task_input cannot be None for action '{action.action}'")
    return send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks"),
        method="POST",
        data={"pipeline": asdict(pipeline), "task_input": action.task_input},
    )


def claim_task(action: PorchAction, pipeline: Pipeline):
    "Claims a task that belongs to the previously registered pipeline."

    return send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks/claim"),
        method="POST",
        data=asdict(pipeline),
    )


def update_task(action: PorchAction, pipeline: Pipeline):
    "Updates a status of a task."

    if action.task_input is None:
        raise TypeError(f"task_input cannot be None for action '{action.action}'")
    if action.task_status is None:
        raise TypeError(f"task_status cannot be None for action '{action.action}'")
    return send_request(
        validate_ca_cert=action.validate_ca_cert,
        url=urljoin(action.porch_url, "tasks"),
        method="PUT",
        data={
            "pipeline": asdict(pipeline),
            "task_input": action.task_input,
            "status": action.task_status,
        },
    )


_PORCH_CLIENT_ACTIONS = {
    "list_tasks": list_tasks,
    "list_pipelines": list_pipelines,
    "add_pipeline": add_pipeline,
    "add_task": add_task,
    "claim_task": claim_task,
    "update_task": update_task,
}


def send_request(
    validate_ca_cert: bool,
    url: str,
    method: str,
    data: dict | None = None,
    auth_type: str | None = "token",
):
    """Sends an HTTP request to a JSON API web service.

    Raises ServerErrorException if the status code of the response is not
    in the 200 – 299 range.

    Args:
      validate_ca_cert:
        A boolean flag defining whether the server CA certificate
        will be validated. If set to True, SSL_CERT_FILE environment
        variable should be set.
      url:
        A URL to send the request to.
      method:
        The HTTP method to use (GET, POST, etc.)
      data:
        Optional payload for the request as a Python object.
      auth_type:
        Authorization type, defaults to 'token'. If no authorization
        is required, set the value explicitly to None. Only the token
        type authorization is implemented at the moment. For this type
        of authorization to work, set NPG_PORCH_TOKEN environment
        variable.

    Example:

      from npg_porch_cli import send_request

      url = "https://some.com/api/fruit_types"
      fruit_types = send_request(validate_ca_cert=True, url=url, method="GET", auth_type=None)

      url = "https://some.com/api/add_fruit_type"
      new_type = send_request(
          validate_ca_cert=True,
          url=url,
          method="PUT",
          data={"banana": {"taste": "sweet"}},
      )

    Returns:
      Server's decoded reply.
    """

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if auth_type is not None:
        if auth_type == "token":
            headers["Authorization"] = "Bearer " + get_token()
        else:
            raise ValueError(f"Authorization type {auth_type} is not implemented")

    request_args = {
        "headers": headers,
        "timeout": CLIENT_TIMEOUT,
        "verify": validate_ca_cert,
    }
    if data is not None:
        request_args["json"] = data

    response = requests.request(method, url, **request_args)
    if not response.ok:
        raise ServerErrorException(
            f'Status code {response.status_code} "{response.reason}" '
            f"received from {response.url}"
        )

    return response.json()
