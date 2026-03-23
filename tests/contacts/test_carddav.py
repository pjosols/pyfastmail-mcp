"""Tests for tools/contacts/carddav.py — contacts_list_address_books, contacts_list."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.contacts.carddav import register


def _client():
    c = MagicMock()
    c.email = "user@example.com"
    c.discover_carddav_home.return_value = (
        "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/"
    )
    return c


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(xml_text: str):
    resp = MagicMock(spec=requests.Response)
    resp.text = xml_text
    resp.raise_for_status = MagicMock()
    return resp


_XML_TWO_BOOKS = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype><D:principal/></D:resourcetype>
        <D:displayname>user@example.com</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/dav/addressbooks/user/user@example.com/Default/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
          <C:addressbook/>
        </D:resourcetype>
        <D:displayname>Personal</D:displayname>
        <C:addressbook-description>My contacts</C:addressbook-description>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/dav/addressbooks/user/user@example.com/Work/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
          <C:addressbook/>
        </D:resourcetype>
        <D:displayname>Work</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

_XML_EMPTY = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype><D:principal/></D:resourcetype>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


@pytest.mark.asyncio
async def test_list_address_books_ok():
    client = _client()
    client.propfind.return_value = _mock_response(_XML_TWO_BOOKS)
    result = json.loads(await _tool(client, "contacts_list_address_books")())
    client.discover_carddav_home.assert_called_once()
    assert len(result) == 2
    assert result[0]["displayname"] == "Personal"
    assert result[0]["description"] == "My contacts"
    assert result[1]["displayname"] == "Work"
    assert result[1]["description"] == ""


@pytest.mark.asyncio
async def test_list_address_books_empty():
    client = _client()
    client.propfind.return_value = _mock_response(_XML_EMPTY)
    result = json.loads(await _tool(client, "contacts_list_address_books")())
    assert result == []


@pytest.mark.asyncio
async def test_list_address_books_error():
    client = _client()
    client.discover_carddav_home.side_effect = requests.RequestException(
        "connection refused"
    )
    result = json.loads(await _tool(client, "contacts_list_address_books")())
    assert "error" in result
    assert "connection refused" in result["error"]


# --- contacts_list ---

_XML_CONTACTS = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:response>
    <D:href>/dav/addressbooks/user/user@example.com/Default/alice.vcf</D:href>
    <D:propstat>
      <D:prop>
        <C:address-data>BEGIN:VCARD
VERSION:3.0
UID:uid-alice
FN:Alice Smith
EMAIL:alice@example.com
TEL:555-1234
ORG:Acme
END:VCARD</C:address-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/dav/addressbooks/user/user@example.com/Default/bob.vcf</D:href>
    <D:propstat>
      <D:prop>
        <C:address-data>BEGIN:VCARD
VERSION:3.0
UID:uid-bob
FN:Bob Jones
EMAIL:bob@example.com
END:VCARD</C:address-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

_XML_NO_CONTACTS = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
</D:multistatus>"""


@pytest.mark.asyncio
async def test_list_contacts_explicit_href():
    client = _client()
    client.report.return_value = _mock_response(_XML_CONTACTS)
    result = json.loads(
        await _tool(client, "contacts_list")(
            address_book_href="https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/"
        )
    )
    assert len(result) == 2
    assert result[0]["id"] == "uid-alice"
    assert result[0]["name"] == "Alice Smith"
    assert result[0]["emails"] == ["alice@example.com"]
    assert result[0]["phones"] == ["555-1234"]
    assert result[0]["org"] == "Acme"
    assert result[1]["id"] == "uid-bob"
    assert result[1]["emails"] == ["bob@example.com"]
    assert result[1]["phones"] == []


@pytest.mark.asyncio
async def test_list_contacts_auto_discover():
    client = _client()
    client.propfind.return_value = _mock_response(_XML_TWO_BOOKS)
    client.report.return_value = _mock_response(_XML_CONTACTS)
    result = json.loads(await _tool(client, "contacts_list")())
    client.discover_carddav_home.assert_called_once()
    assert len(result) == 2
    called_url = client.report.call_args[0][0]
    assert "Default" in called_url


@pytest.mark.asyncio
async def test_list_contacts_auto_discover_no_books():
    client = _client()
    client.propfind.return_value = _mock_response(_XML_EMPTY)
    result = json.loads(await _tool(client, "contacts_list")())
    client.discover_carddav_home.assert_called_once()
    assert result == []


@pytest.mark.asyncio
async def test_list_contacts_empty_book():
    client = _client()
    client.report.return_value = _mock_response(_XML_NO_CONTACTS)
    result = json.loads(
        await _tool(client, "contacts_list")(
            address_book_href="https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/"
        )
    )
    assert result == []


@pytest.mark.asyncio
async def test_list_contacts_error():
    client = _client()
    client.report.side_effect = requests.RequestException("timeout")
    result = json.loads(
        await _tool(client, "contacts_list")(
            address_book_href="https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/Default/"
        )
    )
    assert "error" in result
    assert "timeout" in result["error"]
