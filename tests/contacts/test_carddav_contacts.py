"""Tests for contacts_get_contact and contacts_create_contact tools."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.contacts.carddav import register as register_read
from pyfastmail_mcp.tools.contacts.carddav_write import register as register_write


def _client():
    c = MagicMock()
    c.email = "user@example.com"
    return c


def _read_tool(client, name):
    server = FastMCP("test")
    register_read(server, client)
    return server._tool_manager._tools[name].fn


def _write_tool(client, name):
    server = FastMCP("test")
    register_write(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(text: str):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


_VCARD_FULL = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-alice
FN:Alice Smith
EMAIL:alice@example.com
TEL:555-1234
ORG:Acme
NOTE:Test note
END:VCARD"""

_VCARD_MINIMAL = """\
BEGIN:VCARD
VERSION:3.0
FN:Bob Jones
END:VCARD"""


@pytest.mark.asyncio
async def test_get_contact_full_href():
    """Full href (absolute URL) — dav_client.get called with it directly."""
    client = _client()
    href = "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/alice.vcf"
    client.get.return_value = _mock_response(_VCARD_FULL)

    result = json.loads(await _read_tool(client, "contacts_get_contact")(href=href))
    assert result["id"] == "uid-alice"
    assert result["name"] == "Alice Smith"
    assert result["emails"] == ["alice@example.com"]
    assert result["phones"] == ["555-1234"]
    assert result["org"] == "Acme"
    assert result["notes"] == "Test note"
    assert result["href"] == href


@pytest.mark.asyncio
async def test_get_contact_relative_href():
    """Relative href — CARDDAV_BASE is prepended for the GET call."""
    from pyfastmail_mcp.dav_client import CARDDAV_BASE

    client = _client()
    href = "/dav/addressbooks/user/user@example.com/Default/alice.vcf"
    client.get.return_value = _mock_response(_VCARD_FULL)

    result = json.loads(await _read_tool(client, "contacts_get_contact")(href=href))

    client.get.assert_called_once_with(CARDDAV_BASE + href)
    assert result["id"] == "uid-alice"
    assert result["href"] == href


@pytest.mark.asyncio
async def test_get_contact_minimal_vcard():
    """vCard with no UID, email, phone, org, or notes — defaults to empty strings/lists."""
    client = _client()
    href = "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/bob.vcf"
    client.get.return_value = _mock_response(_VCARD_MINIMAL)

    result = json.loads(await _read_tool(client, "contacts_get_contact")(href=href))

    assert result["id"] == href  # falls back to href when no UID
    assert result["name"] == "Bob Jones"
    assert result["emails"] == []
    assert result["phones"] == []
    assert result["org"] == ""
    assert result["notes"] == ""


@pytest.mark.asyncio
async def test_get_contact_error():
    """Network error returns JSON error payload."""
    client = _client()
    client.get.side_effect = requests.RequestException("not found")

    result = json.loads(
        await _read_tool(client, "contacts_get_contact")(
            href="https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/missing.vcf"
        )
    )

    assert "error" in result
    assert "not found" in result["error"]


# --- contacts_create_contact ---

_AB_HREF = "/dav/addressbooks/user/user@example.com/Default/"
_AB_HREF_ABS = "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/"


@pytest.mark.asyncio
async def test_create_contact_success():
    """PUT is called with a URL containing the generated UID; returns full contact."""
    client = _client()
    client.put.return_value = _mock_response("")
    client.get.return_value = _mock_response(_VCARD_FULL)

    result = json.loads(
        await _write_tool(client, "contacts_create_contact")(
            address_book_href=_AB_HREF_ABS,
            name="Alice Smith",
            email="alice@example.com",
            phone="555-1234",
            org="Acme",
            notes="A note",
        )
    )

    client.put.assert_called_once()
    url_arg, vcard_arg, ct_arg = client.put.call_args[0]
    assert url_arg.startswith(_AB_HREF_ABS)
    assert url_arg.endswith(".vcf")
    assert "Alice Smith" in vcard_arg
    assert "alice@example.com" in vcard_arg
    assert "text/vcard" in ct_arg
    assert result["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_create_contact_relative_href():
    """Relative address_book_href gets CARDDAV_BASE prepended."""
    from pyfastmail_mcp.dav_client import CARDDAV_BASE

    client = _client()
    client.put.return_value = _mock_response("")
    client.get.return_value = _mock_response(_VCARD_FULL)

    await _write_tool(client, "contacts_create_contact")(
        address_book_href=_AB_HREF,
        name="Bob Jones",
    )

    url_arg = client.put.call_args[0][0]
    assert url_arg.startswith(CARDDAV_BASE)
    assert url_arg.endswith(".vcf")


@pytest.mark.asyncio
async def test_create_contact_minimal():
    """Only name is required; optional fields absent from vCard."""
    client = _client()
    client.put.return_value = _mock_response("")
    client.get.return_value = _mock_response(_VCARD_MINIMAL)

    result = json.loads(
        await _write_tool(client, "contacts_create_contact")(
            address_book_href=_AB_HREF_ABS,
            name="Minimal Person",
        )
    )

    _, vcard_arg, _ = client.put.call_args[0]
    assert "Minimal Person" in vcard_arg
    assert "EMAIL" not in vcard_arg.upper()


@pytest.mark.asyncio
async def test_create_contact_error():
    """PUT failure returns JSON error payload."""
    client = _client()
    client.put.side_effect = requests.RequestException("server error")

    result = json.loads(
        await _write_tool(client, "contacts_create_contact")(
            address_book_href=_AB_HREF_ABS,
            name="Fail Person",
        )
    )

    assert "error" in result
    assert "server error" in result["error"]
