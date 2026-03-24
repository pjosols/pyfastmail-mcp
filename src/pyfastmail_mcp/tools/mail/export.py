"""Email export tool — raw .eml download via JMAP blob endpoint."""

import json
from urllib.parse import quote

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError
from pyfastmail_mcp.tools.mail.attachments import _validate_jmap_url


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_export_email(
        email_id: str,
        blob_id: str | None = None,
    ) -> str:
        """Download the raw RFC 5322 .eml source of an email.

        Returns the full raw message including all headers and MIME parts.
        Use this when you need all headers — mail_get_email only fetches
        headers by name.

        Args:
            email_id: The JMAP email ID.
            blob_id: Optional blobId; fetched automatically if not provided.
        """
        try:
            if blob_id is None:
                responses = client.call(
                    USING_MAIL,
                    [
                        [
                            "Email/get",
                            {
                                "accountId": client.account_id,
                                "ids": [email_id],
                                "properties": ["blobId"],
                            },
                            "g",
                        ]
                    ],
                )
                _, data, _ = responses[0]
                emails = data.get("list", [])
                if not emails:
                    return json.dumps({"error": f"Email {email_id!r} not found"})
                blob_id = emails[0]["blobId"]

            session = client._get_session()
            account_id = client.account_id
            download_url = (
                session["downloadUrl"]
                .replace("{accountId}", quote(account_id, safe=""))
                .replace("{blobId}", quote(blob_id, safe=""))
                .replace("{type}", quote("message/rfc822", safe=""))
                .replace("{name}", quote("email.eml", safe=""))
            )
            _validate_jmap_url(download_url)
            resp = client._http.get(download_url)
            resp.raise_for_status()
            return json.dumps(
                {
                    "email_id": email_id,
                    "blob_id": blob_id,
                    "eml": resp.text,
                }
            )
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
