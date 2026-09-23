"""Live membership completion, supported failures and explicit recovery."""

from test_mdns_responder import make_server


def test_mdns_lifecycle_public_contract():
    server = make_server([])
    assert callable(getattr(server, "wait_for_mdns_updates", None))
    assert callable(getattr(server, "retry_mdns", None))
    assert server.mdns_status == "stopped"
    assert server.mdns_error is None
