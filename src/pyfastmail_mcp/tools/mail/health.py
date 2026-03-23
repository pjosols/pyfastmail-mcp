"""Health check tool."""

import json

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import FastmailError


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def health_check() -> str:
        """Verify connectivity to Fastmail and return account info."""
        try:
            account_id = client.account_id
            return json.dumps({"status": "ok", "account_id": account_id})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"status": "error", "message": str(exc)})
