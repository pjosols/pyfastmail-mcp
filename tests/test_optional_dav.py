"""Tests for optional DAV credentials — DAVClient.available flag and conditional registration."""

import os
from unittest.mock import MagicMock, patch

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import DAVClient
from pyfastmail_mcp.tools import register_all


def _jmap_client():
    c = MagicMock()
    c.account_id = "acc1"
    return c


# --- DAVClient.available ---


def test_dav_client_available_when_both_creds_provided():
    client = DAVClient(email="user@example.com", app_password="secret")
    assert client.available is True
    assert client._http is not None


def test_dav_client_unavailable_when_no_email():
    client = DAVClient(email="", app_password="secret")
    assert client.available is False
    assert client._http is None


def test_dav_client_unavailable_when_no_password():
    client = DAVClient(email="user@example.com", app_password="")
    assert client.available is False
    assert client._http is None


def test_dav_client_unavailable_when_no_creds():
    client = DAVClient(email="", app_password="")
    assert client.available is False
    assert client._http is None


def test_dav_client_reads_creds_from_env():
    with patch.dict(
        os.environ,
        {"FASTMAIL_EMAIL": "env@example.com", "FASTMAIL_APP_PASSWORD": "envpass"},
    ):
        client = DAVClient()
    assert client.available is True


def test_dav_client_unavailable_when_env_missing():
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("FASTMAIL_EMAIL", "FASTMAIL_APP_PASSWORD")
    }
    with patch.dict(os.environ, env, clear=True):
        client = DAVClient()
    assert client.available is False


# --- register_all conditional registration ---

CALENDAR_TOOLS = {
    "calendar_list_calendars",
    "calendar_list_events",
    "calendar_get_event",
    "calendar_create_event",
    "calendar_update_event",
    "calendar_delete_event",
}
FILES_TOOLS = {
    "files_list",
    "files_get",
    "files_upload",
    "files_create_folder",
    "files_delete",
    "files_move",
}


def test_register_all_skips_calendar_and_files_when_dav_unavailable():
    dav = MagicMock()
    dav.available = False
    server = FastMCP("test")
    register_all(server, _jmap_client(), dav)
    registered = set(server._tool_manager._tools.keys())
    assert not (CALENDAR_TOOLS & registered)
    assert not (FILES_TOOLS & registered)


def test_register_all_includes_calendar_and_files_when_dav_available():
    dav = MagicMock()
    dav.available = True
    server = FastMCP("test")
    register_all(server, _jmap_client(), dav)
    registered = set(server._tool_manager._tools.keys())
    assert CALENDAR_TOOLS <= registered
    assert FILES_TOOLS <= registered


def test_register_all_mail_and_contacts_always_registered():
    dav = MagicMock()
    dav.available = False
    server = FastMCP("test")
    register_all(server, _jmap_client(), dav)
    registered = set(server._tool_manager._tools.keys())
    assert "health_check" in registered
    assert "mail_send_email" in registered
    assert "contacts_list_address_books" in registered
