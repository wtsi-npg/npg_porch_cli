#!/usr/bin/env python3

# Copyright (C) 2022, 2024 Genome Research Ltd.
#
# Author: Jennifer Liddle <js10@sanger.ac.uk>
#
# npg_porch_client is free software: you can redistribute it and/or modify it
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

import requests

# Certification file for https requests
# if we don't have one, we can set certfile = False
certfile = "/usr/share/ca-certificates/sanger.ac.uk/Genome_Research_Ltd_Certificate_Authority-cert.pem"  # noqa: E501

# tokens from Porch
admin_headers = {"Authorization": "Bearer a"}
pipeline_headers = {"Authorization": "Bearer b"}

# Command line arguments
parser = argparse.ArgumentParser(description="Pipeline Orchestration Wrapper")
parser.add_argument("--baseurl", type=str, help="base URL")
parser.add_argument("--pipeline_url", type=str, help="Pipeline git project URL")
parser.add_argument("--pipeline_version", type=str, help="Pipeline version")
parser.add_argument("--pipeline", type=str, help="pipeline name")
parser.add_argument("--idrun", type=int, help="id_run")
parser.add_argument("--sample", type=str, help="sample name")
parser.add_argument("--study", type=str, help="study ID")
parser.add_argument(
    "--status",
    type=str,
    help="new status to set",
    default="DONE",
    choices=["PENDING", "CLAIMED", "RUNNING", "DONE", "FAILED", "CANCELLED"],
)
parser.add_argument(
    "command",
    type=str,
    help="command to send to npg_porch",
    choices=["list", "plist", "register", "add", "claim", "update"],
)
args = parser.parse_args()

if args.command == "list":
    response = requests.get(
        args.baseurl + "/tasks", verify=certfile, headers=pipeline_headers
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    x = response.json()
    for p in x:
        if p["pipeline"]["name"] == args.pipeline:
            print(f"{p['task_input']}\t{p['status']}")

if args.command == "plist":
    response = requests.get(
        args.baseurl + "/pipelines", verify=certfile, headers=admin_headers
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    x = response.json()
    pipelines = {}
    for p in x:
        pname = p["name"]
        if pname not in pipelines:
            print(pname)
            pipelines[pname] = 1

if args.command == "register":
    data = {
        "name": args.pipeline,
        "uri": args.pipeline_url,
        "version": args.pipeline_version,
    }
    response = requests.post(
        args.baseurl + "/pipelines", json=data, verify=certfile, headers=admin_headers
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    print(response.json())

if args.command == "add":
    data = {
        "pipeline": {
            "name": args.pipeline,
            "uri": args.pipeline_url,
            "version": args.pipeline_version,
        },
        "task_input": {
            "id_run": args.idrun,
            "sample": args.sample,
            "id_study": args.study,
        },
    }
    response = requests.post(
        args.baseurl + "/tasks", json=data, verify=certfile, headers=pipeline_headers
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    print(response.json())

if args.command == "claim":
    data = {
        "name": args.pipeline,
        "uri": args.pipeline_url,
        "version": args.pipeline_version,
    }
    response = requests.post(
        args.baseurl + "/tasks/claim",
        json=data,
        verify=certfile,
        headers=pipeline_headers,
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    print(response.json())

if args.command == "update":
    data = {
        "pipeline": {
            "name": args.pipeline,
            "uri": args.pipeline_url,
            "version": args.pipeline_version,
        },
        "task_input": {
            "id_run": args.idrun,
            "sample": args.sample,
            "id_study": args.study,
        },
        "status": args.status,
    }
    response = requests.put(
        args.baseurl + "/tasks", json=data, verify=certfile, headers=pipeline_headers
    )
    if not response.ok:
        print(f'"{response.reason}" received from {response.url}')
        exit(1)

    print(data)
    print(response.json())
