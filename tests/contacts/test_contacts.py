"""Tests for contacts_list_address_books in tools/contacts/contacts.py."""

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


def _ab_response(address_books):
    return [("AddressBook/get", {"list": address_books}, "a")]


async def test_list_address_books_ok():
    client = mock_client()
    client.call.return_value = _ab_response(
        [
            {
                "id": "ab1",
                "name": "Personal",
                "description": "",
                "sortOrder": 0,
                "isDefault": True,
                "isSubscribed": True,
            }
        ]
    )
    result = await _tool(client, "contacts_list_address_books")()
    data = json.loads(result)
    assert data[0]["id"] == "ab1"
    assert data[0]["isDefault"] is True


async def test_list_address_books_multiple():
    client = mock_client()
    client.call.return_value = _ab_response(
        [
            {
                "id": "ab1",
                "name": "Personal",
                "description": "",
                "sortOrder": 0,
                "isDefault": True,
                "isSubscribed": True,
            },
            {
                "id": "ab2",
                "name": "Work",
                "description": "Work contacts",
                "sortOrder": 1,
                "isDefault": False,
                "isSubscribed": True,
            },
        ]
    )
    result = await _tool(client, "contacts_list_address_books")()
    data = json.loads(result)
    assert len(data) == 2
    assert data[1]["name"] == "Work"


async def test_list_address_books_empty():
    client = mock_client()
    client.call.return_value = _ab_response([])
    result = await _tool(client, "contacts_list_address_books")()
    assert json.loads(result) == []


async def test_list_address_books_uses_get_not_query():
    """Verify AddressBook/get is called with ids=None (not AddressBook/query)."""
    client = mock_client()
    client.call.return_value = _ab_response([])
    await _tool(client, "contacts_list_address_books")()
    args = client.call.call_args
    method_calls = args[0][1]
    assert method_calls[0][0] == "AddressBook/get"
    assert method_calls[0][1]["ids"] is None


async def test_list_address_books_fastmail_error():
    client = mock_client()
    client.call.side_effect = FastmailError("auth failed")
    result = await _tool(client, "contacts_list_address_books")()
    data = json.loads(result)
    assert "error" in data
    assert "auth failed" in data["error"]


async def test_list_address_books_request_error():
    client = mock_client()
    client.call.side_effect = requests.RequestException("network error")
    result = await _tool(client, "contacts_list_address_books")()
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]
