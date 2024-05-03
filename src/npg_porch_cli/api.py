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

import os
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests

PORCH_CLIENT_ACTIONS = {
    "list_tasks": "tasks",
    "list_pipelines": "pipelines",
    "add_pipeline": "pipelines",
    "add_task": "tasks",
    "claim_task": "tasks/claim",
    "update_task": "tasks",
}

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
class PorchRequest:

    porch_url: str
    validate_ca_cert: bool = field(default=True)
    pipeline_name: str | None = field(default=None)
    pipeline_url: str | None = field(default=None)
    pipeline_version: str | None = field(default=None)

    def send(
        self,
        action: str,
        task_input: dict | None = None,
        task_status: str | None = None,
    ) -> dict:
        """
        Sends a request to the porch API server to perform an action defined
        by the `action` argument. Either of two optional arguments, if defined,
        are used when constructing the request.

        The server's response is returned as a dictionary.
        """

        if task_status is not None:
            task_status = self.validate_status(task_status=task_status)
        self._validate_request(
            action=action, task_input=task_input, task_status=task_status
        )

        method = "GET"
        pipeline_data = {
            "name": self.pipeline_name,
            "uri": self.pipeline_url,
            "version": self.pipeline_version,
        }
        data = None

        if action == "update_task":
            method = "PUT"
            data = {
                "pipeline": pipeline_data,
                "task_input": task_input,
                "status": task_status,
            }
        elif action.startswith("list") is False:
            method = "POST"
            data = pipeline_data
            if action == "add_task":
                data = {"pipeline": pipeline_data, "task_input": task_input}

        request_args = {
            "headers": self._get_request_headers(action),
            "timeout": CLIENT_TIMEOUT,
            "verify": self.validate_ca_cert,
        }
        if data is not None:
            request_args["json"] = data

        response = requests.request(
            method, self._generate_request_url(action), **request_args
        )
        if not response.ok:
            raise ServerErrorException(
                f"Action {action} failed. "
                f'Status code {response.status_code} "{response.reason}" '
                f"received from {response.url}"
            )

        response_obj = response.json()
        if action == "list_tasks" and self.pipeline_name is not None:
            response_obj = [
                o for o in response_obj if o["pipeline"]["name"] == self.pipeline_name
            ]

        return response_obj

    def validate_status(self, task_status: str) -> str:
        """
        Retrieves OpenAPI schema for the porch server and validates the given
        task status value against the values listed in the schema document.

        Returns a validated task status value. The case of this string can be
        different from the input string.
        """
        url = urljoin(self.porch_url, PORCH_OPENAPI_SCHEMA_URL)
        response = requests.request("GET", url)
        if not response.ok:
            raise ServerErrorException(
                f"Failed to get OpenAPI Schema. "
                f'Status code {response.status_code} "{response.reason}" '
                f"received from {response.url}"
            )

        status = task_status.upper()
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
                f"Task status '{task_status}' is not valid. "
                "Valid statuses: " + ", ".join(sorted(valid_statuses))
            )

        return status

    def _generate_request_url(self, action: str):
        return urljoin(self.porch_url, PORCH_CLIENT_ACTIONS[action])

    def _get_token(self):
        if NPG_PORCH_TOKEN_ENV_VAR not in os.environ:
            raise AuthException("Authorization token is needed")
        return os.environ[NPG_PORCH_TOKEN_ENV_VAR]

    def _get_request_headers(self, action: str):
        headers = {"Authorization": "Bearer " + self._get_token()}
        if action.startswith("list") is False:
            headers["Content-Type"] = "application/json"
        return headers

    def _validate_request(
        self, action: str, task_status: str | None, task_input: str | None
    ):

        if action not in PORCH_CLIENT_ACTIONS:
            raise InvalidValueException(
                f"Action '{action}' is not valid. "
                "Valid actions: " + ", ".join(sorted(PORCH_CLIENT_ACTIONS.keys()))
            )

        if action.startswith("list") is False:
            if (
                self.pipeline_name is None
                or self.pipeline_url is None
                or self.pipeline_version is None
            ):
                raise InvalidValueException(
                    f"Full pipeline details should be defined for action '{action}'"
                )

        if (
            action.endswith("task") is True
            and action.startswith("claim") is False
            and task_input is None
        ):
            raise InvalidValueException(
                f"task_input argument should be defined for action '{action}'"
            )

        if action == "update_task":
            if task_status is None:
                raise InvalidValueException(
                    f"task_status argument should be defined for action '{action}'"
                )

        return True
