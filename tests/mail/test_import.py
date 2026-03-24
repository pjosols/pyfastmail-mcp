"""Tests for mail_import_email tool."""

import json
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.import_ import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name="mail_import_email"):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _import_response(created=None, not_created=None):
    return [
        (
            "Email/import",
            {
                "created": created or {},
                "notCreated": not_created or {},
            },
            "i",
        )
    ]


@pytest.mark.asyncio
async def test_import_success():
    client = mock_client()
    client.call.return_value = _import_response(
        created={"1": {"id": "e1", "blobId": "b1", "threadId": "t1", "size": 512}}
    )

    result = json.loads(await _tool(client)(blob_id="b1", mailbox_ids=["m1"]))

    assert result == {"id": "e1", "blob_id": "b1", "thread_id": "t1", "size": 512}


@pytest.mark.asyncio
async def test_import_builds_correct_request():
    client = mock_client()
    client.call.return_value = _import_response(
        created={"1": {"id": "e1", "blobId": "b1", "threadId": "t1", "size": 100}}
    )

    await _tool(client)(
        blob_id="b1",
        mailbox_ids=["m1", "m2"],
        keywords=["$seen"],
        received_at="2026-01-01T00:00:00Z",
    )

    _, method_calls = client.call.call_args[0]
    _, params, _ = method_calls[0]
    email_obj = params["emails"]["1"]
    assert email_obj["blobId"] == "b1"
    assert email_obj["mailboxIds"] == {"m1": True, "m2": True}
    assert email_obj["keywords"] == {"$seen": True}
    assert email_obj["receivedAt"] == "2026-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_import_blob_not_found():
    client = mock_client()
    client.call.return_value = _import_response(
        not_created={"1": {"type": "blobNotFound"}}
    )

    result = json.loads(await _tool(client)(blob_id="missing", mailbox_ids=["m1"]))

    assert "error" in result
    assert "missing" in result["error"]


@pytest.mark.asyncio
async def test_import_invalid_email():
    client = mock_client()
    client.call.return_value = _import_response(
        not_created={"1": {"type": "invalidEmail"}}
    )

    result = json.loads(await _tool(client)(blob_id="b1", mailbox_ids=["m1"]))

    assert result == {"error": "Email blob is not a valid RFC 5322 message"}


@pytest.mark.asyncio
async def test_import_over_quota():
    client = mock_client()
    client.call.return_value = _import_response(
        not_created={"1": {"type": "overQuota"}}
    )

    result = json.loads(await _tool(client)(blob_id="b1", mailbox_ids=["m1"]))

    assert result == {"error": "Account is over quota"}


@pytest.mark.asyncio
async def test_import_exception_handling():
    from pyfastmail_mcp.exceptions import JMAPError

    client = mock_client()
    client.call.side_effect = JMAPError(
        method="Email/import", error_type="serverFail", description="boom"
    )

    result = json.loads(await _tool(client)(blob_id="b1", mailbox_ids=["m1"]))

    assert "error" in result
