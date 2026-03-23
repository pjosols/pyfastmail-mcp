"""Shared test fixtures."""

from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client


def get_tool(register_fn, client, name):
    server = FastMCP("test")
    register_fn(server, client)
    return server._tool_manager._tools[name].fn
