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
