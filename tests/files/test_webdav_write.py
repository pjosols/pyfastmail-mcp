"""Tests for WebDAV write tools (files_upload, files_create_folder, files_delete, files_move)."""

import base64
import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.files.webdav_write import register


def _client():
    return MagicMock()


def _mock_response():
    resp = MagicMock(spec=requests.Response)
    resp.raise_for_status = MagicMock()
    return resp


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


async def test_files_upload_success():
    client = _client()
    client.put_bytes.return_value = _mock_response()
    raw = b"file content"
    encoded = base64.b64encode(raw).decode()
    result = json.loads(
        await _tool(client, "files_upload")(path="/docs/f.txt", content=encoded, content_type="text/plain")
    )
    assert result["uploaded"] is True
    assert result["path"] == "/docs/f.txt"
    client.put_bytes.assert_called_once()
    args = client.put_bytes.call_args[0]
    assert args[1] == raw
    assert args[2] == "text/plain"


async def test_files_upload_error():
    client = _client()
    client.put_bytes.side_effect = requests.RequestException("upload failed")
    result = json.loads(
        await _tool(client, "files_upload")(path="/f.txt", content=base64.b64encode(b"x").decode())
    )
    assert "error" in result


async def test_files_create_folder_success():
    client = _client()
    client.mkcol.return_value = _mock_response()
    result = json.loads(await _tool(client, "files_create_folder")(path="/NewFolder"))
    assert result["created"] is True
    assert result["path"] == "/NewFolder"
    client.mkcol.assert_called_once()
    assert "/NewFolder" in client.mkcol.call_args[0][0]


async def test_files_create_folder_error():
    client = _client()
    client.mkcol.side_effect = requests.RequestException("already exists")
    result = json.loads(await _tool(client, "files_create_folder")(path="/Dup"))
    assert "error" in result


async def test_files_delete_success():
    client = _client()
    client.delete.return_value = _mock_response()
    result = json.loads(await _tool(client, "files_delete")(path="/old.txt"))
    assert result["deleted"] is True
    assert result["path"] == "/old.txt"
    client.delete.assert_called_once()
    assert "/old.txt" in client.delete.call_args[0][0]


async def test_files_delete_error():
    client = _client()
    client.delete.side_effect = requests.RequestException("not found")
    result = json.loads(await _tool(client, "files_delete")(path="/ghost.txt"))
    assert "error" in result


async def test_files_move_success():
    client = _client()
    client.move.return_value = _mock_response()
    result = json.loads(
        await _tool(client, "files_move")(source="/a.txt", destination="/b.txt")
    )
    assert result["moved"] is True
    assert result["source"] == "/a.txt"
    assert result["destination"] == "/b.txt"
    client.move.assert_called_once()


async def test_files_move_error():
    client = _client()
    client.move.side_effect = requests.RequestException("move failed")
    result = json.loads(
        await _tool(client, "files_move")(source="/a.txt", destination="/b.txt")
    )
    assert "error" in result
