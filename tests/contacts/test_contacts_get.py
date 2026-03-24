"""Tests for contacts_get_contact in tools/contacts/contacts.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.contacts.contacts import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _response(list_=None, not_found=None):
    data = {"list": list_ or []}
    if not_found:
        data["notFound"] = not_found
    return [("ContactCard/get", data, "g")]


async def test_get_contact_ok():
    client = mock_client()
    card = {
        "id": "c1",
        "addressBookIds": {"ab1": True},
        "name": {"full": "Alice"},
        "emails": {"e1": {"email": "alice@example.com"}},
        "phones": None,
        "addresses": None,
        "organizations": None,
        "notes": None,
    }
    client.call.return_value = _response([card])
    result = await _tool(client, "contacts_get_contact")(ids=["c1"])
    data = json.loads(result)
    assert data["list"][0]["id"] == "c1"
    assert data["list"][0]["name"]["full"] == "Alice"


async def test_get_contact_multiple():
    client = mock_client()
    cards = [{"id": "c1"}, {"id": "c2"}]
    client.call.return_value = _response(cards)
    result = await _tool(client, "contacts_get_contact")(ids=["c1", "c2"])
    data = json.loads(result)
    assert len(data["list"]) == 2


async def test_get_contact_not_found():
    client = mock_client()
    client.call.return_value = _response([], not_found=["missing-id"])
    result = await _tool(client, "contacts_get_contact")(ids=["missing-id"])
    data = json.loads(result)
    assert data["list"] == []
    assert "missing-id" in data["notFound"]


async def test_get_contact_partial_not_found():
    client = mock_client()
    client.call.return_value = _response([{"id": "c1"}], not_found=["bad"])
    result = await _tool(client, "contacts_get_contact")(ids=["c1", "bad"])
    data = json.loads(result)
    assert len(data["list"]) == 1
    assert "bad" in data["notFound"]


async def test_get_contact_fastmail_error():
    client = mock_client()
    client.call.side_effect = FastmailError("jmap error")
    result = await _tool(client, "contacts_get_contact")(ids=["c1"])
    data = json.loads(result)
    assert "error" in data
    assert "jmap error" in data["error"]


async def test_get_contact_request_error():
    client = mock_client()
    client.call.side_effect = requests.RequestException("network down")
    result = await _tool(client, "contacts_get_contact")(ids=["c1"])
    data = json.loads(result)
    assert "error" in data
    assert "network down" in data["error"]
