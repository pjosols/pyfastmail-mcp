"""Email label/keyword tools."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.mail.actions import _humanize_errors


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_manage_email_labels(
        email_ids: list[str],
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> str:
        """Add or remove keywords/labels on one or more emails.

        Use this to pin/flag, mark read/unread, or apply custom labels.
        Common keywords: $flagged (pin/star), $seen (read), $draft, $answered, $forwarded.
        At least one of add or remove must be provided.

        Args:
            email_ids: List of JMAP email IDs to update.
            add: Keywords to add (e.g. ["$flagged"] to pin, ["$seen"] to mark read).
            remove: Keywords to remove (e.g. ["$flagged"] to unpin, ["$seen"] to mark unread).
        """
        if not add and not remove:
            return json.dumps(
                {"error": "At least one of 'add' or 'remove' must be provided"}
            )
        try:
            patch: dict = {}
            for kw in add or []:
                patch[f"keywords/{kw}"] = True
            for kw in remove or []:
                patch[f"keywords/{kw}"] = None
            update = {eid: patch for eid in email_ids}
            data = client.set("Email", update=update)
            updated = list((data.get("updated") or {}).keys())
            result: dict = {"updated": updated}
            not_updated = data.get("notUpdated") or {}
            if not_updated:
                result["notUpdated"] = _humanize_errors(not_updated)
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
