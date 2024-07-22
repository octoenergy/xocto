from __future__ import annotations

import json
import os
import subprocess
from typing import Any

import pact
import requests


class PactConsumerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def post(
        self,
        path: str,
        data: dict[str, Any],
        token: str | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token
        response = requests.post(
            url, data=json.dumps(data), headers=headers, verify=False
        )
        return response.json()


def pact_service(
    broker_url: str,
    broker_username: str,
    broker_password: str,
    consumer_name: str,
    provider_name: str,
    consumer_version: str,
    publish_to_broker: bool,
    log_path: str = "pact_logs",
) -> pact.Pact:
    service = pact.Consumer(
        name=consumer_name, tag_with_git_branch=True, version=consumer_version
    ).has_pact_with(
        pact.Provider(provider_name),
        publish_to_broker=publish_to_broker,
        broker_base_url=broker_url,
        broker_username=broker_username,
        broker_password=broker_password,
        pact_dir=log_path,
        log_dir=log_path,
    )

    return service


def get_unique_version_hash() -> str | None:
    """
    Get a unique version number for the pact verification for the current git revision.

    - Get git hash for the current git revision.

    """
    if "CIRCLECI" not in os.environ:
        return None
    version = _git_revision_hash()
    return version


def _git_revision_hash() -> str:
    """
    Return the git revision hash for the current branch.
    """

    git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"])

    return git_hash.decode("utf8").rstrip()


def get_git_branch_name() -> str | None:
    """
    Get the current git branch name.
    """
    branch_name = _git_branch_name()

    if "fatal: not a git repository" in branch_name:
        return None

    return branch_name


def _git_branch_name() -> str:
    """
    This runs git rev-parse --abbrev-ref HEAD to get the current branch name.
    """
    git_branch = subprocess.check_output(
        [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ]
    )

    return git_branch.decode("utf8").rstrip()
