"""Email thread tool."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_THREAD_EMAIL_PROPS = ["id", "threadId", "subject", "from", "receivedAt", "preview"]


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_get_email_thread(email_id: str) -> str:
        """Return all emails in the same thread as the given email, in chronological order.

        Args:
            email_id: ID of any email in the thread.
        """
        try:
            account_id = client.account_id

            responses = client.call(
                USING_MAIL,
                [
                    [
                        "Email/get",
                        {
                            "accountId": account_id,
                            "ids": [email_id],
                            "properties": ["threadId"],
                        },
                        "g",
                    ]
                ],
            )
            _, data, _ = responses[0]
            items = data.get("list", [])
            if not items:
                return json.dumps({"error": f"Email {email_id!r} not found"})

            thread_id = items[0]["threadId"]

            responses = client.call(
                USING_MAIL,
                [
                    [
                        "Thread/get",
                        {
                            "accountId": account_id,
                            "ids": [thread_id],
                        },
                        "t",
                    ],
                    [
                        "Email/get",
                        {
                            "accountId": account_id,
                            "#ids": {
                                "resultOf": "t",
                                "name": "Thread/get",
                                "path": "/list/*/emailIds",
                            },
                            "properties": _THREAD_EMAIL_PROPS,
                        },
                        "e",
                    ],
                ],
            )
            _, email_data, _ = responses[1]
            emails = email_data.get("list", [])
            emails.sort(key=lambda e: e.get("receivedAt", ""))
            return json.dumps(emails, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
