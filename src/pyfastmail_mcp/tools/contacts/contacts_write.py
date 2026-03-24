"""Contacts write tools (JMAP)."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_CONTACTS, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError


def _build_card(
    name: str | None,
    emails: list[str] | None,
    phones: list[str] | None,
    org: str | None,
    notes: str | None,
    address_book_ids: list[str] | None,
) -> dict:
    """Build a minimal JSContact Card dict (RFC 9553)."""
    card: dict = {"@type": "Card", "version": "1.0"}
    if name:
        card["name"] = {"full": name}
    if emails:
        card["emails"] = {f"e{i}": {"address": e} for i, e in enumerate(emails)}
    if phones:
        card["phones"] = {f"p{i}": {"number": p} for i, p in enumerate(phones)}
    if org:
        card["organizations"] = {"o0": {"name": org}}
    if notes:
        card["notes"] = {"n0": {"note": notes}}
    if address_book_ids:
        card["addressBookIds"] = {ab: True for ab in address_book_ids}
    return card


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def contacts_update_contact(
        contact_id: str,
        name: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        org: str | None = None,
        notes: str | None = None,
        address_book_ids: list[str] | None = None,
    ) -> str:
        """Update an existing contact card via JSON patch.

        Only the fields you provide will be changed; omitted fields are left as-is.

        Args:
            contact_id: ID of the ContactCard to update.
            name: New full display name.
            emails: Replace all email addresses with this list.
            phones: Replace all phone numbers with this list.
            org: Replace organization name.
            notes: Replace notes.
            address_book_ids: Replace address book membership.
        """
        try:
            patch: dict = {}
            if name is not None:
                patch["name/full"] = name
            if emails is not None:
                patch["emails"] = {
                    f"e{i}": {"address": e} for i, e in enumerate(emails)
                }
            if phones is not None:
                patch["phones"] = {f"p{i}": {"number": p} for i, p in enumerate(phones)}
            if org is not None:
                patch["organizations"] = {"o0": {"name": org}}
            if notes is not None:
                patch["notes"] = {"n0": {"note": notes}}
            if address_book_ids is not None:
                patch["addressBookIds"] = {ab: True for ab in address_book_ids}

            if not patch:
                return json.dumps({"error": "No fields to update"})

            data = client.set(
                "ContactCard",
                update={contact_id: patch},
                using=USING_CONTACTS,
            )
            if data.get("updated") and contact_id in data["updated"]:
                return json.dumps({"updated": contact_id})
            if data.get("notUpdated") and contact_id in data["notUpdated"]:
                err = data["notUpdated"][contact_id]
                return json.dumps(
                    {"error": err.get("description", err.get("type", "unknown"))}
                )
            return json.dumps({"error": "No response from server"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_delete_contact(contact_ids: list[str]) -> str:
        """Delete one or more contacts by ID.

        Args:
            contact_ids: List of ContactCard IDs to delete.
        """
        try:
            data = client.set(
                "ContactCard",
                destroy=contact_ids,
                using=USING_CONTACTS,
            )
            result: dict = {}
            if data.get("destroyed"):
                result["destroyed"] = data["destroyed"]
            if data.get("notDestroyed"):
                result["errors"] = {
                    k: v.get("description", v.get("type", "unknown"))
                    for k, v in data["notDestroyed"].items()
                }
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_create_contact(
        name: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        org: str | None = None,
        notes: str | None = None,
        address_book_ids: list[str] | None = None,
    ) -> str:
        """Create a new contact card.

        Args:
            name: Full display name of the contact.
            emails: List of email addresses.
            phones: List of phone numbers.
            org: Organization / company name.
            notes: Free-text notes.
            address_book_ids: Address book IDs to add the contact to.
        """
        try:
            card = _build_card(name, emails, phones, org, notes, address_book_ids)
            data = client.set(
                "ContactCard",
                create={"new": card},
                using=USING_CONTACTS,
            )
            if data.get("created"):
                return json.dumps(data["created"].get("new", data["created"]), indent=2)
            if data.get("notCreated"):
                err = data["notCreated"].get("new", {})
                return json.dumps(
                    {"error": err.get("description", err.get("type", "unknown"))}
                )
            return json.dumps({"error": "No response from server"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
