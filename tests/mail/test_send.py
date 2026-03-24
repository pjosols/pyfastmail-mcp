"""Tests for mail_send_email in tools/mail/send.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.send import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


_IDENTITY = {"id": "ident1", "name": "Alice", "email": "alice@example.com"}


def _identity_response():
    return [("Identity/get", {"list": [_IDENTITY]}, "i")]


def _send_response(email_id="e1", sub_id="s1"):
    return [
        ("Email/set", {"created": {"draft": {"id": email_id}}}, "e"),
        ("EmailSubmission/set", {"created": {"sub": {"id": sub_id}}}, "s"),
    ]


async def test_send_email_ok():
    client = mock_client()
    client.call.side_effect = [_identity_response(), _send_response()]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello"
    )
    data = json.loads(result)
    assert data == {"sent": True, "emailId": "e1", "submissionId": "s1"}


async def test_send_email_with_cc_bcc_html():
    client = mock_client()
    client.call.side_effect = [_identity_response(), _send_response()]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"],
        subject="Hi",
        text_body="Hello",
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        html_body="<p>Hello</p>",
    )
    data = json.loads(result)
    assert data["sent"] is True
    email_set_call = client.call.call_args_list[1]
    email_obj = email_set_call[0][1][0][1]["create"]["draft"]
    assert email_obj["cc"] == [{"email": "cc@example.com"}]
    assert email_obj["bcc"] == [{"email": "bcc@example.com"}]
    assert "htmlBody" in email_obj


async def test_send_email_explicit_identity():
    client = mock_client()
    client.call.side_effect = [_identity_response(), _send_response()]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello", identity_id="ident1"
    )
    assert json.loads(result)["sent"] is True


async def test_send_email_identity_not_found():
    client = mock_client()
    client.call.side_effect = [_identity_response()]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello", identity_id="bad-id"
    )
    data = json.loads(result)
    assert "error" in data
    assert "bad-id" in data["error"]


async def test_send_email_no_identities():
    client = mock_client()
    client.call.return_value = [("Identity/get", {"list": []}, "i")]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello"
    )
    data = json.loads(result)
    assert "error" in data


async def test_send_email_submission_not_created():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        [
            ("Email/set", {"created": {"draft": {"id": "e1"}}}, "e"),
            (
                "EmailSubmission/set",
                {"notCreated": {"sub": {"type": "forbidden"}}},
                "s",
            ),
        ],
    ]
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello"
    )
    data = json.loads(result)
    assert "error" in data


async def test_send_email_client_error():
    client = mock_client()
    client.call.side_effect = requests.RequestException("network failure")
    result = await _tool(client, "mail_send_email")(
        to=["bob@example.com"], subject="Hi", text_body="Hello"
    )
    data = json.loads(result)
    assert "error" in data
    assert "network failure" in data["error"]


def _submission_error_response(error_type, **extra):
    return [
        ("Email/set", {"created": {"draft": {"id": "e1"}}}, "e"),
        (
            "EmailSubmission/set",
            {"notCreated": {"sub": {"type": error_type, **extra}}},
            "s",
        ),
    ]


async def test_send_forbidden_from():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("forbiddenFrom"),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Not permitted to send from this address" in result["error"]


async def test_send_forbidden_to_send():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("forbiddenToSend"),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Sending is not permitted for this account" in result["error"]


async def test_send_forbidden_mail_from():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("forbiddenMailFrom"),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Not permitted to use this envelope sender" in result["error"]


async def test_send_too_many_recipients():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("tooManyRecipients", maxRecipients=10),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Too many recipients (max: 10)" in result["error"]


async def test_send_no_recipients():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("noRecipients"),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "No recipients specified" in result["error"]


async def test_send_invalid_recipients():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("invalidRecipients", invalidRecipients=["bad@"]),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Invalid recipient addresses" in result["error"]
    assert "bad@" in result["error"]


async def test_send_invalid_email():
    client = mock_client()
    client.call.side_effect = [
        _identity_response(),
        _submission_error_response("invalidEmail"),
    ]
    result = json.loads(
        await _tool(client, "mail_send_email")(
            to=["x@y.com"], subject="s", text_body="b"
        )
    )
    assert "Email is invalid" in result["error"]
