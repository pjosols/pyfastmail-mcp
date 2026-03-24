"""Mailbox tools."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_MAIL, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_MAILBOX_PROPS = ["id", "name", "role", "totalEmails", "unreadEmails", "parentId"]

_SYSTEM_ROLES = {"inbox", "trash", "sent", "drafts", "archive", "spam", "junk"}


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_list_mailboxes() -> str:
        """List all JMAP mailboxes (Fastmail folders and labels) with id, name, role, email counts, and parentId.

        In Fastmail, both folders and labels are represented as JMAP mailboxes.
        An email can belong to multiple mailboxes simultaneously — this is how labels work.
        Nested folders have a parentId pointing to their parent mailbox.
        System mailboxes (inbox, sent, trash, drafts, archive, spam) have a role field set.
        """
        try:
            mailboxes = client.query_and_get("Mailbox", None, _MAILBOX_PROPS)
            return json.dumps(mailboxes, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_create_mailbox(name: str, parent_id: str | None = None) -> str:
        """Create a new JMAP mailbox (folder or label) with the given name.

        In Fastmail, mailboxes serve as both folders and labels. To create a nested
        folder, provide the parent mailbox's ID via parent_id. Top-level mailboxes
        have no parentId. An email can belong to multiple mailboxes (labels).
        """
        try:
            create_args: dict = {"name": name}
            if parent_id:
                create_args["parentId"] = parent_id
            data = client.set("Mailbox", create={"new": create_args})
            created = data.get("created", {})
            if "new" in created:
                return json.dumps({"created": created["new"]})
            not_created = data.get("notCreated", {})
            if "new" in not_created:
                err = not_created["new"]
                return json.dumps(
                    {"error": err.get("description", err.get("type", "unknown"))}
                )
            return json.dumps({"error": "Mailbox not created"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_rename_mailbox(mailbox_id: str, new_name: str) -> str:
        """Rename a mailbox (folder or label) by its ID."""
        try:
            data = client.set("Mailbox", update={mailbox_id: {"name": new_name}})
            updated = data.get("updated", {})
            if mailbox_id in updated:
                return json.dumps({"updated": mailbox_id, "name": new_name})
            not_updated = data.get("notUpdated", {})
            if mailbox_id in not_updated:
                err = not_updated[mailbox_id]
                return json.dumps(
                    {"error": err.get("description", err.get("type", "unknown"))}
                )
            return json.dumps({"error": "Mailbox not updated"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_delete_mailbox(
        mailbox_id: str, on_destroy_remove_emails: bool = False
    ) -> str:
        """Delete a mailbox (folder or label) by its ID.

        System mailboxes (inbox, trash, sent, drafts, archive, spam) cannot be deleted.
        Deleting a folder does not automatically delete its child mailboxes — remove
        nested folders first. If the mailbox contains emails, set
        on_destroy_remove_emails=True to delete them along with the mailbox.

        Args:
            mailbox_id: ID of the mailbox to delete.
            on_destroy_remove_emails: If True, also delete all emails in the mailbox.
                Default False — the server will reject deletion if emails exist.
        """
        try:
            mailboxes = client.query_and_get("Mailbox", None, ["id", "role"])
            for mb in mailboxes:
                if mb["id"] == mailbox_id and mb.get("role") in _SYSTEM_ROLES:
                    return json.dumps(
                        {
                            "error": f"Cannot delete system mailbox with role {mb['role']!r}"
                        }
                    )
            responses = client.call(
                USING_MAIL,
                [
                    [
                        "Mailbox/set",
                        {
                            "accountId": client.account_id,
                            "destroy": [mailbox_id],
                            "onDestroyRemoveEmails": on_destroy_remove_emails,
                        },
                        "s",
                    ]
                ],
            )
            _, data, _ = responses[0]
            destroyed = data.get("destroyed", [])
            if mailbox_id in destroyed:
                return json.dumps({"destroyed": mailbox_id})
            not_destroyed = data.get("notDestroyed", {})
            if mailbox_id in not_destroyed:
                err = not_destroyed[mailbox_id]
                etype = err.get("type", "")
                if etype == "mailboxHasChild":
                    return json.dumps(
                        {"error": "Mailbox has child mailboxes; remove them first"}
                    )
                if etype == "mailboxHasEmail":
                    return json.dumps(
                        {
                            "error": (
                                "Mailbox contains emails; set on_destroy_remove_emails=True"
                                " to delete them along with the mailbox"
                            )
                        }
                    )
                return json.dumps(
                    {"error": err.get("description", err.get("type", "unknown"))}
                )
            return json.dumps({"error": "Mailbox not destroyed"})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
