"""Tests for mail_reply_to_email in tools/mail/reply.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.reply import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


_IDENTITY = {"id": "ident1", "name": "Alice", "email": "alice@example.com"}

_ORIGINAL_EMAIL = {
    "id": "orig1",
    "subject": "Hello",
    "from": [{"email": "bob@example.com", "name": "Bob"}],
    "to": [{"email": "alice@example.com"}],
    "cc": [],
    "replyTo": None,
    "messageId": ["<msg1@example.com>"],
    "references": ["<ref1@example.com>"],
    "bodyValues": {"1": {"value": "Original text"}},
    "textBody": [{"partId": "1", "type": "text/plain"}],
}


def _email_get_response(email=None):
    return [("Email/get", {"list": [email or _ORIGINAL_EMAIL]}, "g")]


def _identity_response():
    return [("Identity/get", {"list": [_IDENTITY]}, "i")]


def _send_response(email_id="e2", sub_id="s2"):
    return [
        ("Email/set", {"created": {"draft": {"id": email_id}}}, "e"),
        ("EmailSubmission/set", {"created": {"sub": {"id": sub_id}}}, "s"),
    ]


async def test_reply_ok():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        _send_response(),
    ]
    result = await _tool(client, "mail_reply_to_email")(
        email_id="orig1", text_body="My reply"
    )
    data = json.loads(result)
    assert data == {"sent": True, "emailId": "e2", "submissionId": "s2"}


async def test_reply_adds_re_prefix():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        _send_response(),
    ]
    await _tool(client, "mail_reply_to_email")(email_id="orig1", text_body="reply")
    email_obj = client.call.call_args_list[2][0][1][0][1]["create"]["draft"]
    assert email_obj["subject"] == "Re: Hello"


async def test_reply_no_double_re_prefix():
    email = {**_ORIGINAL_EMAIL, "subject": "Re: Hello"}
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(email),
        _identity_response(),
        _send_response(),
    ]
    await _tool(client, "mail_reply_to_email")(email_id="orig1", text_body="reply")
    email_obj = client.call.call_args_list[2][0][1][0][1]["create"]["draft"]
    assert email_obj["subject"] == "Re: Hello"


async def test_reply_threading_headers():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        _send_response(),
    ]
    await _tool(client, "mail_reply_to_email")(email_id="orig1", text_body="reply")
    email_obj = client.call.call_args_list[2][0][1][0][1]["create"]["draft"]
    assert email_obj["inReplyTo"] == ["<msg1@example.com>"]
    assert "<ref1@example.com>" in email_obj["references"]
    assert "<msg1@example.com>" in email_obj["references"]


async def test_reply_quotes_original():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        _send_response(),
    ]
    await _tool(client, "mail_reply_to_email")(email_id="orig1", text_body="My reply")
    email_obj = client.call.call_args_list[2][0][1][0][1]["create"]["draft"]
    body = email_obj["bodyValues"]["body"]["value"]
    assert "My reply" in body
    assert "> Original text" in body


async def test_reply_all_adds_cc():
    email = {
        **_ORIGINAL_EMAIL,
        "to": [{"email": "alice@example.com"}, {"email": "carol@example.com"}],
        "cc": [{"email": "dave@example.com"}],
    }
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(email),
        _identity_response(),
        _send_response(),
    ]
    await _tool(client, "mail_reply_to_email")(
        email_id="orig1", text_body="reply", reply_all=True
    )
    email_obj = client.call.call_args_list[2][0][1][0][1]["create"]["draft"]
    cc_emails = {a["email"] for a in email_obj.get("cc", [])}
    assert "carol@example.com" in cc_emails
    assert "dave@example.com" in cc_emails
    assert "alice@example.com" not in cc_emails


async def test_reply_email_not_found():
    client = mock_client()
    client.call.return_value = [("Email/get", {"list": []}, "g")]
    result = await _tool(client, "mail_reply_to_email")(
        email_id="missing", text_body="reply"
    )
    data = json.loads(result)
    assert "error" in data
    assert "missing" in data["error"]


async def test_reply_identity_not_found():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        [("Identity/get", {"list": []}, "i")],
    ]
    result = await _tool(client, "mail_reply_to_email")(
        email_id="orig1", text_body="reply"
    )
    data = json.loads(result)
    assert "error" in data


async def test_reply_submission_not_created():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        [
            ("Email/set", {"created": {"draft": {"id": "e2"}}}, "e"),
            (
                "EmailSubmission/set",
                {"notCreated": {"sub": {"type": "forbidden"}}},
                "s",
            ),
        ],
    ]
    result = await _tool(client, "mail_reply_to_email")(
        email_id="orig1", text_body="reply"
    )
    data = json.loads(result)
    assert "error" in data


async def test_reply_client_error():
    client = mock_client()
    client.call.side_effect = requests.RequestException("network failure")
    result = await _tool(client, "mail_reply_to_email")(
        email_id="orig1", text_body="reply"
    )
    data = json.loads(result)
    assert "error" in data
    assert "network failure" in data["error"]


async def test_reply_submission_error_surfaced():
    client = mock_client()
    client.call.side_effect = [
        _email_get_response(),
        _identity_response(),
        [
            ("Email/set", {"created": {"draft": {"id": "e1"}}}, "e"),
            (
                "EmailSubmission/set",
                {"notCreated": {"sub": {"type": "forbiddenFrom"}}},
                "s",
            ),
        ],
    ]
    result = json.loads(
        await _tool(client, "mail_reply_to_email")(email_id="orig1", text_body="reply")
    )
    assert "Not permitted to send from this address" in result["error"]
