"""CardDAV write tools — create, update, delete contacts."""

import json
import uuid
from urllib.parse import quote

import requests
import vobject
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import CARDDAV_BASE, PROPFIND_ADDRESSBOOK, DAVClient
from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.contacts.carddav import (
    _parse_address_books,
    _parse_vcard_full,
)


def _build_vcard(
    name: str,
    email: str | None,
    phone: str | None,
    org: str | None,
    notes: str | None,
    uid: str,
) -> str:
    v = vobject.vCard()
    v.add("uid").value = uid
    v.add("fn").value = name
    # Structured name: split on first space for given/family
    parts = name.split(" ", 1)
    n = v.add("n")
    n.value = vobject.vcard.Name(
        family=parts[-1] if len(parts) > 1 else "",
        given=parts[0],
    )
    if email:
        v.add("email").value = email
    if phone:
        v.add("tel").value = phone
    if org:
        v.add("org").value = [org]
    if notes:
        v.add("note").value = notes
    return v.serialize()


def _default_address_book(dav_client: DAVClient) -> str:
    home_url = dav_client.discover_carddav_home()
    dav_client.validate_dav_url(home_url)
    resp = dav_client.propfind(home_url, depth="1", body=PROPFIND_ADDRESSBOOK)
    books = _parse_address_books(resp.text, home_url)
    if not books:
        raise ValueError("No address books found")
    return books[0]["href"]


def _apply_updates(v: vobject.vCard, **fields) -> None:
    """Overwrite vCard fields that are explicitly provided (non-None)."""
    mapping = {
        "name": "fn",
        "email": "email",
        "phone": "tel",
        "org": "org",
        "notes": "note",
    }
    for field, component in mapping.items():
        if fields.get(field) is None:
            continue
        value = fields[field]
        # Remove existing
        if component in v.contents:
            del v.contents[component]
        if field == "name":
            if "n" in v.contents:
                del v.contents["n"]
            v.add("fn").value = value
            n = v.add("n")
            parts = value.split(" ", 1)
            n.value = vobject.vcard.Name(
                family=parts[-1] if len(parts) > 1 else "",
                given=parts[0],
            )
        elif field == "org":
            v.add("org").value = [value]
        else:
            v.add(component).value = value


def register(server: FastMCP, dav_client: DAVClient) -> None:
    @server.tool()
    async def contacts_create_contact(
        name: str,
        email: str | None = None,
        phone: str | None = None,
        org: str | None = None,
        notes: str | None = None,
        address_book_href: str | None = None,
    ) -> str:
        """Create a new contact in a CardDAV address book.

        Args:
            name: Full display name of the contact.
            email: Email address (optional).
            phone: Phone number (optional).
            org: Organization/company name (optional).
            notes: Free-text notes (optional).
            address_book_href: URL path of the address book. Defaults to the first one found.
        """
        try:
            if not address_book_href:
                address_book_href = _default_address_book(dav_client)

            uid = str(uuid.uuid4())
            vcard_text = _build_vcard(name, email, phone, org, notes, uid)

            base = address_book_href
            if not base.startswith("http"):
                base = CARDDAV_BASE + address_book_href
            if not base.endswith("/"):
                base += "/"

            url = f"{base}{quote(uid, safe='')}.vcf"
            dav_client.validate_dav_url(url)
            dav_client.put(url, vcard_text, "text/vcard")

            # Fetch back to confirm and return full contact
            resp = dav_client.get(url)
            contact = _parse_vcard_full(resp.text, url)
            return json.dumps(contact, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_update_contact(
        href: str,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        org: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Update an existing contact in a CardDAV address book.

        Only the fields you provide will be changed; omitted fields are left as-is.

        Args:
            href: The href/URL path of the vCard resource (as returned by contacts_list).
            name: New display name (optional).
            email: New email address (optional).
            phone: New phone number (optional).
            org: New organisation name (optional).
            notes: New notes (optional).
        """
        try:
            url = href if href.startswith("http") else CARDDAV_BASE + href
            dav_client.validate_dav_url(url)
            get_resp = dav_client.get(url)
            etag = get_resp.headers.get("ETag")
            v = vobject.readOne(get_resp.text)
            _apply_updates(v, name=name, email=email, phone=phone, org=org, notes=notes)
            dav_client.put(url, v.serialize(), "text/vcard", etag=etag)
            updated = _parse_vcard_full(v.serialize(), href)
            return json.dumps(updated, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_delete_contact(href: str) -> str:
        """Delete a contact from a CardDAV address book.

        Args:
            href: The href/URL path of the vCard resource (as returned by contacts_list).
        """
        try:
            url = href if href.startswith("http") else CARDDAV_BASE + href
            dav_client.validate_dav_url(url)
            dav_client.delete(url)
            return json.dumps({"deleted": href})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
