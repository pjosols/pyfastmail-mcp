"""Tests for contacts_update_contact in tools/contacts/contacts_write.py."""

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


async def test_update_contact_name():
    client = mock_client()
    client.set.return_value = {"updated": {"c1": None}}
    result = await _tool(client, "contacts_update_contact")(
        contact_id="c1", name="Alice"
    )
    data = json.loads(result)
    assert data == {"updated": "c1"}
    _, kwargs = client.set.call_args
    assert kwargs["update"] == {"c1": {"name/full": "Alice"}}


async def test_update_contact_all_fields():
    client = mock_client()
    client.set.return_value = {"updated": {"c1": None}}
    await _tool(client, "contacts_update_contact")(
        contact_id="c1",
        name="Bob",
        emails=["bob@example.com"],
        phones=["+1234"],
        org="Acme",
        notes="VIP",
        address_book_ids=["ab1"],
    )
    _, kwargs = client.set.call_args
    patch = kwargs["update"]["c1"]
    assert patch["name/full"] == "Bob"
    assert patch["emails"] == {"e0": {"address": "bob@example.com"}}
    assert patch["phones"] == {"p0": {"number": "+1234"}}
    assert patch["organizations"] == {"o0": {"name": "Acme"}}
    assert patch["notes"] == {"n0": {"note": "VIP"}}
    assert patch["addressBookIds"] == {"ab1": True}


async def test_update_contact_no_fields():
    client = mock_client()
    result = await _tool(client, "contacts_update_contact")(contact_id="c1")
    data = json.loads(result)
    assert data == {"error": "No fields to update"}
    client.set.assert_not_called()


async def test_update_contact_not_updated_error():
    client = mock_client()
    client.set.return_value = {
        "notUpdated": {"c1": {"type": "notFound", "description": "Contact not found"}}
    }
    result = await _tool(client, "contacts_update_contact")(contact_id="c1", name="X")
    data = json.loads(result)
    assert data == {"error": "Contact not found"}


async def test_update_contact_no_response():
    client = mock_client()
    client.set.return_value = {}
    result = await _tool(client, "contacts_update_contact")(contact_id="c1", name="X")
    data = json.loads(result)
    assert data == {"error": "No response from server"}


async def test_update_contact_fastmail_error():
    client = mock_client()
    client.set.side_effect = FastmailError("auth failed")
    result = await _tool(client, "contacts_update_contact")(contact_id="c1", name="X")
    data = json.loads(result)
    assert "auth failed" in data["error"]


async def test_update_contact_request_exception():
    client = mock_client()
    client.set.side_effect = requests.RequestException("network error")
    result = await _tool(client, "contacts_update_contact")(contact_id="c1", name="X")
    data = json.loads(result)
    assert "network error" in data["error"]
