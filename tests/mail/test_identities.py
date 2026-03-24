"""Tests for mail_list_identities and mail_set_identity in tools/mail/identities.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.identities import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


async def test_list_identities_ok():
    client = mock_client()
    client.call.return_value = [
        (
            "Identity/get",
            {"list": [{"id": "id1", "name": "Alice", "email": "alice@example.com"}]},
            "i",
        )
    ]
    result = await _tool(client, "mail_list_identities")()
    data = json.loads(result)
    assert data == [{"id": "id1", "name": "Alice", "email": "alice@example.com"}]


async def test_list_identities_multiple():
    client = mock_client()
    client.call.return_value = [
        (
            "Identity/get",
            {
                "list": [
                    {"id": "id1", "name": "Alice", "email": "alice@example.com"},
                    {"id": "id2", "name": "Bob", "email": "bob@example.com"},
                ]
            },
            "i",
        )
    ]
    result = await _tool(client, "mail_list_identities")()
    data = json.loads(result)
    assert len(data) == 2
    assert data[1]["email"] == "bob@example.com"


async def test_list_identities_empty():
    client = mock_client()
    client.call.return_value = [("Identity/get", {"list": []}, "i")]
    result = await _tool(client, "mail_list_identities")()
    assert json.loads(result) == []


async def test_list_identities_missing_fields():
    client = mock_client()
    client.call.return_value = [("Identity/get", {"list": [{"id": "id1"}]}, "i")]
    result = await _tool(client, "mail_list_identities")()
    data = json.loads(result)
    assert data == [{"id": "id1", "name": "", "email": ""}]


async def test_list_identities_error():
    client = mock_client()
    client.call.side_effect = requests.RequestException("network error")
    result = await _tool(client, "mail_list_identities")()
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]


# --- mail_set_identity tests ---


async def test_set_identity_create():
    client = mock_client()
    client.set.return_value = {"created": {"new": {"id": "id-new"}}}
    result = await _tool(client, "mail_set_identity")(
        create_email="new@example.com", create_name="New"
    )
    data = json.loads(result)
    assert data == {"created": "id-new"}
    client.set.assert_called_once()
    call_kwargs = client.set.call_args
    assert call_kwargs.kwargs["create"] == {
        "new": {"email": "new@example.com", "name": "New"}
    }


async def test_set_identity_update():
    client = mock_client()
    client.set.return_value = {"updated": {"id1": None}}
    result = await _tool(client, "mail_set_identity")(
        update_id="id1", update_name="Updated Name", update_text_signature="Sig"
    )
    data = json.loads(result)
    assert data == {"updated": "id1"}
    patch = client.set.call_args.kwargs["update"]["id1"]
    assert patch["name"] == "Updated Name"
    assert patch["textSignature"] == "Sig"


async def test_set_identity_destroy():
    client = mock_client()
    client.set.return_value = {"destroyed": ["id1"]}
    result = await _tool(client, "mail_set_identity")(destroy_id="id1")
    data = json.loads(result)
    assert data == {"destroyed": "id1"}
    assert client.set.call_args.kwargs["destroy"] == ["id1"]


async def test_set_identity_no_op():
    client = mock_client()
    result = await _tool(client, "mail_set_identity")()
    data = json.loads(result)
    assert data == {"error": "No operation specified"}
    client.set.assert_not_called()


async def test_set_identity_forbidden_from():
    client = mock_client()
    client.set.return_value = {"notCreated": {"new": {"type": "forbiddenFrom"}}}
    result = await _tool(client, "mail_set_identity")(create_email="bad@example.com")
    data = json.loads(result)
    assert "forbiddenFrom" in data["error"] or "Not permitted" in data["error"]


async def test_set_identity_forbidden_destroy():
    client = mock_client()
    client.set.return_value = {"notDestroyed": {"id1": {"type": "forbidden"}}}
    result = await _tool(client, "mail_set_identity")(destroy_id="id1")
    data = json.loads(result)
    assert "mayDelete" in data["error"] or "cannot be deleted" in data["error"]


async def test_set_identity_error():
    client = mock_client()
    client.set.side_effect = requests.RequestException("timeout")
    result = await _tool(client, "mail_set_identity")(destroy_id="id1")
    data = json.loads(result)
    assert "timeout" in data["error"]
