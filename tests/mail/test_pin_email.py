"""Tests for mail_pin_email in tools/mail/actions.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.mail.actions import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


async def test_pin_email_ok():
    client = mock_client()
    client.set.return_value = {"updated": {"e1": None, "e2": None}}
    result = await _tool(client, "mail_pin_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert set(data["updated"]) == {"e1", "e2"}
    assert "notUpdated" not in data
    client.set.assert_called_once_with(
        "Email",
        update={"e1": {"keywords/$flagged": True}, "e2": {"keywords/$flagged": True}},
    )


async def test_unpin_email():
    client = mock_client()
    client.set.return_value = {"updated": {"e1": None}}
    result = await _tool(client, "mail_pin_email")(email_ids=["e1"], pin=False)
    data = json.loads(result)
    assert data["updated"] == ["e1"]
    client.set.assert_called_once_with(
        "Email", update={"e1": {"keywords/$flagged": None}}
    )


async def test_pin_email_partial_failure():
    client = mock_client()
    client.set.return_value = {
        "updated": {"e1": None},
        "notUpdated": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_pin_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert data["updated"] == ["e1"]
    assert "e2" in data["notUpdated"]


async def test_pin_email_fastmail_error():
    client = mock_client()
    client.set.side_effect = FastmailError("jmap error")
    result = await _tool(client, "mail_pin_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "jmap error" in data["error"]


async def test_pin_email_request_exception():
    client = mock_client()
    client.set.side_effect = requests.RequestException("network error")
    result = await _tool(client, "mail_pin_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]
