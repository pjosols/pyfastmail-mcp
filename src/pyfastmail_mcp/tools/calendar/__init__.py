"""Calendar tools subpackage (CalDAV)."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import DAVClient


def register_all(server: FastMCP, dav_client: DAVClient) -> None:
    """Register all calendar tools with the server."""
    from . import caldav, caldav_get_event, caldav_write

    caldav.register(server, dav_client)
    caldav_get_event.register(server, dav_client)
    caldav_write.register(server, dav_client)
