"""Forward email tool."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_SUBMISSION, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, IdentityNotFoundError
from pyfastmail_mcp.tools.mail.identities import _find_identity
from pyfastmail_mcp.tools.mail.reply import _get_email, _quote_body


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_forward_email(
        email_id: str,
        to: list[str],
        text_body: str = "",
        identity_id: str | None = None,
    ) -> str:
        """Forward an email to one or more recipients, preserving the original content.

        Args:
            email_id: ID of the email to forward.
            to: List of recipient email addresses.
            text_body: Optional introductory text prepended before the quoted original.
            identity_id: Sender identity ID; auto-selects first if omitted.
        """
        try:
            original = _get_email(client, email_id)
            if not original:
                return json.dumps({"error": f"Email {email_id!r} not found"})

            identity = _find_identity(client, identity_id)
            account_id = client.account_id

            subject = original.get("subject", "")
            if not subject.lower().startswith("fwd:"):
                subject = f"Fwd: {subject}"

            quoted = _quote_body(original)
            full_body = f"{text_body}\n\n{quoted}".strip() if quoted else text_body

            drafts = client.get_mailbox_by_role("drafts")
            email_obj: dict = {
                "from": [
                    {"email": identity["email"], "name": identity.get("name", "")}
                ],
                "to": [{"email": addr} for addr in to],
                "subject": subject,
                "keywords": {"$draft": True},
                "mailboxIds": {drafts["id"]: True},
                "bodyValues": {"body": {"value": full_body, "charset": "utf-8"}},
                "textBody": [{"partId": "body", "type": "text/plain"}],
            }

            responses = client.call(
                USING_SUBMISSION,
                [
                    [
                        "Email/set",
                        {"accountId": account_id, "create": {"draft": email_obj}},
                        "e",
                    ],
                    [
                        "EmailSubmission/set",
                        {
                            "accountId": account_id,
                            "create": {
                                "sub": {
                                    "emailId": "#draft",
                                    "identityId": identity["id"],
                                }
                            },
                            "onSuccessDestroyEmail": ["#sub"],
                        },
                        "s",
                    ],
                ],
            )
            _, email_data, _ = responses[0]
            _, sub_data, _ = responses[1]

            not_created = sub_data.get("notCreated") or {}
            if not_created:
                return json.dumps({"error": not_created})

            created_email = (email_data.get("created") or {}).get("draft", {})
            created_sub = (sub_data.get("created") or {}).get("sub", {})
            return json.dumps(
                {
                    "sent": True,
                    "emailId": created_email.get("id"),
                    "submissionId": created_sub.get("id"),
                },
                indent=2,
            )
        except IdentityNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
