"""Tool registration — wires up all domain subpackages."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.dav_client import DAVClient


def register_all(server: FastMCP, client: JMAPClient, dav_client: DAVClient) -> None:
    """Register every tool domain with the server."""
    from .mail import register_all as register_mail
    from .contacts import register_all as register_contacts
    from .calendar import register_all as register_calendar
    from .files import register_all as register_files

    register_mail(server, client)
    register_contacts(server, dav_client)
    register_calendar(server, dav_client)
    register_files(server, dav_client)
