#!/usr/bin/env python3

# Copyright (C) 2022, 2024 Genome Research Ltd.
#
# Author: Jennifer Liddle <js10@sanger.ac.uk>
#
# This file is part of npg_porch_cli project.
#
# npg_porch_cli is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import argparse
import json

from npg_porch_cli.api import PorchRequest


def run():
    """
    Parses command line arguments, send the request to porch server API,
    prints out the server's response to STDOUT.

    The text below assumes that this code is deployed as a script called
    `npg_porch_client`.

    One positional argument, the name of the action to be performed, is required.
    One named argument `--base_url`, teh URL of the `porch` server, is also
    required.

      npg_porch_client list_pipeline --base_url SOME_URL

    A full list of actions:
        list_tasks
        list_pipelines
        add_pipeline
        add_task
        claim_task
        update_task

    Though most of named arguments are optional, some actions require
    certain combinations of arguments to be defined.

    All list actions do not require any optional arguments defined. If
    `--pipeline_name` is defined, `list_tasks` returns a list of tasks for
    this pipeline, otherwise all registered tasks are returned.

    All non-list actions require all `--pipeline`, `pipeline_url` and
    `--pipeline_version` defined.

    The `add_task` and `update_task` actions require the `--task_json` to
    be defined. In addition to this, for the `update_task` action `--status`
    should be defined.

    NPG_PORCH_TOKEN environment variable should be set to the value of
    either an admin or project-specific token.

    """
    parser = argparse.ArgumentParser(
        prog="npg_porch_client",
        description="npg_porch (Pipeline Orchestration)API Client",
        epilog="The server JSON reply is printed to STDOUT",
    )

    parser.add_argument(
        "action",
        type=str,
        help="Action to send to npg_porch server API",
        choices=[
            "list_tasks",
            "list_pipelines",
            "add_pipeline",
            "add_task",
            "claim_task",
            "update_task",
        ],
    )
    parser.add_argument("--base_url", type=str, required=True, help="Base URL")
    parser.add_argument(
        "--validate_ca_cert",
        action=argparse.BooleanOptionalAction,
        type=bool,
        help="A flag instructing to validate server's CA SSL certificate, true by default",
        default=True,
    )
    parser.add_argument(
        "--pipeline_url", type=str, help="Pipeline git project URL, optional"
    )
    parser.add_argument(
        "--pipeline_version", type=str, help="Pipeline version, optional"
    )
    parser.add_argument("--pipeline", type=str, help="Pipeline name, optional")
    parser.add_argument("--task_json", type=str, help="Task as JSON, optional")
    parser.add_argument("--status", type=str, help="New status to set, optional")

    args = parser.parse_args()

    r = PorchRequest(
        porch_url=args.base_url,
        validate_ca_cert=args.validate_ca_cert,
        pipeline_name=args.pipeline,
        pipeline_url=args.pipeline_url,
        pipeline_version=args.pipeline_version,
    )

    parsed_json = None
    if args.task_json is not None:
        print(args.task_json)
        parsed_json = json.loads(args.task_json)
    response = r.send(
        action=args.action, task_input=parsed_json, task_status=args.status
    )
    print(response)
