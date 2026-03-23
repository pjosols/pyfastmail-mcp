"""FastMCP server setup and entry point."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.dav_client import DAVClient
from pyfastmail_mcp.tools import register_all


def create_server() -> FastMCP:
    server = FastMCP("pyfastmail-mcp")
    client = JMAPClient()
    dav_client = DAVClient()
    register_all(server, client, dav_client)
    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
