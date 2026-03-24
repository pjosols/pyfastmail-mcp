"""Tests for L4 path traversal guard in WebDAV tools."""

import base64
import json
from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.files.webdav import register as register_read
from pyfastmail_mcp.tools.files.webdav_write import register as register_write

_ERR = "Path must not contain '..' segments"


def _read_tool(name):
    client = MagicMock()
    server = FastMCP("test")
    register_read(server, client)
    return server._tool_manager._tools[name].fn


def _write_tool(name):
    client = MagicMock()
    server = FastMCP("test")
    register_write(server, client)
    return server._tool_manager._tools[name].fn


async def test_files_list_rejects_dotdot():
    result = json.loads(await _read_tool("files_list")(path="/docs/../secret"))
    assert result["error"] == _ERR


async def test_files_get_rejects_dotdot():
    result = json.loads(await _read_tool("files_get")(path="/docs/../secret.txt"))
    assert result["error"] == _ERR


async def test_files_upload_rejects_dotdot():
    content = base64.b64encode(b"data").decode()
    result = json.loads(
        await _write_tool("files_upload")(path="/docs/../evil.txt", content=content)
    )
    assert result["error"] == _ERR


async def test_files_create_folder_rejects_dotdot():
    result = json.loads(await _write_tool("files_create_folder")(path="/docs/../evil"))
    assert result["error"] == _ERR


async def test_files_delete_rejects_dotdot():
    result = json.loads(await _write_tool("files_delete")(path="/../etc/passwd"))
    assert result["error"] == _ERR


async def test_files_move_rejects_dotdot_source():
    result = json.loads(
        await _write_tool("files_move")(source="/docs/../secret", destination="/safe")
    )
    assert result["error"] == _ERR


async def test_files_move_rejects_dotdot_destination():
    result = json.loads(
        await _write_tool("files_move")(source="/safe", destination="/docs/../evil")
    )
    assert result["error"] == _ERR
