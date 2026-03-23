"""Reply to email tool."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, USING_SUBMISSION, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, IdentityNotFoundError
from pyfastmail_mcp.tools.mail.identities import _find_identity

_EMAIL_PROPS = [
    "id",
    "subject",
    "from",
    "to",
    "cc",
    "replyTo",
    "messageId",
    "references",
    "bodyValues",
    "textBody",
]


def _get_email(client: JMAPClient, email_id: str) -> dict:
    responses = client.call(
        USING_MAIL,
        [
            [
                "Email/get",
                {
                    "accountId": client.account_id,
                    "ids": [email_id],
                    "properties": _EMAIL_PROPS,
                    "fetchAllBodyValues": True,
                },
                "g",
            ]
        ],
    )
    _, data, _ = responses[0]
    items = data.get("list", [])
    return items[0] if items else {}


def _quote_body(email: dict) -> str:
    body_values = email.get("bodyValues") or {}
    for part in email.get("textBody") or []:
        val = body_values.get(part.get("partId", ""), {}).get("value", "")
        if val:
            return "\n".join(f"> {line}" for line in val.splitlines())
    return ""


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_reply_to_email(
        email_id: str,
        text_body: str,
        reply_all: bool = False,
        identity_id: str | None = None,
    ) -> str:
        """Reply to an email, preserving threading headers and quoting the original.

        Args:
            email_id: ID of the email to reply to.
            text_body: Your reply text (original message is quoted below).
            reply_all: If True, CC all original recipients.
            identity_id: Sender identity ID; auto-selects first if omitted.
        """
        try:
            original = _get_email(client, email_id)
            if not original:
                return json.dumps({"error": f"Email {email_id!r} not found"})

            identity = _find_identity(client, identity_id)
            account_id = client.account_id

            orig_msg_ids = original.get("messageId") or []
            orig_refs = original.get("references") or []
            in_reply_to = orig_msg_ids[0] if orig_msg_ids else None
            references = orig_refs + orig_msg_ids

            reply_to_addrs = original.get("replyTo") or original.get("from") or []
            to_addrs = [{"email": a["email"]} for a in reply_to_addrs if a.get("email")]

            subject = original.get("subject", "")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"

            quoted = _quote_body(original)
            full_body = f"{text_body}\n\n{quoted}" if quoted else text_body

            drafts = client.get_mailbox_by_role("drafts")
            email_obj: dict = {
                "from": [
                    {"email": identity["email"], "name": identity.get("name", "")}
                ],
                "to": to_addrs,
                "subject": subject,
                "keywords": {"$draft": True},
                "mailboxIds": {drafts["id"]: True},
                "bodyValues": {"body": {"value": full_body, "charset": "utf-8"}},
                "textBody": [{"partId": "body", "type": "text/plain"}],
            }
            if in_reply_to:
                email_obj["inReplyTo"] = [in_reply_to]
            if references:
                email_obj["references"] = references
            if reply_all:
                orig_to = original.get("to") or []
                orig_cc = original.get("cc") or []
                my_email = identity["email"].lower()
                cc_addrs = [
                    {"email": a["email"]}
                    for a in orig_to + orig_cc
                    if a.get("email") and a["email"].lower() != my_email
                ]
                if cc_addrs:
                    email_obj["cc"] = cc_addrs

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
