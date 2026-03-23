"""Tests for SSRF href validation in DAVClient and all DAV tools."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import (
    CARDDAV_BASE,
    CALDAV_BASE,
    WEBDAV_BASE,
    DAVClient,
)


# ---------------------------------------------------------------------------
# DAVClient.validate_dav_url unit tests
# ---------------------------------------------------------------------------

def _real_client():
    return DAVClient(email="u@example.com", app_password="pw")


def test_validate_allows_carddav():
    _real_client().validate_dav_url(f"{CARDDAV_BASE}/dav/addressbooks/user/u@example.com/Default/")


def test_validate_allows_caldav():
    _real_client().validate_dav_url(f"{CALDAV_BASE}/dav/calendars/user/u@example.com/Default/")


def test_validate_allows_webdav():
    _real_client().validate_dav_url(f"{WEBDAV_BASE}/Documents/file.txt")


def test_validate_rejects_external_url():
    with pytest.raises(ValueError, match="not allowed"):
        _real_client().validate_dav_url("https://evil.example.com/steal")


def test_validate_rejects_empty_string():
    with pytest.raises(ValueError, match="not allowed"):
        _real_client().validate_dav_url("")


def test_validate_rejects_lookalike():
    with pytest.raises(ValueError, match="not allowed"):
        _real_client().validate_dav_url("https://carddav.fastmail.com.evil.com/path")


# ---------------------------------------------------------------------------
# Helpers for tool-level tests
# ---------------------------------------------------------------------------

def _mock_client():
    c = MagicMock(spec=DAVClient)
    c.email = "u@example.com"
    c.carddav_principal_url.return_value = f"{CARDDAV_BASE}/dav/principals/user/u@example.com/"
    c.caldav_principal_url.return_value = f"{CALDAV_BASE}/dav/principals/user/u@example.com/"
    # validate_dav_url should use the real implementation
    real = _real_client()
    c.validate_dav_url.side_effect = real.validate_dav_url
    return c


def _tool(client, module_register, name):
    server = FastMCP("test")
    module_register(server, client)
    return server._tool_manager._tools[name].fn


BAD_HREF = "https://evil.example.com/steal"


# ---------------------------------------------------------------------------
# contacts_get_contact — carddav.py
# ---------------------------------------------------------------------------

async def test_contacts_get_contact_rejects_bad_href():
    from pyfastmail_mcp.tools.contacts.carddav import register
    fn = _tool(_mock_client(), register, "contacts_get_contact")
    result = json.loads(await fn(href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# contacts_list — carddav.py
# ---------------------------------------------------------------------------

async def test_contacts_list_rejects_bad_href():
    from pyfastmail_mcp.tools.contacts.carddav import register
    fn = _tool(_mock_client(), register, "contacts_list")
    result = json.loads(await fn(address_book_href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# contacts_create_contact — carddav_write.py
# ---------------------------------------------------------------------------

async def test_contacts_create_rejects_bad_href():
    from pyfastmail_mcp.tools.contacts.carddav_write import register
    fn = _tool(_mock_client(), register, "contacts_create_contact")
    result = json.loads(await fn(name="Test", address_book_href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# contacts_update_contact — carddav_write.py
# ---------------------------------------------------------------------------

async def test_contacts_update_rejects_bad_href():
    from pyfastmail_mcp.tools.contacts.carddav_write import register
    fn = _tool(_mock_client(), register, "contacts_update_contact")
    result = json.loads(await fn(href=BAD_HREF, name="New Name"))
    assert "error" in result


# ---------------------------------------------------------------------------
# contacts_delete_contact — carddav_write.py
# ---------------------------------------------------------------------------

async def test_contacts_delete_rejects_bad_href():
    from pyfastmail_mcp.tools.contacts.carddav_write import register
    fn = _tool(_mock_client(), register, "contacts_delete_contact")
    result = json.loads(await fn(href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_list_events — caldav.py
# ---------------------------------------------------------------------------

async def test_calendar_list_events_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav import register
    fn = _tool(_mock_client(), register, "calendar_list_events")
    result = json.loads(await fn(calendar_href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_get_event — caldav.py
# ---------------------------------------------------------------------------

async def test_calendar_get_event_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav import register
    fn = _tool(_mock_client(), register, "calendar_get_event")
    result = json.loads(await fn(href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_create_event — caldav_write.py
# ---------------------------------------------------------------------------

async def test_calendar_create_event_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav_write import register
    fn = _tool(_mock_client(), register, "calendar_create_event")
    result = json.loads(await fn(
        calendar_href=BAD_HREF,
        title="T",
        start="2026-01-01T10:00:00",
        end="2026-01-01T11:00:00",
    ))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_update_event — caldav_write.py
# ---------------------------------------------------------------------------

async def test_calendar_update_event_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav_write import register
    fn = _tool(_mock_client(), register, "calendar_update_event")
    result = json.loads(await fn(href=BAD_HREF, title="New"))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_delete_event — caldav_write.py
# ---------------------------------------------------------------------------

async def test_calendar_delete_event_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav_write import register
    fn = _tool(_mock_client(), register, "calendar_delete_event")
    result = json.loads(await fn(href=BAD_HREF))
    assert "error" in result
