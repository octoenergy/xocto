from xocto import pact_testing


def test_pact_service():
    pact_service = pact_testing.pact_service(
        broker_url="https://pact-broker.example.com",
        broker_username="username",
        broker_password="password",
        consumer_name="consumer_name",
        consumer_version="1.0.0",
        provider_name="provider_name",
        publish_to_broker=True,
    )
    assert pact_service.broker_base_url == "https://pact-broker.example.com"
    assert pact_service.broker_username == "username"
    assert pact_service.broker_password == "password"
    assert pact_service.provider.name == "provider_name"
    assert pact_service.consumer.name == "consumer_name"
    assert pact_service.consumer.version == "1.0.0"
    assert pact_service.publish_to_broker is True
