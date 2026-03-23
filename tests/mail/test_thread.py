"""Tests for mail_get_email_thread tool."""

import json

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.thread import register


def _client():
    from unittest.mock import MagicMock

    c = MagicMock()
    c.account_id = "acc99"
    return c


def _tool(client):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools["mail_get_email_thread"].fn


_EMAIL = {
    "id": "e1",
    "threadId": "t1",
    "subject": "Hello",
    "from": [{"email": "a@b.com"}],
    "receivedAt": "2024-01-01T00:00:00Z",
    "preview": "Hi",
}
_EMAIL2 = {
    "id": "e2",
    "threadId": "t1",
    "subject": "Re: Hello",
    "from": [{"email": "b@b.com"}],
    "receivedAt": "2024-01-02T00:00:00Z",
    "preview": "Hey",
}


@pytest.mark.asyncio
async def test_get_email_thread_ok():
    client = _client()
    client.call.side_effect = [
        [["Email/get", {"list": [{"threadId": "t1"}]}, "g"]],
        [
            ["Thread/get", {"list": [{"id": "t1", "emailIds": ["e1", "e2"]}]}, "t"],
            ["Email/get", {"list": [_EMAIL, _EMAIL2]}, "e"],
        ],
    ]

    result = json.loads(await _tool(client)(email_id="e1"))

    assert len(result) == 2
    assert result[0]["id"] == "e1"
    assert result[1]["id"] == "e2"


@pytest.mark.asyncio
async def test_get_email_thread_not_found():
    client = _client()
    client.call.return_value = [["Email/get", {"list": []}, "g"]]

    result = json.loads(await _tool(client)(email_id="missing"))

    assert "error" in result
    assert "missing" in result["error"]


@pytest.mark.asyncio
async def test_get_email_thread_client_error():
    client = _client()
    client.call.side_effect = requests.RequestException("network failure")

    result = json.loads(await _tool(client)(email_id="e1"))

    assert result == {"error": "network failure"}
