"""Tests for contacts_list in tools/contacts/contacts.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_CONTACTS
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


async def test_list_no_filters():
    client = mock_client()
    client.query_and_get.return_value = [{"id": "c1", "name": {"full": "Alice"}}]
    result = await _tool(client, "contacts_list")()
    data = json.loads(result)
    assert data[0]["id"] == "c1"
    args, kwargs = client.query_and_get.call_args
    assert args[1] is None
    assert kwargs["using"] == USING_CONTACTS
    assert kwargs.get("limit") is None


async def test_list_filter_address_book():
    client = mock_client()
    client.query_and_get.return_value = []
    await _tool(client, "contacts_list")(address_book_id="ab1")
    args, _ = client.query_and_get.call_args
    assert args[1] == {"inAddressBook": "ab1"}


async def test_list_filter_text():
    client = mock_client()
    client.query_and_get.return_value = []
    await _tool(client, "contacts_list")(text="alice")
    args, _ = client.query_and_get.call_args
    assert args[1] == {"text": "alice"}


async def test_list_combined_filters():
    client = mock_client()
    client.query_and_get.return_value = []
    await _tool(client, "contacts_list")(address_book_id="ab1", text="bob")
    args, _ = client.query_and_get.call_args
    assert args[1] == {"inAddressBook": "ab1", "text": "bob"}


async def test_list_limit():
    client = mock_client()
    client.query_and_get.return_value = []
    await _tool(client, "contacts_list")(limit=5)
    _, kwargs = client.query_and_get.call_args
    assert kwargs["limit"] == 5


async def test_list_empty():
    client = mock_client()
    client.query_and_get.return_value = []
    result = await _tool(client, "contacts_list")()
    assert json.loads(result) == []


async def test_list_fastmail_error():
    client = mock_client()
    client.query_and_get.side_effect = FastmailError("jmap error")
    result = await _tool(client, "contacts_list")()
    data = json.loads(result)
    assert "error" in data
    assert "jmap error" in data["error"]


async def test_list_request_error():
    client = mock_client()
    client.query_and_get.side_effect = requests.RequestException("network down")
    result = await _tool(client, "contacts_list")()
    data = json.loads(result)
    assert "error" in data
    assert "network down" in data["error"]
