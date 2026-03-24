"""Tests for _humanize_errors in actions.py and its use in labels.py."""

import json
from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.actions import (
    _humanize_errors,
)
from pyfastmail_mcp.tools.mail.actions import register as register_actions
from pyfastmail_mcp.tools.mail.labels import register as register_labels

# --- Unit tests for _humanize_errors ---


def test_humanize_too_many_keywords():
    result = _humanize_errors({"e1": {"type": "tooManyKeywords"}})
    assert result["e1"]["type"] == "tooManyKeywords"
    assert "Too many keywords" in result["e1"]["error"]


def test_humanize_too_many_mailboxes():
    result = _humanize_errors({"e1": {"type": "tooManyMailboxes"}})
    assert "Too many mailboxes" in result["e1"]["error"]


def test_humanize_blob_not_found():
    result = _humanize_errors({"e1": {"type": "blobNotFound"}})
    assert "blob" in result["e1"]["error"].lower()


def test_humanize_unknown_error_passthrough():
    err = {"type": "notFound", "description": "gone"}
    result = _humanize_errors({"e1": err})
    assert result["e1"] == err


def test_humanize_multiple_errors():
    errors = {
        "e1": {"type": "tooManyKeywords"},
        "e2": {"type": "notFound"},
    }
    result = _humanize_errors(errors)
    assert "error" in result["e1"]
    assert result["e2"] == errors["e2"]


# --- Integration: tooManyKeywords surfaced via mail_mark_email_read ---


def _actions_tool(client, name):
    server = FastMCP("test")
    register_actions(server, client)
    return server._tool_manager._tools[name].fn


async def test_mark_read_too_many_keywords():
    client = MagicMock()
    client.set.return_value = {
        "updated": {},
        "notUpdated": {"e1": {"type": "tooManyKeywords"}},
    }
    result = json.loads(
        await _actions_tool(client, "mail_mark_email_read")(email_ids=["e1"])
    )
    assert "Too many keywords" in result["notUpdated"]["e1"]["error"]


# --- Integration: tooManyKeywords surfaced via mail_manage_email_labels ---


def _labels_tool(client):
    server = FastMCP("test")
    register_labels(server, client)
    return server._tool_manager._tools["mail_manage_email_labels"].fn


async def test_labels_too_many_keywords():
    client = MagicMock()
    client.set.return_value = {
        "updated": {},
        "notUpdated": {"e1": {"type": "tooManyKeywords"}},
    }
    result = json.loads(
        await _labels_tool(client)(email_ids=["e1"], add=["custom-tag"])
    )
    assert "Too many keywords" in result["notUpdated"]["e1"]["error"]


async def test_labels_too_many_mailboxes():
    client = MagicMock()
    client.set.return_value = {
        "updated": {},
        "notUpdated": {"e1": {"type": "tooManyMailboxes"}},
    }
    result = json.loads(await _labels_tool(client)(email_ids=["e1"], add=["$flagged"]))
    assert "Too many mailboxes" in result["notUpdated"]["e1"]["error"]
