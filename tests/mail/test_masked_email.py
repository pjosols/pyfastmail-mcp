"""Tests for masked_email tools in tools/mail/masked_email.py."""

import json

import requests
from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.masked_email import register


def _client():
    c = MagicMock()
    c.account_id = "acc99"
    return c


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


MASKED_ITEM = {
    "id": "m1",
    "email": "abc@masked.fm",
    "state": "enabled",
    "forDomain": "example.com",
    "description": "test",
    "lastMessageAt": None,
    "createdAt": "2024-01-01T00:00:00Z",
}


# --- mail_list_masked_emails ---


async def test_list_all(tmp_path):
    client = _client()
    client.call.return_value = [["MaskedEmail/get", {"list": [MASKED_ITEM]}, "g"]]
    result = json.loads(await _tool(client, "mail_list_masked_emails")())
    assert len(result) == 1
    assert result[0]["id"] == "m1"


async def test_list_filter_domain():
    client = _client()
    other = {**MASKED_ITEM, "id": "m2", "forDomain": "other.com"}
    client.call.return_value = [
        ["MaskedEmail/get", {"list": [MASKED_ITEM, other]}, "g"]
    ]
    result = json.loads(await _tool(client, "mail_list_masked_emails")(domain="example"))
    assert len(result) == 1
    assert result[0]["id"] == "m1"


async def test_list_filter_state():
    client = _client()
    disabled = {**MASKED_ITEM, "id": "m2", "state": "disabled"}
    client.call.return_value = [
        ["MaskedEmail/get", {"list": [MASKED_ITEM, disabled]}, "g"]
    ]
    result = json.loads(await _tool(client, "mail_list_masked_emails")(state="disabled"))
    assert len(result) == 1
    assert result[0]["id"] == "m2"


async def test_list_error():
    client = _client()
    client.call.side_effect = requests.RequestException("boom")
    result = json.loads(await _tool(client, "mail_list_masked_emails")())
    assert "error" in result


# --- mail_create_masked_email ---


async def test_create_ok():
    client = _client()
    client.set.return_value = {
        "created": {"new": {"id": "m1", "email": "abc@masked.fm", "state": "enabled"}}
    }
    result = json.loads(
        await _tool(client, "mail_create_masked_email")(
            for_domain="example.com", description="test"
        )
    )
    assert result["id"] == "m1"
    assert result["email"] == "abc@masked.fm"


async def test_create_with_prefix():
    client = _client()
    client.set.return_value = {
        "created": {
            "new": {"id": "m2", "email": "myprefix@masked.fm", "state": "enabled"}
        }
    }
    result = json.loads(
        await _tool(client, "mail_create_masked_email")(
            for_domain="example.com", description="", email_prefix="myprefix"
        )
    )
    _, kwargs = client.set.call_args
    assert kwargs["create"]["new"]["emailPrefix"] == "myprefix"
    assert result["id"] == "m2"


async def test_create_not_created():
    client = _client()
    client.set.return_value = {"notCreated": {"new": {"description": "invalid prefix"}}}
    result = json.loads(await _tool(client, "mail_create_masked_email")(for_domain="x.com"))
    assert result["error"] == "invalid prefix"


async def test_create_error():
    client = _client()
    client.set.side_effect = requests.RequestException("network error")
    result = json.loads(await _tool(client, "mail_create_masked_email")())
    assert "error" in result


# --- mail_update_masked_email_state ---


async def test_update_enable():
    client = _client()
    client.set.return_value = {"updated": {"m1": None}}
    result = json.loads(
        await _tool(client, "mail_update_masked_email_state")(
            masked_email_id="m1", state="enabled"
        )
    )
    assert result == {"updated": "m1", "state": "enabled"}


async def test_update_disable():
    client = _client()
    client.set.return_value = {"updated": {"m1": None}}
    result = json.loads(
        await _tool(client, "mail_update_masked_email_state")(
            masked_email_id="m1", state="disabled"
        )
    )
    assert result["state"] == "disabled"


async def test_update_invalid_state():
    client = _client()
    result = json.loads(
        await _tool(client, "mail_update_masked_email_state")(
            masked_email_id="m1", state="deleted"
        )
    )
    assert "error" in result
    client.set.assert_not_called()


async def test_update_not_updated():
    client = _client()
    client.set.return_value = {"notUpdated": {"m1": {"description": "not found"}}}
    result = json.loads(
        await _tool(client, "mail_update_masked_email_state")(
            masked_email_id="m1", state="enabled"
        )
    )
    assert result["error"] == "not found"


async def test_update_error():
    client = _client()
    client.set.side_effect = requests.RequestException("timeout")
    result = json.loads(
        await _tool(client, "mail_update_masked_email_state")(
            masked_email_id="m1", state="enabled"
        )
    )
    assert "error" in result
