"""Tests for mail_list_identities in tools/mail/identities.py."""

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
