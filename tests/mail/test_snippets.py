"""Tests for mail_search_snippets."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.mail.snippets import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


@pytest.mark.asyncio
async def test_basic_no_filter():
    client = mock_client()
    snippets = [{"emailId": "e1", "subject": "Hello", "preview": "World"}]
    client.call.return_value = [("SearchSnippet/get", {"list": snippets}, "s")]

    result = json.loads(await _tool(client, "mail_search_snippets")(email_ids=["e1"]))

    assert result == snippets
    args = client.call.call_args[0][1][0][1]
    assert args["emailIds"] == ["e1"]
    assert "filter" not in args


@pytest.mark.asyncio
async def test_with_text_filter():
    client = mock_client()
    client.call.return_value = [("SearchSnippet/get", {"list": []}, "s")]

    await _tool(client, "mail_search_snippets")(email_ids=["e1"], text="hello")

    args = client.call.call_args[0][1][0][1]
    assert args["filter"] == {"text": "hello"}


@pytest.mark.asyncio
async def test_all_filters():
    client = mock_client()
    client.call.return_value = [("SearchSnippet/get", {"list": []}, "s")]

    await _tool(client, "mail_search_snippets")(
        email_ids=["e1"],
        text="q",
        from_="a@b.com",
        to="c@d.com",
        subject="sub",
        has_attachment=True,
    )

    args = client.call.call_args[0][1][0][1]
    assert args["filter"] == {
        "text": "q",
        "from": "a@b.com",
        "to": "c@d.com",
        "subject": "sub",
        "hasAttachment": True,
    }


@pytest.mark.asyncio
async def test_fastmail_error():
    client = mock_client()
    client.call.side_effect = FastmailError("boom")

    result = json.loads(await _tool(client, "mail_search_snippets")(email_ids=["e1"]))

    assert result == {"error": "boom"}


@pytest.mark.asyncio
async def test_request_exception():
    client = mock_client()
    client.call.side_effect = requests.RequestException("net error")

    result = json.loads(await _tool(client, "mail_search_snippets")(email_ids=["e1"]))

    assert "net error" in result["error"]


@pytest.mark.asyncio
async def test_empty_list_response():
    client = mock_client()
    client.call.return_value = [("SearchSnippet/get", {"list": []}, "s")]

    result = json.loads(await _tool(client, "mail_search_snippets")(email_ids=[]))

    assert result == []
