"""Tests for tools/mail/mailbox.py."""

import json

import requests
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.mailbox import register


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _get_tool(mock_client, name="mail_list_mailboxes"):
    server = FastMCP("test")
    register(server, mock_client)
    return server._tool_manager._tools[name].fn


MAILBOXES = [
    {
        "id": "mb1",
        "name": "Inbox",
        "role": "inbox",
        "totalEmails": 10,
        "unreadEmails": 2,
        "parentId": None,
    },
    {
        "id": "mb2",
        "name": "Sent",
        "role": "sent",
        "totalEmails": 5,
        "unreadEmails": 0,
        "parentId": None,
    },
]


async def test_list_mailboxes_ok(mock_client):
    mock_client.query_and_get.return_value = MAILBOXES
    result = await _get_tool(mock_client)()
    data = json.loads(result)
    assert len(data) == 2
    assert data[0]["name"] == "Inbox"
    assert data[1]["role"] == "sent"
    mock_client.query_and_get.assert_called_once_with(
        "Mailbox",
        None,
        ["id", "name", "role", "totalEmails", "unreadEmails", "parentId"],
    )


async def test_list_mailboxes_empty(mock_client):
    mock_client.query_and_get.return_value = []
    result = await _get_tool(mock_client)()
    assert json.loads(result) == []


async def test_list_mailboxes_error(mock_client):
    mock_client.query_and_get.side_effect = requests.RequestException("network failure")
    result = await _get_tool(mock_client)()
    data = json.loads(result)
    assert "error" in data
    assert "network failure" in data["error"]


# --- mail_create_mailbox ---


async def test_create_mailbox_ok(mock_client):
    mock_client.set.return_value = {"created": {"new": {"id": "mb3", "name": "Work"}}}
    result = await _get_tool(mock_client, "mail_create_mailbox")(name="Work")
    data = json.loads(result)
    assert data["created"]["id"] == "mb3"
    mock_client.set.assert_called_once_with("Mailbox", create={"new": {"name": "Work"}})


async def test_create_mailbox_with_parent(mock_client):
    mock_client.set.return_value = {"created": {"new": {"id": "mb4", "name": "Sub"}}}
    result = await _get_tool(mock_client, "mail_create_mailbox")(name="Sub", parent_id="mb1")
    data = json.loads(result)
    assert data["created"]["id"] == "mb4"
    mock_client.set.assert_called_once_with(
        "Mailbox", create={"new": {"name": "Sub", "parentId": "mb1"}}
    )


async def test_create_mailbox_duplicate(mock_client):
    mock_client.set.return_value = {
        "notCreated": {
            "new": {"type": "invalidArguments", "description": "Name exists"}
        }
    }
    result = await _get_tool(mock_client, "mail_create_mailbox")(name="Inbox")
    data = json.loads(result)
    assert "error" in data
    assert "Name exists" in data["error"]


async def test_create_mailbox_error(mock_client):
    mock_client.set.side_effect = requests.RequestException("server error")
    result = await _get_tool(mock_client, "mail_create_mailbox")(name="X")
    assert "error" in json.loads(result)


# --- mail_rename_mailbox ---


async def test_rename_mailbox_ok(mock_client):
    mock_client.set.return_value = {"updated": {"mb1": None}}
    result = await _get_tool(mock_client, "mail_rename_mailbox")(
        mailbox_id="mb1", new_name="Primary"
    )
    data = json.loads(result)
    assert data["updated"] == "mb1"
    assert data["name"] == "Primary"
    mock_client.set.assert_called_once_with(
        "Mailbox", update={"mb1": {"name": "Primary"}}
    )


async def test_rename_mailbox_not_found(mock_client):
    mock_client.set.return_value = {
        "notUpdated": {"mb99": {"type": "notFound", "description": "Not found"}}
    }
    result = await _get_tool(mock_client, "mail_rename_mailbox")(
        mailbox_id="mb99", new_name="X"
    )
    data = json.loads(result)
    assert "error" in data
    assert "Not found" in data["error"]


async def test_rename_mailbox_error(mock_client):
    mock_client.set.side_effect = requests.RequestException("timeout")
    result = await _get_tool(mock_client, "mail_rename_mailbox")(
        mailbox_id="mb1", new_name="X"
    )
    assert "error" in json.loads(result)


# --- mail_delete_mailbox ---


async def test_delete_mailbox_ok(mock_client):
    mock_client.query_and_get.return_value = [{"id": "mb5", "role": None}]
    mock_client.set.return_value = {"destroyed": ["mb5"]}
    result = await _get_tool(mock_client, "mail_delete_mailbox")(mailbox_id="mb5")
    data = json.loads(result)
    assert data["destroyed"] == "mb5"


async def test_delete_mailbox_system_role_blocked(mock_client):
    mock_client.query_and_get.return_value = [{"id": "mb1", "role": "inbox"}]
    result = await _get_tool(mock_client, "mail_delete_mailbox")(mailbox_id="mb1")
    data = json.loads(result)
    assert "error" in data
    assert "inbox" in data["error"]
    mock_client.set.assert_not_called()


async def test_delete_mailbox_not_destroyed(mock_client):
    mock_client.query_and_get.return_value = [{"id": "mb5", "role": None}]
    mock_client.set.return_value = {
        "notDestroyed": {"mb5": {"type": "notFound", "description": "Gone"}}
    }
    result = await _get_tool(mock_client, "mail_delete_mailbox")(mailbox_id="mb5")
    data = json.loads(result)
    assert "error" in data
    assert "Gone" in data["error"]


async def test_delete_mailbox_error(mock_client):
    mock_client.query_and_get.side_effect = requests.RequestException("network error")
    result = await _get_tool(mock_client, "mail_delete_mailbox")(mailbox_id="mb5")
    assert "error" in json.loads(result)
