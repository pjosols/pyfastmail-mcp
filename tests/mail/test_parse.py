"""Tests for mail_parse_email tool."""

import json
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.parse import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name="mail_parse_email"):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _parse_response(parsed=None, not_parseable=None, not_found=None):
    return [
        (
            "Email/parse",
            {
                "parsed": parsed or {},
                "notParseable": not_parseable or [],
                "notFound": not_found or [],
            },
            "p",
        )
    ]


@pytest.mark.asyncio
async def test_parse_success():
    client = mock_client()
    client.call.return_value = _parse_response(
        parsed={
            "b1": {
                "subject": "Hello",
                "from": [{"email": "a@example.com"}],
                "to": [{"email": "b@example.com"}],
                "cc": None,
                "receivedAt": "2026-01-01T00:00:00Z",
                "bodyValues": {"1": {"value": "Hi there"}},
                "textBody": [{"partId": "1"}],
                "htmlBody": [],
                "attachments": [],
                "hasAttachment": False,
            }
        }
    )

    result = json.loads(await _tool(client)(blob_ids=["b1"]))

    assert len(result) == 1
    assert result[0]["blobId"] == "b1"
    assert result[0]["subject"] == "Hello"
    assert result[0]["body"] == "Hi there"
    assert result[0]["hasAttachment"] is False
    assert result[0]["attachments"] == []


@pytest.mark.asyncio
async def test_parse_sends_correct_request():
    client = mock_client()
    client.call.return_value = _parse_response(
        parsed={
            "b1": {
                "subject": None,
                "from": None,
                "to": None,
                "cc": None,
                "receivedAt": None,
                "bodyValues": {},
                "textBody": [],
                "attachments": [],
                "hasAttachment": False,
            }
        }
    )

    await _tool(client)(blob_ids=["b1"])

    _, method_calls = client.call.call_args[0]
    method, params, tag = method_calls[0]
    assert method == "Email/parse"
    assert params["accountId"] == "acc99"
    assert params["blobIds"] == ["b1"]
    assert "properties" in params
    assert params["fetchAllBodyValues"] is True


@pytest.mark.asyncio
async def test_parse_with_attachments():
    client = mock_client()
    client.call.return_value = _parse_response(
        parsed={
            "b1": {
                "subject": "With attachment",
                "from": None,
                "to": None,
                "cc": None,
                "receivedAt": None,
                "bodyValues": {},
                "textBody": [],
                "attachments": [
                    {"name": "file.pdf", "type": "application/pdf", "size": 1024}
                ],
                "hasAttachment": True,
            }
        }
    )

    result = json.loads(await _tool(client)(blob_ids=["b1"]))

    assert result[0]["hasAttachment"] is True
    assert result[0]["attachments"] == [
        {"name": "file.pdf", "type": "application/pdf", "size": 1024}
    ]


@pytest.mark.asyncio
async def test_parse_not_parseable():
    client = mock_client()
    client.call.return_value = _parse_response(not_parseable=["b1"])

    result = json.loads(await _tool(client)(blob_ids=["b1"]))

    assert result[0] == {"blobId": "b1", "error": "not parseable as RFC 5322"}


@pytest.mark.asyncio
async def test_parse_not_found():
    client = mock_client()
    client.call.return_value = _parse_response(not_found=["b1"])

    result = json.loads(await _tool(client)(blob_ids=["b1"]))

    assert result[0] == {"blobId": "b1", "error": "blob not found"}


@pytest.mark.asyncio
async def test_parse_mixed_results():
    client = mock_client()
    client.call.return_value = _parse_response(
        parsed={
            "b1": {
                "subject": "OK",
                "from": None,
                "to": None,
                "cc": None,
                "receivedAt": None,
                "bodyValues": {},
                "textBody": [],
                "attachments": [],
                "hasAttachment": False,
            }
        },
        not_found=["b2"],
        not_parseable=["b3"],
    )

    result = json.loads(await _tool(client)(blob_ids=["b1", "b2", "b3"]))

    assert result[0]["blobId"] == "b1"
    assert result[0]["subject"] == "OK"
    assert result[1] == {"blobId": "b2", "error": "blob not found"}
    assert result[2] == {"blobId": "b3", "error": "not parseable as RFC 5322"}


@pytest.mark.asyncio
async def test_parse_exception_handling():
    from pyfastmail_mcp.exceptions import JMAPError

    client = mock_client()
    client.call.side_effect = JMAPError(
        method="Email/parse", error_type="serverFail", description="boom"
    )

    result = json.loads(await _tool(client)(blob_ids=["b1"]))

    assert "error" in result
