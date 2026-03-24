"""Contacts read tools (JMAP)."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_CONTACTS, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_AB_PROPS = ["id", "name", "description", "sortOrder", "isDefault", "isSubscribed"]

_CARD_PROPS = [
    "id",
    "addressBookIds",
    "name",
    "emails",
    "phones",
    "addresses",
    "organizations",
    "notes",
]


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def contacts_list_address_books() -> str:
        """List all address books with id, name, description, sortOrder, isDefault, and isSubscribed."""
        try:
            responses = client.call(
                USING_CONTACTS,
                [
                    [
                        "AddressBook/get",
                        {
                            "accountId": client.account_id,
                            "ids": None,
                            "properties": _AB_PROPS,
                        },
                        "a",
                    ]
                ],
            )
            _, data, _ = responses[0]
            return json.dumps(data.get("list", []), indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_query_contacts(
        address_book_id: str | None = None,
        text: str | None = None,
        kind: str | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
    ) -> str:
        """Query contacts with optional filters and sorting.

        Args:
            address_book_id: Filter to contacts in this address book.
            text: Full-text search across name, email, phone, etc.
            kind: Filter by kind (e.g. "individual", "org", "group").
            limit: Maximum number of results to return.
            sort_by: Sort field — one of "name/given", "name/surname", "created", "updated".
        """
        try:
            filter_: dict | None = None
            conditions: dict = {}
            if address_book_id:
                conditions["inAddressBook"] = address_book_id
            if text:
                conditions["text"] = text
            if kind:
                conditions["kind"] = kind
            if conditions:
                filter_ = conditions

            sort: list[dict] | None = None
            if sort_by:
                sort = [{"property": sort_by}]

            results = client.query_and_get(
                "ContactCard",
                filter_,
                _CARD_PROPS,
                using=USING_CONTACTS,
                sort=sort,
                limit=limit,
            )
            return json.dumps(results, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_list(
        address_book_id: str | None = None,
        text: str | None = None,
        limit: int | None = None,
    ) -> str:
        """List contacts, optionally filtered by address book or text search.

        Uses a single round trip (ContactCard/query + ContactCard/get).

        Args:
            address_book_id: Restrict to contacts in this address book.
            text: Full-text search across name, email, phone, etc.
            limit: Maximum number of contacts to return.
        """
        try:
            filter_: dict | None = None
            conditions: dict = {}
            if address_book_id:
                conditions["inAddressBook"] = address_book_id
            if text:
                conditions["text"] = text
            if conditions:
                filter_ = conditions

            results = client.query_and_get(
                "ContactCard",
                filter_,
                _CARD_PROPS,
                using=USING_CONTACTS,
                limit=limit,
            )
            return json.dumps(results, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def contacts_get_contact(ids: list[str]) -> str:
        """Fetch full contact card(s) by ID.

        Returns id, addressBookIds, name, emails, phones, addresses, organizations, and notes.

        Args:
            ids: One or more ContactCard IDs to fetch.
        """
        try:
            responses = client.call(
                USING_CONTACTS,
                [
                    [
                        "ContactCard/get",
                        {
                            "accountId": client.account_id,
                            "ids": ids,
                            "properties": _CARD_PROPS,
                        },
                        "g",
                    ]
                ],
            )
            _, data, _ = responses[0]
            result: dict = {"list": data.get("list", [])}
            if data.get("notFound"):
                result["notFound"] = data["notFound"]
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
