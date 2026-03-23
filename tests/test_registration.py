"""Tests for subpackage tool registration wiring."""

from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools import register_all
from pyfastmail_mcp.tools.mail import register_all as register_mail
from pyfastmail_mcp.tools.contacts import register_all as register_contacts


def _jmap_client():
    c = MagicMock()
    c.account_id = "acc1"
    return c


def _dav_client():
    c = MagicMock()
    c.email = "user@example.com"
    return c


EXPECTED_MAIL_TOOLS = {
    "health_check",
    "mail_list_mailboxes",
    "mail_create_mailbox",
    "mail_rename_mailbox",
    "mail_delete_mailbox",
    "mail_get_email",
    "mail_search_emails",
    "mail_get_recent_emails",
    "mail_get_email_thread",
    "mail_mark_email_read",
    "mail_move_email",
    "mail_delete_email",
    "mail_archive_email",
    "mail_list_identities",
    "mail_send_email",
    "mail_reply_to_email",
    "mail_forward_email",
    "mail_manage_email_labels",
    "mail_list_masked_emails",
    "mail_create_masked_email",
    "mail_update_masked_email_state",
    "mail_download_attachment",
    "mail_upload_attachment",
}

EXPECTED_CONTACTS_TOOLS = {
    "contacts_list_address_books",
    "contacts_list",
    "contacts_get_contact",
    "contacts_create_contact",
    "contacts_update_contact",
    "contacts_delete_contact",
}


def test_mail_register_all_registers_expected_tools():
    server = FastMCP("test")
    register_mail(server, _jmap_client())
    registered = set(server._tool_manager._tools.keys())
    assert EXPECTED_MAIL_TOOLS == registered


def test_contacts_register_all_registers_expected_tools():
    server = FastMCP("test")
    register_contacts(server, _dav_client())
    registered = set(server._tool_manager._tools.keys())
    assert EXPECTED_CONTACTS_TOOLS == registered


EXPECTED_CALENDAR_TOOLS = {
    "calendar_list_calendars",
    "calendar_list_events",
    "calendar_get_event",
    "calendar_create_event",
    "calendar_update_event",
    "calendar_delete_event",
}

EXPECTED_FILES_TOOLS = {
    "files_list",
    "files_get",
    "files_upload",
    "files_create_folder",
    "files_delete",
    "files_move",
}


def test_register_all_combines_all_subpackages():
    server = FastMCP("test")
    register_all(server, _jmap_client(), _dav_client())
    registered = set(server._tool_manager._tools.keys())
    expected = (
        EXPECTED_MAIL_TOOLS
        | EXPECTED_CONTACTS_TOOLS
        | EXPECTED_CALENDAR_TOOLS
        | EXPECTED_FILES_TOOLS
    )
    assert expected == registered
