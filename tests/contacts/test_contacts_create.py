"""Tests for contacts_create_contact in tools/contacts/contacts_write.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.contacts.contacts_write import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


async def test_create_contact_minimal():
    client = mock_client()
    client.set.return_value = {
        "created": {"new": {"id": "c1", "name": {"full": "Alice"}}}
    }
    result = await _tool(client, "contacts_create_contact")(name="Alice")
    data = json.loads(result)
    assert data["id"] == "c1"
    # verify card structure passed to set
    _, kwargs = client.set.call_args
    card = kwargs["create"]["new"]
    assert card["name"] == {"full": "Alice"}
    assert card["@type"] == "Card"


async def test_create_contact_full_fields():
    client = mock_client()
    client.set.return_value = {"created": {"new": {"id": "c2"}}}
    await _tool(client, "contacts_create_contact")(
        name="Bob",
        emails=["bob@example.com"],
        phones=["+1234"],
        org="Acme",
        notes="VIP",
        address_book_ids=["ab1"],
    )
    _, kwargs = client.set.call_args
    card = kwargs["create"]["new"]
    assert card["emails"] == {"e0": {"address": "bob@example.com"}}
    assert card["phones"] == {"p0": {"number": "+1234"}}
    assert card["organizations"] == {"o0": {"name": "Acme"}}
    assert card["notes"] == {"n0": {"note": "VIP"}}
    assert card["addressBookIds"] == {"ab1": True}


async def test_create_contact_not_created_error():
    client = mock_client()
    client.set.return_value = {
        "notCreated": {"new": {"type": "invalidProperties", "description": "bad data"}}
    }
    result = await _tool(client, "contacts_create_contact")(name="X")
    data = json.loads(result)
    assert data == {"error": "bad data"}


async def test_create_contact_no_response():
    client = mock_client()
    client.set.return_value = {}
    result = await _tool(client, "contacts_create_contact")(name="X")
    data = json.loads(result)
    assert data == {"error": "No response from server"}


async def test_create_contact_fastmail_error():
    client = mock_client()
    client.set.side_effect = FastmailError("auth failed")
    result = await _tool(client, "contacts_create_contact")(name="X")
    data = json.loads(result)
    assert "auth failed" in data["error"]


async def test_create_contact_request_exception():
    client = mock_client()
    client.set.side_effect = requests.RequestException("network error")
    result = await _tool(client, "contacts_create_contact")(name="X")
    data = json.loads(result)
    assert "network error" in data["error"]
