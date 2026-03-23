"""Tests for attachment download and upload tools."""

import base64
import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.attachments import register


def _client():
    client = MagicMock()
    client.account_id = "acc99"
    client._get_session.return_value = {
        "downloadUrl": "https://api.fm.com/jmap/download/{accountId}/{blobId}/{name}?accept={type}",
        "uploadUrl": "https://api.fm.com/jmap/upload/{accountId}/",
    }
    return client


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(content=b"", json_data=None, status_code=200, headers=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.content = content
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


# --- mail_download_attachment ---


@pytest.mark.asyncio
async def test_download_attachment_ok():
    client = _client()
    raw = b"hello bytes"
    client._http.get.return_value = _mock_response(content=raw)
    result = json.loads(
        await _tool(client, "mail_download_attachment")(
            blob_id="blob1", name="file.txt", content_type="text/plain"
        )
    )
    assert result["blobId"] == "blob1"
    assert result["name"] == "file.txt"
    assert result["type"] == "text/plain"
    assert result["size"] == len(raw)
    assert result["data"] == base64.b64encode(raw).decode()


@pytest.mark.asyncio
async def test_download_attachment_default_content_type():
    client = _client()
    client._http.get.return_value = _mock_response(content=b"data")
    result = json.loads(
        await _tool(client, "mail_download_attachment")(blob_id="blob2", name="file.bin")
    )
    assert result["type"] == "application/octet-stream"


@pytest.mark.asyncio
async def test_download_attachment_rejects_oversized():
    client = _client()
    limit = 50 * 1024 * 1024 + 1
    client._http.get.return_value = _mock_response(
        content=b"", headers={"Content-Length": str(limit)}
    )
    result = json.loads(
        await _tool(client, "mail_download_attachment")(blob_id="big", name="big.bin")
    )
    assert "error" in result
    assert "too large" in result["error"]


@pytest.mark.asyncio
async def test_download_attachment_error():
    client = _client()
    client._http.get.return_value = _mock_response(status_code=404)
    result = json.loads(
        await _tool(client, "mail_download_attachment")(blob_id="bad", name="x.txt")
    )
    assert "error" in result


# --- mail_upload_attachment ---


@pytest.mark.asyncio
async def test_upload_attachment_ok():
    client = _client()
    raw = b"file content"
    encoded = base64.b64encode(raw).decode()
    client._http.post.return_value = _mock_response(
        json_data={"blobId": "newblob", "type": "image/png", "size": len(raw)}
    )
    result = json.loads(
        await _tool(client, "mail_upload_attachment")(
            data=encoded, content_type="image/png", name="photo.png"
        )
    )
    assert result["blobId"] == "newblob"
    assert result["type"] == "image/png"
    assert result["size"] == len(raw)
    client._http.post.assert_called_once()
    _, kwargs = client._http.post.call_args
    assert kwargs["data"] == raw
    assert kwargs["headers"]["Content-Type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_attachment_error():
    client = _client()
    client._http.post.return_value = _mock_response(status_code=500)
    result = json.loads(
        await _tool(client, "mail_upload_attachment")(
            data=base64.b64encode(b"x").decode(),
            content_type="text/plain",
            name="f.txt",
        )
    )
    assert "error" in result
