"""CardDAV tools — contacts via CardDAV (RFC 6352)."""

import json
from xml.etree import ElementTree as ET

import requests
import vobject
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import CARDDAV_BASE, DAVClient, PROPFIND_ADDRESSBOOK
from pyfastmail_mcp.exceptions import FastmailError

_DAV_NS = "DAV:"
_CARD_NS = "urn:ietf:params:xml:ns:carddav"

_REPORT_ALL_CONTACTS = """<?xml version="1.0" encoding="UTF-8"?>
<C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:prop>
    <D:getetag/>
    <C:address-data/>
  </D:prop>
</C:addressbook-query>"""


def _tag(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _parse_address_books(xml_text: str, base_url: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    results = []
    for response in root.iter(_tag(_DAV_NS, "response")):
        href_el = response.find(_tag(_DAV_NS, "href"))
        href = href_el.text.strip() if href_el is not None and href_el.text else ""

        resourcetype = response.find(f".//{_tag(_DAV_NS, 'resourcetype')}")
        if resourcetype is None:
            continue
        if resourcetype.find(_tag(_CARD_NS, "addressbook")) is None:
            continue

        displayname_el = response.find(f".//{_tag(_DAV_NS, 'displayname')}")
        displayname = (
            displayname_el.text.strip()
            if displayname_el is not None and displayname_el.text
            else ""
        )

        desc_el = response.find(f".//{_tag(_CARD_NS, 'addressbook-description')}")
        description = (
            desc_el.text.strip()
            if desc_el is not None and desc_el.text
            else ""
        )

        results.append({"href": href, "displayname": displayname, "description": description})
    return results


def _parse_vcard(vcard_text: str, href: str) -> dict:
    v = vobject.readOne(vcard_text)
    uid = v.contents.get("uid", [None])[0]
    fn = v.contents.get("fn", [None])[0]
    org = v.contents.get("org", [None])[0]
    return {
        "id": uid.value if uid else href,
        "href": href,
        "name": fn.value if fn else "",
        "emails": [e.value for e in v.contents.get("email", [])],
        "phones": [t.value for t in v.contents.get("tel", [])],
        "org": org.value[0] if org and org.value else "",
    }


def _parse_contacts(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    results = []
    for response in root.iter(_tag(_DAV_NS, "response")):
        href_el = response.find(_tag(_DAV_NS, "href"))
        href = href_el.text.strip() if href_el is not None and href_el.text else ""
        addr_data_el = response.find(f".//{_tag(_CARD_NS, 'address-data')}")
        if addr_data_el is None or not addr_data_el.text:
            continue
        try:
            results.append(_parse_vcard(addr_data_el.text, href))
        except (FastmailError, requests.RequestException, ValueError):
            continue
    return results


def _parse_vcard_full(vcard_text: str, href: str) -> dict:
    v = vobject.readOne(vcard_text)
    uid = v.contents.get("uid", [None])[0]
    fn = v.contents.get("fn", [None])[0]
    org = v.contents.get("org", [None])[0]
    note = v.contents.get("note", [None])[0]
    return {
        "id": uid.value if uid else href,
        "href": href,
        "name": fn.value if fn else "",
        "emails": [e.value for e in v.contents.get("email", [])],
        "phones": [t.value for t in v.contents.get("tel", [])],
        "org": org.value[0] if org and org.value else "",
        "notes": note.value if note else "",
    }


def register(server: FastMCP, dav_client: DAVClient) -> None:
    @server.tool()
    async def contacts_list_address_books() -> str:
        """List all CardDAV address books for the authenticated Fastmail account."""
        try:
            principal_url = dav_client.carddav_principal_url()
            resp = dav_client.propfind(principal_url, depth="1", body=PROPFIND_ADDRESSBOOK)
            books = _parse_address_books(resp.text, principal_url)
            return json.dumps(books, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_get_contact(href: str) -> str:
        """Get full details of a single contact by its CardDAV href.

        Args:
            href: The href/URL path of the vCard resource (as returned by contacts_list).
        """
        try:
            url = href if href.startswith("http") else CARDDAV_BASE + href
            dav_client.validate_dav_url(url)
            resp = dav_client.get(url)
            contact = _parse_vcard_full(resp.text, href)
            return json.dumps(contact, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_list(address_book_href: str | None = None) -> str:
        """List contacts in a CardDAV address book.

        Args:
            address_book_href: URL path of the address book (e.g.
                /dav/addressbooks/user/you@example.com/Default/).
                Defaults to the first address book found.
        """
        try:
            if not address_book_href:
                principal_url = dav_client.carddav_principal_url()
                resp = dav_client.propfind(principal_url, depth="1", body=PROPFIND_ADDRESSBOOK)
                books = _parse_address_books(resp.text, principal_url)
                if not books:
                    return json.dumps([])
                address_book_href = books[0]["href"]

            base = address_book_href
            if not base.startswith("http"):
                base = CARDDAV_BASE + address_book_href

            dav_client.validate_dav_url(base)
            resp = dav_client.report(base, _REPORT_ALL_CONTACTS)
            contacts = _parse_contacts(resp.text)
            return json.dumps(contacts, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
