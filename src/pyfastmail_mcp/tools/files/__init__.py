"""Files tools subpackage (WebDAV)."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import DAVClient


def register_all(server: FastMCP, dav_client: DAVClient) -> None:
    """Register all files tools with the server."""
    from . import webdav, webdav_write

    webdav.register(server, dav_client)
    webdav_write.register(server, dav_client)
