"""Email action tools (mark read, move, delete, archive)."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, MailboxNotFoundError

_SET_ERROR_MESSAGES = {
    "tooManyKeywords": "Too many keywords on this email (server limit reached)",
    "tooManyMailboxes": "Too many mailboxes for this email (server limit reached)",
    "blobNotFound": "One or more referenced blobs were not found",
}

_SUBMISSION_ERROR_MESSAGES = {
    "forbiddenFrom": "Not permitted to send from this address",
    "forbiddenToSend": "Sending is not permitted for this account",
    "forbiddenMailFrom": "Not permitted to use this envelope sender",
    "noRecipients": "No recipients specified",
    "invalidEmail": "Email is invalid",
}


def _humanize_errors(errors: dict) -> dict:
    """Replace raw JMAP SetError types with human-readable messages."""
    out = {}
    for eid, err in errors.items():
        etype = err.get("type", "")
        msg = _SET_ERROR_MESSAGES.get(etype)
        if msg:
            out[eid] = {"type": etype, "error": msg}
        else:
            out[eid] = err
    return out


def _humanize_submission_errors(not_created: dict) -> str:
    """Return a human-readable error string for EmailSubmission notCreated errors."""
    messages = []
    for _key, err in not_created.items():
        etype = err.get("type", "unknown")
        if etype == "tooManyRecipients":
            max_r = err.get("maxRecipients")
            msg = (
                f"Too many recipients (max: {max_r})"
                if max_r
                else "Too many recipients"
            )
        elif etype == "invalidRecipients":
            addrs = err.get("invalidRecipients") or []
            msg = f"Invalid recipient addresses: {addrs}"
        else:
            msg = _SUBMISSION_ERROR_MESSAGES.get(etype, f"Submission error: {etype}")
        messages.append(msg)
    return "; ".join(messages)


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
                result["notUpdated"] = _humanize_errors(not_updated)
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
                result["notUpdated"] = _humanize_errors(not_updated)
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
                result["notUpdated"] = _humanize_errors(not_updated)
            return json.dumps(result, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_pin_email(email_ids: list[str], pin: bool = True) -> str:
        """Pin or unpin one or more emails (sets the $flagged keyword).

        Pinned emails appear with a flag/star/pin icon in the mail client.

        Args:
            email_ids: List of JMAP email IDs to pin or unpin.
            pin: True to pin, False to unpin (default True).
        """
        try:
            value = True if pin else None
            update = {eid: {"keywords/$flagged": value} for eid in email_ids}
            data = client.set("Email", update=update)
            updated = list((data.get("updated") or {}).keys())
            not_updated = data.get("notUpdated") or {}
            result: dict = {"updated": updated}
            if not_updated:
                result["notUpdated"] = _humanize_errors(not_updated)
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
                    result["notDestroyed"] = _humanize_errors(not_destroyed)
            else:
                trash = client.get_mailbox_by_role("trash")
                update = {eid: {"mailboxIds": {trash["id"]: True}} for eid in email_ids}
                data = client.set("Email", update=update)
                moved = list((data.get("updated") or {}).keys())
                result = {"movedToTrash": moved, "mailboxId": trash["id"]}
                not_updated = data.get("notUpdated") or {}
                if not_updated:
                    result["notUpdated"] = _humanize_errors(not_updated)
            return json.dumps(result, indent=2)
        except MailboxNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
