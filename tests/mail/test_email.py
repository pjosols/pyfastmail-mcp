"""Tests for tools/mail/email.py."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.email import _extract_body, register


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.account_id = "acc1"
    return client


def _tool(mock_client, name="mail_get_email"):
    server = FastMCP("test")
    register(server, mock_client)
    return server._tool_manager._tools[name].fn


EMAIL = {
    "id": "e1",
    "subject": "Hello",
    "from": [{"email": "a@example.com"}],
    "to": [{"email": "b@example.com"}],
    "cc": None,
    "receivedAt": "2026-01-01T00:00:00Z",
    "bodyValues": {"1": {"value": "plain text"}, "2": {"value": "<b>html</b>"}},
    "textBody": [{"partId": "1"}],
    "htmlBody": [{"partId": "2"}],
    "attachments": [{"name": "file.pdf", "type": "application/pdf", "size": 1024}],
    "hasAttachment": True,
}


async def test_get_email_ok(mock_client):
    mock_client.call.return_value = [["Email/get", {"list": [EMAIL]}, "g"]]
    result = json.loads(await _tool(mock_client)(email_id="e1"))
    assert result["id"] == "e1"
    assert result["subject"] == "Hello"
    assert result["body"] == "plain text"
    assert result["attachments"] == [
        {"name": "file.pdf", "type": "application/pdf", "size": 1024}
    ]
    assert result["hasAttachment"] is True


async def test_get_email_prefer_html(mock_client):
    mock_client.call.return_value = [["Email/get", {"list": [EMAIL]}, "g"]]
    result = json.loads(await _tool(mock_client)(email_id="e1", prefer_html=True))
    assert result["body"] == "<b>html</b>"


async def test_get_email_not_found(mock_client):
    mock_client.call.return_value = [["Email/get", {"list": []}, "g"]]
    result = json.loads(await _tool(mock_client)(email_id="missing"))
    assert "not found" in result["error"]


async def test_get_email_client_error(mock_client):
    mock_client.call.side_effect = requests.RequestException("network failure")
    result = json.loads(await _tool(mock_client)(email_id="e1"))
    assert "network failure" in result["error"]


async def test_get_email_no_attachments(mock_client):
    email = {**EMAIL, "attachments": None, "hasAttachment": False}
    mock_client.call.return_value = [["Email/get", {"list": [email]}, "g"]]
    result = json.loads(await _tool(mock_client)(email_id="e1"))
    assert result["attachments"] == []


def test_extract_body_text():
    assert _extract_body(EMAIL, prefer_html=False) == "plain text"


def test_extract_body_html():
    assert _extract_body(EMAIL, prefer_html=True) == "<b>html</b>"


def test_extract_body_html_fallback_to_text():
    email = {**EMAIL, "htmlBody": []}
    assert _extract_body(email, prefer_html=True) == "plain text"


def test_extract_body_missing():
    assert _extract_body({"bodyValues": {}, "textBody": []}, prefer_html=False) is None


SUMMARY = [
    {
        "id": "e1",
        "subject": "Hi",
        "from": [{"email": "a@b.com"}],
        "receivedAt": "2026-01-01T00:00:00Z",
    }
]


async def test_search_emails_no_filters(mock_client):
    mock_client.query_and_get.return_value = SUMMARY
    result = json.loads(await _tool(mock_client, "mail_search_emails")())
    assert result == SUMMARY
    mock_client.query_and_get.assert_called_once()
    call_args, call_kwargs = mock_client.query_and_get.call_args
    assert call_args[1] is None


async def test_search_emails_with_filters(mock_client):
    mock_client.query_and_get.return_value = SUMMARY
    await _tool(mock_client, "mail_search_emails")(
        text="hello",
        from_="a@b.com",
        to="c@d.com",
        subject="Hi",
        has_attachment=True,
        limit=5,
        newest_first=False,
    )
    call_args, call_kwargs = mock_client.query_and_get.call_args
    assert call_args[1] == {
        "text": "hello",
        "from": "a@b.com",
        "to": "c@d.com",
        "subject": "Hi",
        "hasAttachment": True,
    }
    assert call_kwargs["limit"] == 5
    assert call_kwargs["sort"] == [{"property": "receivedAt", "isAscending": True}]


async def test_search_emails_error(mock_client):
    mock_client.query_and_get.side_effect = requests.RequestException("boom")
    result = json.loads(await _tool(mock_client, "mail_search_emails")())
    assert "boom" in result["error"]


async def test_get_recent_emails_ok(mock_client):
    mock_client.query_and_get.return_value = SUMMARY
    result = json.loads(await _tool(mock_client, "mail_get_recent_emails")())
    assert result == SUMMARY
    call_args, call_kwargs = mock_client.query_and_get.call_args
    assert "after" in call_args[1]
    assert call_kwargs["limit"] == 20


async def test_get_recent_emails_custom_days(mock_client):
    mock_client.query_and_get.return_value = []
    await _tool(mock_client, "mail_get_recent_emails")(days=3, limit=5)
    _, call_kwargs = mock_client.query_and_get.call_args
    assert call_kwargs["limit"] == 5


async def test_get_recent_emails_error(mock_client):
    mock_client.query_and_get.side_effect = requests.RequestException("timeout")
    result = json.loads(await _tool(mock_client, "mail_get_recent_emails")())
    assert "timeout" in result["error"]
