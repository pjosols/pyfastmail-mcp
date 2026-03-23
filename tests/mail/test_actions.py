"""Tests for tools/mail/actions.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.actions import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


async def test_mark_email_read_ok():
    client = mock_client()
    client.set.return_value = {"updated": {"e1": None, "e2": None}}
    result = await _tool(client, "mail_mark_email_read")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert set(data["updated"]) == {"e1", "e2"}
    assert "notUpdated" not in data
    client.set.assert_called_once_with(
        "Email",
        update={"e1": {"keywords/$seen": True}, "e2": {"keywords/$seen": True}},
    )


async def test_mark_email_unread():
    client = mock_client()
    client.set.return_value = {"updated": {"e1": None}}
    result = await _tool(client, "mail_mark_email_read")(email_ids=["e1"], read=False)
    data = json.loads(result)
    assert data["updated"] == ["e1"]
    client.set.assert_called_once_with(
        "Email", update={"e1": {"keywords/$seen": False}}
    )


async def test_mark_email_read_partial_failure():
    client = mock_client()
    client.set.return_value = {
        "updated": {"e1": None},
        "notUpdated": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_mark_email_read")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert data["updated"] == ["e1"]
    assert "e2" in data["notUpdated"]


async def test_mark_email_read_error():
    client = mock_client()
    client.set.side_effect = requests.RequestException("server error")
    result = await _tool(client, "mail_mark_email_read")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "server error" in data["error"]


async def test_move_email_ok():
    client = mock_client()
    client.get_mailbox_by_name.return_value = {"id": "mb1", "name": "Archive"}
    client.set.return_value = {"updated": {"e1": None, "e2": None}}
    result = await _tool(client, "mail_move_email")(
        email_ids=["e1", "e2"], mailbox_name="Archive"
    )
    data = json.loads(result)
    assert set(data["moved"]) == {"e1", "e2"}
    assert data["mailboxId"] == "mb1"
    assert "notUpdated" not in data
    client.set.assert_called_once_with(
        "Email",
        update={
            "e1": {"mailboxIds": {"mb1": True}},
            "e2": {"mailboxIds": {"mb1": True}},
        },
    )


async def test_move_email_partial_failure():
    client = mock_client()
    client.get_mailbox_by_name.return_value = {"id": "mb1", "name": "Archive"}
    client.set.return_value = {
        "updated": {"e1": None},
        "notUpdated": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_move_email")(
        email_ids=["e1", "e2"], mailbox_name="Archive"
    )
    data = json.loads(result)
    assert data["moved"] == ["e1"]
    assert "e2" in data["notUpdated"]


async def test_move_email_mailbox_not_found():
    from pyfastmail_mcp.exceptions import MailboxNotFoundError

    client = mock_client()
    client.get_mailbox_by_name.side_effect = MailboxNotFoundError(
        "Mailbox not found: 'Nope'"
    )
    result = await _tool(client, "mail_move_email")(
        email_ids=["e1"], mailbox_name="Nope"
    )
    data = json.loads(result)
    assert "error" in data
    assert "Nope" in data["error"]


async def test_move_email_client_error():
    client = mock_client()
    client.get_mailbox_by_name.side_effect = requests.RequestException("network error")
    result = await _tool(client, "mail_move_email")(
        email_ids=["e1"], mailbox_name="Inbox"
    )
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]


async def test_delete_email_soft_ok():
    client = mock_client()
    client.get_mailbox_by_role.return_value = {"id": "trash1"}
    client.set.return_value = {"updated": {"e1": None, "e2": None}}
    result = await _tool(client, "mail_delete_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert set(data["movedToTrash"]) == {"e1", "e2"}
    assert data["mailboxId"] == "trash1"
    assert "notUpdated" not in data
    client.set.assert_called_once_with(
        "Email",
        update={
            "e1": {"mailboxIds": {"trash1": True}},
            "e2": {"mailboxIds": {"trash1": True}},
        },
    )


async def test_delete_email_soft_partial_failure():
    client = mock_client()
    client.get_mailbox_by_role.return_value = {"id": "trash1"}
    client.set.return_value = {
        "updated": {"e1": None},
        "notUpdated": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_delete_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert data["movedToTrash"] == ["e1"]
    assert "e2" in data["notUpdated"]


async def test_delete_email_permanent_ok():
    client = mock_client()
    client.set.return_value = {"destroyed": ["e1", "e2"]}
    result = await _tool(client, "mail_delete_email")(
        email_ids=["e1", "e2"], permanent=True
    )
    data = json.loads(result)
    assert data["destroyed"] == ["e1", "e2"]
    assert "notDestroyed" not in data
    client.set.assert_called_once_with("Email", destroy=["e1", "e2"])


async def test_delete_email_permanent_partial_failure():
    client = mock_client()
    client.set.return_value = {
        "destroyed": ["e1"],
        "notDestroyed": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_delete_email")(
        email_ids=["e1", "e2"], permanent=True
    )
    data = json.loads(result)
    assert data["destroyed"] == ["e1"]
    assert "e2" in data["notDestroyed"]


async def test_delete_email_trash_not_found():
    from pyfastmail_mcp.exceptions import MailboxNotFoundError

    client = mock_client()
    client.get_mailbox_by_role.side_effect = MailboxNotFoundError("No trash mailbox")
    result = await _tool(client, "mail_delete_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "trash" in data["error"].lower()


async def test_delete_email_client_error():
    client = mock_client()
    client.get_mailbox_by_role.side_effect = requests.RequestException("network error")
    result = await _tool(client, "mail_delete_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]


async def test_archive_email_ok():
    client = mock_client()
    client.get_mailbox_by_role.return_value = {"id": "arch1"}
    client.set.return_value = {"updated": {"e1": None, "e2": None}}
    result = await _tool(client, "mail_archive_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert set(data["archived"]) == {"e1", "e2"}
    assert data["mailboxId"] == "arch1"
    assert "notUpdated" not in data
    client.get_mailbox_by_role.assert_called_once_with("archive")
    client.set.assert_called_once_with(
        "Email",
        update={
            "e1": {"mailboxIds": {"arch1": True}},
            "e2": {"mailboxIds": {"arch1": True}},
        },
    )


async def test_archive_email_partial_failure():
    client = mock_client()
    client.get_mailbox_by_role.return_value = {"id": "arch1"}
    client.set.return_value = {
        "updated": {"e1": None},
        "notUpdated": {"e2": {"type": "notFound"}},
    }
    result = await _tool(client, "mail_archive_email")(email_ids=["e1", "e2"])
    data = json.loads(result)
    assert data["archived"] == ["e1"]
    assert "e2" in data["notUpdated"]


async def test_archive_email_mailbox_not_found():
    from pyfastmail_mcp.exceptions import MailboxNotFoundError

    client = mock_client()
    client.get_mailbox_by_role.side_effect = MailboxNotFoundError("No archive mailbox")
    result = await _tool(client, "mail_archive_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "archive" in data["error"].lower()


async def test_archive_email_client_error():
    client = mock_client()
    client.get_mailbox_by_role.side_effect = requests.RequestException("network error")
    result = await _tool(client, "mail_archive_email")(email_ids=["e1"])
    data = json.loads(result)
    assert "error" in data
    assert "network error" in data["error"]
