"""Tests for contacts_update_contact and contacts_delete_contact tools."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.contacts.carddav_write import register


def _client():
    c = MagicMock()
    c.email = "user@example.com"
    return c


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(text: str = "", headers: dict | None = None):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


_HREF = "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/alice.vcf"
_REL_HREF = "/dav/addressbooks/user/user@example.com/Default/alice.vcf"

_VCARD = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-alice
FN:Alice Smith
EMAIL:alice@example.com
TEL:555-1234
ORG:Acme
NOTE:Old note
END:VCARD"""

# vCard with a structured N: field — triggers ValidateError if _apply_updates
# doesn't delete the existing n component before adding a new one.
_VCARD_WITH_N = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-alice
FN:Alice Smith
N:Smith;Alice;;;
EMAIL:alice@example.com
END:VCARD"""


# --- contacts_update_contact ---


@pytest.mark.asyncio
async def test_update_contact_name():
    """Updating name changes FN in the PUT body."""
    client = _client()
    client.get.return_value = _mock_response(_VCARD, {"ETag": '"abc"'})
    client.put.return_value = _mock_response()

    result = json.loads(
        await _tool(client, "contacts_update_contact")(href=_HREF, name="Alice Jones")
    )

    assert result["name"] == "Alice Jones"
    (
        _,
        vcard_body,
        _,
    ) = client.put.call_args[0]
    assert "Alice Jones" in vcard_body
    # ETag forwarded
    assert client.put.call_args[1].get("etag") == '"abc"' or '"abc"' in str(
        client.put.call_args
    )


@pytest.mark.asyncio
async def test_update_contact_name_with_existing_n_field():
    """Updating name on a vCard that already has N: must not raise ValidateError."""
    client = _client()
    client.get.return_value = _mock_response(_VCARD_WITH_N, {})
    client.put.return_value = _mock_response()

    result = json.loads(
        await _tool(client, "contacts_update_contact")(href=_HREF, name="Bob Jones")
    )

    assert result["name"] == "Bob Jones"
    _, vcard_body, _ = client.put.call_args[0]
    assert "Bob Jones" in vcard_body


@pytest.mark.asyncio
async def test_update_contact_email():
    """Updating email replaces the EMAIL field."""
    client = _client()
    client.get.return_value = _mock_response(_VCARD, {})
    client.put.return_value = _mock_response()

    result = json.loads(
        await _tool(client, "contacts_update_contact")(
            href=_HREF, email="new@example.com"
        )
    )

    assert "new@example.com" in result["emails"]
    _, vcard_body, _ = client.put.call_args[0]
    assert "new@example.com" in vcard_body


@pytest.mark.asyncio
async def test_update_contact_relative_href():
    """Relative href gets CARDDAV_BASE prepended for GET and PUT."""
    from pyfastmail_mcp.dav_client import CARDDAV_BASE

    client = _client()
    client.get.return_value = _mock_response(_VCARD, {})
    client.put.return_value = _mock_response()

    await _tool(client, "contacts_update_contact")(href=_REL_HREF, notes="Updated")

    client.get.assert_called_once_with(CARDDAV_BASE + _REL_HREF)
    put_url = client.put.call_args[0][0]
    assert put_url == CARDDAV_BASE + _REL_HREF


@pytest.mark.asyncio
async def test_update_contact_no_fields_changed():
    """Calling with no optional fields leaves vCard unchanged."""
    client = _client()
    client.get.return_value = _mock_response(_VCARD, {})
    client.put.return_value = _mock_response()

    result = json.loads(await _tool(client, "contacts_update_contact")(href=_HREF))

    assert result["name"] == "Alice Smith"
    assert result["emails"] == ["alice@example.com"]


@pytest.mark.asyncio
async def test_update_contact_get_error():
    """GET failure returns JSON error payload."""
    client = _client()
    client.get.side_effect = requests.RequestException("not found")

    result = json.loads(
        await _tool(client, "contacts_update_contact")(href=_HREF, name="X")
    )

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_update_contact_put_error():
    """PUT failure returns JSON error payload."""
    client = _client()
    client.get.return_value = _mock_response(_VCARD, {})
    client.put.side_effect = requests.RequestException("conflict")

    result = json.loads(
        await _tool(client, "contacts_update_contact")(href=_HREF, name="X")
    )

    assert "error" in result
    assert "conflict" in result["error"]


# --- contacts_delete_contact ---


@pytest.mark.asyncio
async def test_delete_contact_absolute_href():
    """Absolute href passed directly to dav_client.delete."""
    client = _client()
    client.delete.return_value = _mock_response()

    result = json.loads(await _tool(client, "contacts_delete_contact")(href=_HREF))

    client.delete.assert_called_once_with(_HREF)
    assert result["deleted"] == _HREF


@pytest.mark.asyncio
async def test_delete_contact_relative_href():
    """Relative href gets CARDDAV_BASE prepended."""
    from pyfastmail_mcp.dav_client import CARDDAV_BASE

    client = _client()
    client.delete.return_value = _mock_response()

    result = json.loads(await _tool(client, "contacts_delete_contact")(href=_REL_HREF))

    client.delete.assert_called_once_with(CARDDAV_BASE + _REL_HREF)
    assert result["deleted"] == _REL_HREF


@pytest.mark.asyncio
async def test_delete_contact_error():
    """DELETE failure returns JSON error payload."""
    client = _client()
    client.delete.side_effect = requests.RequestException("forbidden")

    result = json.loads(await _tool(client, "contacts_delete_contact")(href=_HREF))

    assert "error" in result
    assert "forbidden" in result["error"]
