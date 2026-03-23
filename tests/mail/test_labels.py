"""Tests for tools/mail/labels.py — mail_manage_email_labels."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.labels import register


def _tool(client):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools["mail_manage_email_labels"].fn


def _client(updated=None, not_updated=None):
    c = MagicMock()
    c.set.return_value = {
        "updated": {k: None for k in (updated or [])},
        "notUpdated": not_updated or {},
    }
    return c


async def test_add_keywords():
    c = _client(updated=["e1", "e2"])
    result = json.loads(await _tool(c)(email_ids=["e1", "e2"], add=["$flagged"]))
    c.set.assert_called_once_with(
        "Email",
        update={"e1": {"keywords/$flagged": True}, "e2": {"keywords/$flagged": True}},
    )
    assert result["updated"] == ["e1", "e2"]
    assert "notUpdated" not in result


async def test_remove_keywords():
    c = _client(updated=["e1"])
    result = json.loads(await _tool(c)(email_ids=["e1"], remove=["$seen"]))
    c.set.assert_called_once_with("Email", update={"e1": {"keywords/$seen": None}})
    assert result["updated"] == ["e1"]


async def test_add_and_remove():
    c = _client(updated=["e1"])
    result = json.loads(
        await _tool(c)(email_ids=["e1"], add=["$flagged"], remove=["$seen"])
    )
    patch = c.set.call_args[1]["update"]["e1"]
    assert patch["keywords/$flagged"] is True
    assert patch["keywords/$seen"] is None
    assert result["updated"] == ["e1"]


async def test_partial_failure():
    c = _client(updated=["e1"], not_updated={"e2": {"type": "notFound"}})
    result = json.loads(await _tool(c)(email_ids=["e1", "e2"], add=["$flagged"]))
    assert "e1" in result["updated"]
    assert "e2" in result["notUpdated"]


async def test_no_add_or_remove_returns_error():
    c = MagicMock()
    result = json.loads(await _tool(c)(email_ids=["e1"]))
    assert "error" in result
    c.set.assert_not_called()


async def test_client_error():
    c = MagicMock()
    c.set.side_effect = requests.RequestException("network failure")
    result = json.loads(await _tool(c)(email_ids=["e1"], add=["$flagged"]))
    assert result["error"] == "network failure"
