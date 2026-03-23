"""Email action tools (mark read, move, delete, archive)."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, MailboxNotFoundError


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_move_email(email_ids: list[str], mailbox_name: str) -> str:
        """Move one or more emails to a mailbox identified by name.

        Args:
            email_ids: List of JMAP email IDs to move.
            mailbox_name: Name of the destination mailbox (case-insensitive).
        """
        try:
            mailbox = client.get_mailbox_by_name(mailbox_name)
            update = {eid: {"mailboxIds": {mailbox["id"]: True}} for eid in email_ids}
            data = client.set("Email", update=update)
            moved = list((data.get("updated") or {}).keys())
            result: dict = {"moved": moved, "mailboxId": mailbox["id"]}
            not_updated = data.get("notUpdated") or {}
            if not_updated:
                result["notUpdated"] = not_updated
            return json.dumps(result, indent=2)
        except MailboxNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_archive_email(email_ids: list[str]) -> str:
        """Move one or more emails to the Archive mailbox.

        Args:
            email_ids: List of JMAP email IDs to archive.
        """
        try:
            archive = client.get_mailbox_by_role("archive")
            update = {eid: {"mailboxIds": {archive["id"]: True}} for eid in email_ids}
            data = client.set("Email", update=update)
            archived = list((data.get("updated") or {}).keys())
            result: dict = {"archived": archived, "mailboxId": archive["id"]}
            not_updated = data.get("notUpdated") or {}
            if not_updated:
                result["notUpdated"] = not_updated
            return json.dumps(result, indent=2)
        except MailboxNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_mark_email_read(email_ids: list[str], read: bool = True) -> str:
        """Set or unset the $seen flag on one or more emails.

        Args:
            email_ids: List of JMAP email IDs to update.
            read: True to mark as read, False to mark as unread (default True).
        """
        try:
            update = {eid: {"keywords/$seen": read} for eid in email_ids}
            data = client.set("Email", update=update)
            updated = list((data.get("updated") or {}).keys())
            not_updated = data.get("notUpdated") or {}
            result: dict = {"updated": updated}
            if not_updated:
                result["notUpdated"] = not_updated
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_delete_email(email_ids: list[str], permanent: bool = False) -> str:
        """Delete one or more emails by moving to Trash, or permanently destroy them.

        Args:
            email_ids: List of JMAP email IDs to delete.
            permanent: If True, permanently destroy emails. Default moves to Trash.
        """
        try:
            if permanent:
                data = client.set("Email", destroy=email_ids)
                destroyed = data.get("destroyed") or []
                result: dict = {"destroyed": destroyed}
                not_destroyed = data.get("notDestroyed") or {}
                if not_destroyed:
                    result["notDestroyed"] = not_destroyed
            else:
                trash = client.get_mailbox_by_role("trash")
                update = {eid: {"mailboxIds": {trash["id"]: True}} for eid in email_ids}
                data = client.set("Email", update=update)
                moved = list((data.get("updated") or {}).keys())
                result = {"movedToTrash": moved, "mailboxId": trash["id"]}
                not_updated = data.get("notUpdated") or {}
                if not_updated:
                    result["notUpdated"] = not_updated
            return json.dumps(result, indent=2)
        except MailboxNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
