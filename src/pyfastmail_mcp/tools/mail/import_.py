"""Email import tool — import raw RFC 5322 messages via JMAP Email/import."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_IMPORT_ERRORS = {
    "blobNotFound": "Blob not found",
    "invalidEmail": "Email blob is not a valid RFC 5322 message",
    "tooManyMailboxes": "Too many mailboxes specified",
    "overQuota": "Account is over quota",
}


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_import_email(
        blob_id: str,
        mailbox_ids: list[str],
        keywords: list[str] | None = None,
        received_at: str | None = None,
    ) -> str:
        """Import a raw RFC 5322 message blob into the mail store.

        The blob must already be uploaded (use mail_upload_attachment to get a blobId).
        The .eml content must be a valid RFC 5322 message with at minimum Date and
        Message-Id headers — a bare body without proper headers will be rejected.

        Args:
            blob_id: blobId of the uploaded .eml blob.
            mailbox_ids: List of mailbox IDs to place the email in.
            keywords: Optional JMAP keywords (e.g. ["$seen", "$flagged"]).
            received_at: Optional UTC timestamp (ISO 8601) for receivedAt.
        """
        try:
            account_id = client.account_id
            email_obj: dict = {
                "blobId": blob_id,
                "mailboxIds": {mid: True for mid in mailbox_ids},
            }
            if keywords:
                email_obj["keywords"] = {kw: True for kw in keywords}
            if received_at:
                email_obj["receivedAt"] = received_at

            responses = client.call(
                USING_MAIL,
                [
                    [
                        "Email/import",
                        {
                            "accountId": account_id,
                            "emails": {"1": email_obj},
                        },
                        "i",
                    ]
                ],
            )
            _, data, _ = responses[0]

            created = data.get("created", {})
            not_created = data.get("notCreated", {})

            if not_created.get("1"):
                err = not_created["1"]
                err_type = err.get("type", "unknown")
                description = _IMPORT_ERRORS.get(err_type, err_type)
                if err_type == "blobNotFound":
                    return json.dumps({"error": f"{description}: {blob_id!r}"})
                return json.dumps({"error": description})

            if created.get("1"):
                result = created["1"]
                return json.dumps(
                    {
                        "id": result.get("id"),
                        "blob_id": result.get("blobId"),
                        "thread_id": result.get("threadId"),
                        "size": result.get("size"),
                    }
                )

            return json.dumps({"error": "Unexpected response from server"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
