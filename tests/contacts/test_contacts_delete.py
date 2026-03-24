"""Tests for contacts_delete_contact in tools/contacts/contacts_write.py."""

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


async def test_delete_single_contact():
    client = mock_client()
    client.set.return_value = {"destroyed": ["c1"]}
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1"])
    data = json.loads(result)
    assert data == {"destroyed": ["c1"]}
    _, kwargs = client.set.call_args
    assert kwargs["destroy"] == ["c1"]


async def test_delete_multiple_contacts():
    client = mock_client()
    client.set.return_value = {"destroyed": ["c1", "c2"]}
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1", "c2"])
    data = json.loads(result)
    assert data["destroyed"] == ["c1", "c2"]


async def test_delete_contact_not_destroyed_error():
    client = mock_client()
    client.set.return_value = {
        "notDestroyed": {"c1": {"type": "notFound", "description": "Contact not found"}}
    }
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1"])
    data = json.loads(result)
    assert data == {"errors": {"c1": "Contact not found"}}


async def test_delete_contact_partial_success():
    client = mock_client()
    client.set.return_value = {
        "destroyed": ["c1"],
        "notDestroyed": {"c2": {"type": "notFound", "description": "Not found"}},
    }
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1", "c2"])
    data = json.loads(result)
    assert data["destroyed"] == ["c1"]
    assert data["errors"] == {"c2": "Not found"}


async def test_delete_contact_fastmail_error():
    client = mock_client()
    client.set.side_effect = FastmailError("auth failed")
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1"])
    data = json.loads(result)
    assert "auth failed" in data["error"]


async def test_delete_contact_request_exception():
    client = mock_client()
    client.set.side_effect = requests.RequestException("network error")
    result = await _tool(client, "contacts_delete_contact")(contact_ids=["c1"])
    data = json.loads(result)
    assert "network error" in data["error"]
