from __future__ import annotations

import pytest

from xocto import pact_testing


def test_pact_service():
    options = pact_testing.PactOptions(
        broker_url="https://pact-broker.example.com",
        broker_username="username",
        broker_password="password",
        consumer_name="consumer_name",
        consumer_version="1.0.0",
        provider_name="provider_name",
        log_path="/tmp/pact/",
    )
    pact_service = pact_testing.pact_service(
        options=options,
        publish_to_broker=True,
    )
    assert pact_service.broker_base_url == "https://pact-broker.example.com"
    assert pact_service.broker_username == "username"
    assert pact_service.broker_password == "password"
    assert pact_service.provider.name == "provider_name"
    assert pact_service.consumer.name == "consumer_name"
    assert pact_service.consumer.version == "1.0.0"
    assert pact_service.publish_to_broker is True
    assert pact_service.pact_dir == "/tmp/pact/"
    assert pact_service.log_dir == "/tmp/pact/"


@pytest.mark.parametrize("branch", ["main", None])
def test_publish_pacts(mocker, branch):
    mock_publish = mocker.patch("pact.v2.broker.Broker.publish")

    pact_testing.publish_pacts(
        consumer_name="my-consumer",
        pact_dir="/tmp/pacts",
        consumer_version="abc123",
        broker_url="https://broker.example.com",
        broker_username="user",
        broker_password="pass",
        branch=branch,
    )

    mock_publish.assert_called_once_with(
        consumer_name="my-consumer",
        version="abc123",
        pact_dir="/tmp/pacts",
        branch=branch,
    )
