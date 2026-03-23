"""Verify that tool exception handlers are narrowed — programming errors propagate."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.exceptions import FastmailError


def _jmap_client():
    c = MagicMock()
    c.account_id = "acc99"
    return c


def _dav_client():
    c = MagicMock()
    c.email = "user@example.com"
    return c


def _tool(register_fn, client, name):
    server = FastMCP("test")
    register_fn(server, client)
    return server._tool_manager._tools[name].fn


# --- FastmailError is caught and returned as JSON ---


@pytest.mark.asyncio
async def test_fastmail_error_returns_json_payload():
    from pyfastmail_mcp.tools.mail.mailbox import register

    client = _jmap_client()
    client.query_and_get.side_effect = FastmailError("jmap failure")
    result = json.loads(await _tool(register, client, "mail_list_mailboxes")())
    assert "error" in result
    assert "jmap failure" in result["error"]


# --- requests.RequestException is caught and returned as JSON ---


@pytest.mark.asyncio
async def test_requests_exception_returns_json_payload():
    from pyfastmail_mcp.tools.mail.mailbox import register

    client = _jmap_client()
    client.query_and_get.side_effect = requests.RequestException("timeout")
    result = json.loads(await _tool(register, client, "mail_list_mailboxes")())
    assert "error" in result
    assert "timeout" in result["error"]


# --- ValueError is caught and returned as JSON ---


@pytest.mark.asyncio
async def test_value_error_returns_json_payload():
    from pyfastmail_mcp.tools.files.webdav import register

    client = _dav_client()
    # depth validation raises ValueError internally
    result = json.loads(
        await _tool(register, client, "files_list")(depth="infinity")
    )
    assert "error" in result


# --- Programming errors propagate (not swallowed) ---


@pytest.mark.asyncio
async def test_attribute_error_propagates():
    from pyfastmail_mcp.tools.mail.mailbox import register

    client = _jmap_client()
    client.query_and_get.side_effect = AttributeError("bad attr")
    with pytest.raises(AttributeError, match="bad attr"):
        await _tool(register, client, "mail_list_mailboxes")()


@pytest.mark.asyncio
async def test_type_error_propagates():
    from pyfastmail_mcp.tools.mail.email import register

    client = _jmap_client()
    client.call.side_effect = TypeError("wrong type")
    with pytest.raises(TypeError, match="wrong type"):
        await _tool(register, client, "mail_get_email")(email_id="e1")


@pytest.mark.asyncio
async def test_key_error_propagates():
    from pyfastmail_mcp.tools.files.webdav_write import register

    client = _dav_client()
    client.put_bytes.side_effect = KeyError("missing key")
    with pytest.raises(KeyError):
        await _tool(register, client, "files_upload")(
            path="/f.bin", content="aGVsbG8=", content_type="application/octet-stream"
        )
