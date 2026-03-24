"""Tests for SSRF href validation in DAVClient and all DAV tools."""

import json
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import (
    CALDAV_BASE,
    CARDDAV_BASE,
    WEBDAV_BASE,
    DAVClient,
)

# ---------------------------------------------------------------------------
# DAVClient.validate_dav_url unit tests
# ---------------------------------------------------------------------------


def _real_client():
    return DAVClient(email="u@example.com", app_password="pw")


def test_validate_allows_carddav():
    _real_client().validate_dav_url(
        f"{CARDDAV_BASE}/dav/addressbooks/user/u@example.com/Default/"
    )


def test_validate_allows_caldav():
    _real_client().validate_dav_url(
        f"{CALDAV_BASE}/dav/calendars/user/u@example.com/Default/"
    )


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


def test_validate_rejects_userinfo():
    with pytest.raises(ValueError, match="not allowed"):
        _real_client().validate_dav_url(
            "https://user@carddav.fastmail.com/dav/addressbooks/"
        )


def test_validate_rejects_nonstandard_port():
    with pytest.raises(ValueError, match="not allowed"):
        _real_client().validate_dav_url("https://carddav.fastmail.com:8080/path")


# ---------------------------------------------------------------------------
# Helpers for tool-level tests
# ---------------------------------------------------------------------------


def _mock_client():
    c = MagicMock(spec=DAVClient)
    c.email = "u@example.com"
    c.carddav_principal_url.return_value = (
        f"{CARDDAV_BASE}/dav/principals/user/u@example.com/"
    )
    c.caldav_principal_url.return_value = (
        f"{CALDAV_BASE}/dav/principals/user/u@example.com/"
    )
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
    from pyfastmail_mcp.tools.calendar.caldav_get_event import register

    fn = _tool(_mock_client(), register, "calendar_get_event")
    result = json.loads(await fn(href=BAD_HREF))
    assert "error" in result


# ---------------------------------------------------------------------------
# calendar_create_event — caldav_write.py
# ---------------------------------------------------------------------------


async def test_calendar_create_event_rejects_bad_href():
    from pyfastmail_mcp.tools.calendar.caldav_write import register

    fn = _tool(_mock_client(), register, "calendar_create_event")
    result = json.loads(
        await fn(
            calendar_href=BAD_HREF,
            title="T",
            start="2026-01-01T10:00:00",
            end="2026-01-01T11:00:00",
        )
    )
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


# ---------------------------------------------------------------------------
# WebDAV tool SSRF validation — webdav.py / webdav_write.py
# ---------------------------------------------------------------------------


def _webdav_client():
    c = MagicMock(spec=DAVClient)
    real = _real_client()
    c.validate_dav_url.side_effect = real.validate_dav_url
    return c


async def test_files_list_calls_validate():
    import requests as _requests

    from pyfastmail_mcp.tools.files.webdav import register

    client = _webdav_client()
    resp = MagicMock(spec=_requests.Response)
    resp.text = "<D:multistatus xmlns:D='DAV:'></D:multistatus>"
    client.propfind.return_value = resp
    fn = _tool(client, register, "files_list")
    await fn(path="/docs")
    client.validate_dav_url.assert_called_once()


async def test_files_get_calls_validate():
    import requests as _requests

    from pyfastmail_mcp.tools.files.webdav import register

    client = _webdav_client()
    resp = MagicMock(spec=_requests.Response)
    resp.content = b"hello"
    resp.headers = {"Content-Type": "text/plain"}
    client.get.return_value = resp
    fn = _tool(client, register, "files_get")
    await fn(path="/notes.txt")
    client.validate_dav_url.assert_called_once()


async def test_files_upload_calls_validate():
    import base64

    from pyfastmail_mcp.tools.files.webdav_write import register

    client = _webdav_client()
    fn = _tool(client, register, "files_upload")
    await fn(path="/f.txt", content=base64.b64encode(b"hi").decode())
    client.validate_dav_url.assert_called_once()


async def test_files_create_folder_calls_validate():
    from pyfastmail_mcp.tools.files.webdav_write import register

    client = _webdav_client()
    fn = _tool(client, register, "files_create_folder")
    await fn(path="/NewFolder")
    client.validate_dav_url.assert_called_once()


async def test_files_delete_calls_validate():
    from pyfastmail_mcp.tools.files.webdav_write import register

    client = _webdav_client()
    fn = _tool(client, register, "files_delete")
    await fn(path="/old.txt")
    client.validate_dav_url.assert_called_once()


async def test_files_move_calls_validate_both_paths():
    from pyfastmail_mcp.tools.files.webdav_write import register

    client = _webdav_client()
    fn = _tool(client, register, "files_move")
    await fn(source="/a.txt", destination="/b.txt")
    assert client.validate_dav_url.call_count == 2
