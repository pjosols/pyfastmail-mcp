"""Tests for WebDAV read tools (files_list, files_get)."""

import base64
import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.files.webdav import register


def _client():
    return MagicMock()


def _mock_response(text: str = "", headers: dict | None = None, content: bytes = b""):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.content = content
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


_LIST_XML = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:">
  <D:response>
    <D:href>/</D:href>
    <D:propstat>
      <D:prop>
        <D:displayname>root</D:displayname>
        <D:resourcetype><D:collection/></D:resourcetype>
        <D:getcontenttype></D:getcontenttype>
        <D:getcontentlength></D:getcontentlength>
        <D:getlastmodified></D:getlastmodified>
      </D:prop>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/notes.txt</D:href>
    <D:propstat>
      <D:prop>
        <D:displayname>notes.txt</D:displayname>
        <D:resourcetype/>
        <D:getcontenttype>text/plain</D:getcontenttype>
        <D:getcontentlength>42</D:getcontentlength>
        <D:getlastmodified>Mon, 01 Jan 2024 00:00:00 GMT</D:getlastmodified>
      </D:prop>
    </D:propstat>
  </D:response>
</D:multistatus>"""


async def test_files_list_returns_items():
    client = _client()
    client.propfind.return_value = _mock_response(text=_LIST_XML)
    result = json.loads(await _tool(client, "files_list")())
    assert len(result) == 2
    assert result[0]["href"] == "/"
    assert result[0]["is_collection"] is True
    assert result[1]["href"] == "/notes.txt"
    assert result[1]["content_type"] == "text/plain"
    assert result[1]["size"] == 42


async def test_files_list_custom_path_and_depth():
    client = _client()
    client.propfind.return_value = _mock_response(text=_LIST_XML)
    await _tool(client, "files_list")(path="/docs", depth="0")
    call_args = client.propfind.call_args
    assert "/docs" in call_args[0][0]
    assert call_args[1]["depth"] == "0"


async def test_files_list_invalid_depth_infinity():
    client = _client()
    result = json.loads(await _tool(client, "files_list")(depth="infinity"))
    assert "error" in result
    client.propfind.assert_not_called()


async def test_files_list_invalid_depth_arbitrary():
    client = _client()
    result = json.loads(await _tool(client, "files_list")(depth="2"))
    assert "error" in result
    client.propfind.assert_not_called()


async def test_files_list_error():
    client = _client()
    client.propfind.side_effect = requests.RequestException("network error")
    result = json.loads(await _tool(client, "files_list")())
    assert "error" in result


async def test_files_get_returns_base64():
    client = _client()
    raw = b"hello world"
    client.get.return_value = _mock_response(
        content=raw,
        headers={"Content-Type": "text/plain"},
    )
    result = json.loads(await _tool(client, "files_get")(path="/notes.txt"))
    assert result["filename"] == "notes.txt"
    assert result["content_type"] == "text/plain"
    assert base64.b64decode(result["content"]) == raw


async def test_files_get_rejects_oversized():
    client = _client()
    limit = 50 * 1024 * 1024 + 1
    client.get.return_value = _mock_response(
        content=b"",
        headers={"Content-Length": str(limit)},
    )
    result = json.loads(await _tool(client, "files_get")(path="/big.bin"))
    assert "error" in result
    assert "too large" in result["error"]


async def test_files_get_error():
    client = _client()
    client.get.side_effect = requests.RequestException("not found")
    result = json.loads(await _tool(client, "files_get")(path="/missing.txt"))
    assert "error" in result
