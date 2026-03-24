"""Contacts tools subpackage (JMAP)."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient


def register_all(server: FastMCP, client: JMAPClient) -> None:
    """Register all contacts tools with the server."""
    from . import contacts, contacts_write

    contacts.register(server, client)
    contacts_write.register(server, client)
