"""Identity tools — list identities and find identity helper."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import USING_SUBMISSION, JMAPClient
from pyfastmail_mcp.exceptions import FastmailError, IdentityNotFoundError


def _find_identity(client: JMAPClient, identity_id: str | None) -> dict:
    """Return identity dict; auto-select first if identity_id is None."""
    responses = client.call(
        USING_SUBMISSION,
        [["Identity/get", {"accountId": client.account_id, "ids": None}, "i"]],
    )
    _, data, _ = responses[0]
    identities = data.get("list", [])
    if not identities:
        raise IdentityNotFoundError("No sender identities found")
    if identity_id is None:
        return identities[0]
    for ident in identities:
        if ident["id"] == identity_id:
            return ident
    raise IdentityNotFoundError(f"Identity not found: {identity_id!r}")


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_set_identity(
        create_email: str | None = None,
        create_name: str | None = None,
        update_id: str | None = None,
        update_name: str | None = None,
        update_reply_to: list[dict] | None = None,
        update_bcc: list[dict] | None = None,
        update_text_signature: str | None = None,
        update_html_signature: str | None = None,
        destroy_id: str | None = None,
    ) -> str:
        """Create, update, or destroy a sender identity.

        To create: provide create_email (required) and optionally create_name.
        To update: provide update_id plus any fields to change (name, replyTo, bcc,
            textSignature, htmlSignature).
        To destroy: provide destroy_id. Fails if mayDelete is false on that identity.

        replyTo and bcc are lists of EmailAddress objects: [{"email": "...", "name": "..."}].

        Requires urn:ietf:params:jmap:submission capability.
        """
        try:
            create: dict | None = None
            update: dict | None = None
            destroy: list | None = None

            if create_email:
                create = {"new": {"email": create_email}}
                if create_name is not None:
                    create["new"]["name"] = create_name

            if update_id:
                patch: dict = {}
                if update_name is not None:
                    patch["name"] = update_name
                if update_reply_to is not None:
                    patch["replyTo"] = update_reply_to
                if update_bcc is not None:
                    patch["bcc"] = update_bcc
                if update_text_signature is not None:
                    patch["textSignature"] = update_text_signature
                if update_html_signature is not None:
                    patch["htmlSignature"] = update_html_signature
                if patch:
                    update = {update_id: patch}

            if destroy_id:
                destroy = [destroy_id]

            if not create and not update and not destroy:
                return json.dumps({"error": "No operation specified"})

            data = client.set(
                "Identity",
                create=create,
                update=update,
                destroy=destroy,
                using=USING_SUBMISSION,
            )

            result: dict = {}
            if data.get("created"):
                created_obj = data["created"].get("new", {})
                result["created"] = created_obj.get("id")
            if data.get("notCreated"):
                err = data["notCreated"].get("new", {})
                err_type = err.get("type", "")
                if err_type == "forbiddenFrom":
                    return json.dumps(
                        {
                            "error": "Not permitted to create an identity with this email address"
                        }
                    )
                return json.dumps({"error": err.get("description", "Create failed")})
            if data.get("updated"):
                result["updated"] = update_id
            if data.get("notUpdated"):
                err = data["notUpdated"].get(update_id, {})
                return json.dumps({"error": err.get("description", "Update failed")})
            if data.get("destroyed"):
                result["destroyed"] = destroy_id
            if data.get("notDestroyed"):
                err = data["notDestroyed"].get(destroy_id, {})
                err_type = err.get("type", "")
                if err_type == "forbidden":
                    return json.dumps(
                        {
                            "error": "This identity cannot be deleted (mayDelete is false)"
                        }
                    )
                return json.dumps({"error": err.get("description", "Destroy failed")})

            return json.dumps(result)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_list_identities() -> str:
        """List all sender identities available on this Fastmail account.

        Returns each identity's id, name, and email address.
        """
        try:
            responses = client.call(
                USING_SUBMISSION,
                [["Identity/get", {"accountId": client.account_id, "ids": None}, "i"]],
            )
            _, data, _ = responses[0]
            identities = [
                {"id": i["id"], "name": i.get("name", ""), "email": i.get("email", "")}
                for i in data.get("list", [])
            ]
            return json.dumps(identities, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
