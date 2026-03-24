"""Search snippet tools (RFC 8621 Section 5)."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_search_snippets(
        email_ids: list[str],
        text: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        subject: str | None = None,
        has_attachment: bool | None = None,
    ) -> str:
        """Get highlighted subject/preview snippets for a list of emails matching a filter.

        Returns subject (with <mark> tags around matches) and a preview snippet per email.
        Use the same filter params as mail_search_emails to get relevant highlights.

        Args:
            email_ids: List of email IDs to fetch snippets for.
            text: Full-text search query (used for highlighting).
            from_: Filter by sender address.
            to: Filter by recipient address.
            subject: Filter by subject text.
            has_attachment: Filter by attachment presence.
        """
        try:
            account_id = client.account_id
            filter_: dict = {}
            if text:
                filter_["text"] = text
            if from_:
                filter_["from"] = from_
            if to:
                filter_["to"] = to
            if subject:
                filter_["subject"] = subject
            if has_attachment is not None:
                filter_["hasAttachment"] = has_attachment

            args: dict = {"accountId": account_id, "emailIds": email_ids}
            if filter_:
                args["filter"] = filter_

            responses = client.call(
                USING_MAIL,
                [["SearchSnippet/get", args, "s"]],
            )
            _, data, _ = responses[0]
            return json.dumps(data.get("list", []), indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
