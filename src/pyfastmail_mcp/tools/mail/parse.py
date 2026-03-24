"""Email parse tool — parse blobs as RFC 5322 messages via JMAP Email/parse."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_PARSE_PROPS = [
    "id",
    "subject",
    "from",
    "to",
    "cc",
    "bcc",
    "replyTo",
    "receivedAt",
    "bodyValues",
    "textBody",
    "htmlBody",
    "attachments",
    "hasAttachment",
]


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_parse_email(blob_ids: list[str]) -> str:
        """Parse one or more blobs as RFC 5322 messages without importing them.

        Useful for viewing .eml attachments or forwarded messages stored as blobs.
        Metadata fields (mailboxIds, keywords, receivedAt) will be null since the
        message is not in the mail store.

        Args:
            blob_ids: List of blobIds to parse (e.g. from mail_download_attachment).
        """
        try:
            account_id = client.account_id
            responses = client.call(
                USING_MAIL,
                [
                    [
                        "Email/parse",
                        {
                            "accountId": account_id,
                            "blobIds": blob_ids,
                            "properties": _PARSE_PROPS,
                            "fetchAllBodyValues": True,
                        },
                        "p",
                    ]
                ],
            )
            _, data, _ = responses[0]

            parsed = data.get("parsed", {})
            not_parseable = data.get("notParseable", [])
            not_found = data.get("notFound", [])

            results = []
            for blob_id in blob_ids:
                if blob_id in parsed:
                    email = parsed[blob_id]
                    body_values = email.get("bodyValues") or {}
                    text_parts = email.get("textBody") or []
                    body = None
                    for part in text_parts:
                        part_id = part.get("partId")
                        if part_id and part_id in body_values:
                            body = body_values[part_id].get("value")
                            break
                    attachments = [
                        {
                            "name": a.get("name"),
                            "type": a.get("type"),
                            "size": a.get("size"),
                        }
                        for a in (email.get("attachments") or [])
                    ]
                    results.append(
                        {
                            "blobId": blob_id,
                            "subject": email.get("subject"),
                            "from": email.get("from"),
                            "to": email.get("to"),
                            "cc": email.get("cc"),
                            "receivedAt": email.get("receivedAt"),
                            "body": body,
                            "hasAttachment": email.get("hasAttachment"),
                            "attachments": attachments,
                        }
                    )
                elif blob_id in not_parseable:
                    results.append(
                        {"blobId": blob_id, "error": "not parseable as RFC 5322"}
                    )
                elif blob_id in not_found:
                    results.append({"blobId": blob_id, "error": "blob not found"})

            return json.dumps(results, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
