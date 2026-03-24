"""Masked email management tools."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MASKED_EMAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_list_masked_emails(
        domain: str | None = None,
        state: str | None = None,
    ) -> str:
        """List masked email addresses, optionally filtered by domain or state.

        Args:
            domain: Filter by forDomain (partial match).
            state: Filter by state: 'enabled', 'disabled', 'deleted', 'pending'.
                   'pending' addresses auto-enable on first received message and
                   auto-delete after 24 hours if no message is received.
        """
        try:
            account_id = client.account_id
            responses = client.call(
                USING_MASKED_EMAIL,
                [["MaskedEmail/get", {"accountId": account_id, "ids": None}, "g"]],
            )
            _, data, _ = responses[0]
            items = data.get("list", [])
            if domain:
                items = [
                    m
                    for m in items
                    if domain.lower() in (m.get("forDomain") or "").lower()
                ]
            if state:
                items = [m for m in items if m.get("state") == state]
            result = [
                {
                    "id": m.get("id"),
                    "email": m.get("email"),
                    "state": m.get("state"),
                    "forDomain": m.get("forDomain"),
                    "description": m.get("description"),
                    "url": m.get("url"),
                    "createdBy": m.get("createdBy"),
                    "lastMessageAt": m.get("lastMessageAt"),
                    "createdAt": m.get("createdAt"),
                }
                for m in items
            ]
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_create_masked_email(
        for_domain: str = "",
        description: str = "",
        email_prefix: str | None = None,
        url: str | None = None,
    ) -> str:
        """Create a new masked email address.

        Args:
            for_domain: Origin of the site this address is for, e.g. 'https://example.com'.
                        Should be origin only — no path component.
            description: Short user-supplied description of what this address is for.
            email_prefix: Optional prefix for the generated address (a-z, 0-9, _ only).
            url: Optional deep link back to the integrator (e.g. sign-up page URL).
                 'createdBy' is set server-side from auth credentials; do not try to set it.
        """
        try:
            create_obj: dict = {
                "state": "enabled",
                "forDomain": for_domain,
                "description": description,
            }
            if email_prefix:
                create_obj["emailPrefix"] = email_prefix
            if url:
                create_obj["url"] = url
            data = client.set(
                "MaskedEmail",
                create={"new": create_obj},
                using=USING_MASKED_EMAIL,
            )
            created = (data.get("created") or {}).get("new")
            if not created:
                not_created = data.get("notCreated") or {}
                err = not_created.get("new", {})
                if err.get("type") == "rateLimit":
                    return json.dumps({"error": "Rate limit reached; try again later"})
                return json.dumps({"error": err.get("description", "Not created")})
            return json.dumps(
                {
                    "id": created.get("id"),
                    "email": created.get("email"),
                    "state": created.get("state") or "pending",
                    "forDomain": for_domain,
                    "description": description,
                    "url": url,
                    "createdBy": created.get("createdBy"),
                },
                indent=2,
            )
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_update_masked_email(
        masked_email_id: str,
        state: str | None = None,
        for_domain: str | None = None,
        description: str | None = None,
        url: str | None = None,
    ) -> str:
        """Update a masked email address.

        Args:
            masked_email_id: The ID of the masked email to update.
            state: New state: 'enabled', 'disabled', or 'deleted'.
                   'deleted' soft-deletes the address (mail will bounce).
            for_domain: Update the origin domain, e.g. 'https://example.com' (no path).
            description: Update the description.
            url: Update the deep link URL.
        """
        valid_states = ("enabled", "disabled", "deleted")
        if state is not None and state not in valid_states:
            return json.dumps(
                {"error": f"state must be one of: {', '.join(valid_states)}"}
            )
        patch: dict = {}
        if state is not None:
            patch["state"] = state
        if for_domain is not None:
            patch["forDomain"] = for_domain
        if description is not None:
            patch["description"] = description
        if url is not None:
            patch["url"] = url
        if not patch:
            return json.dumps({"error": "No fields to update"})
        try:
            data = client.set(
                "MaskedEmail",
                update={masked_email_id: patch},
                using=USING_MASKED_EMAIL,
            )
            updated = list((data.get("updated") or {}).keys())
            if masked_email_id not in updated:
                not_updated = (data.get("notUpdated") or {}).get(masked_email_id, {})
                return json.dumps(
                    {"error": not_updated.get("description", "Not updated")}
                )
            return json.dumps({"updated": masked_email_id, **patch})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
