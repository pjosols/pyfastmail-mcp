"""Send email tool."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_SUBMISSION, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, IdentityNotFoundError
from pyfastmail_mcp.tools.mail.identities import _find_identity

_MAX_RECIPIENTS = 50


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_send_email(
        to: list[str],
        subject: str,
        text_body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        html_body: str | None = None,
        identity_id: str | None = None,
    ) -> str:
        """Send an email via Fastmail.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            text_body: Plain-text body content.
            cc: Optional list of CC addresses.
            bcc: Optional list of BCC addresses.
            html_body: Optional HTML body content. Passed verbatim to the JMAP
                API with no sanitisation. When this tool is driven by an AI
                agent that processes external content, ensure the html_body
                value originates from a trusted source to prevent prompt-
                injection attacks from causing malicious emails to be sent.
            identity_id: Sender identity ID; auto-selects first identity if omitted.
        """
        try:
            total_recipients = len(to) + len(cc or []) + len(bcc or [])
            if total_recipients > _MAX_RECIPIENTS:
                return json.dumps(
                    {
                        "error": (
                            f"Too many recipients ({total_recipients}); "
                            f"limit is {_MAX_RECIPIENTS}"
                        )
                    }
                )
            identity = _find_identity(client, identity_id)
            account_id = client.account_id

            def _addrs(addrs: list[str]) -> list[dict]:
                return [{"email": a} for a in addrs]

            drafts = client.get_mailbox_by_role("drafts")
            email_obj: dict = {
                "from": [
                    {"email": identity["email"], "name": identity.get("name", "")}
                ],
                "to": _addrs(to),
                "subject": subject,
                "keywords": {"$draft": True},
                "mailboxIds": {drafts["id"]: True},
                "bodyValues": {"body": {"value": text_body, "charset": "utf-8"}},
                "textBody": [{"partId": "body", "type": "text/plain"}],
            }
            if cc:
                email_obj["cc"] = _addrs(cc)
            if bcc:
                email_obj["bcc"] = _addrs(bcc)
            if html_body:
                email_obj["bodyValues"]["htmlBody"] = {
                    "value": html_body,
                    "charset": "utf-8",
                }
                email_obj["htmlBody"] = [{"partId": "htmlBody", "type": "text/html"}]

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
