"""Contacts tools subpackage (CardDAV)."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import DAVClient


def register_all(server: FastMCP, dav_client: DAVClient) -> None:
    """Register all contacts tools with the server."""
    from . import carddav, carddav_write

    carddav.register(server, dav_client)
    carddav_write.register(server, dav_client)
