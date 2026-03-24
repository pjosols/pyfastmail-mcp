"""Tests for mail_export_email tool."""

import json
from unittest.mock import MagicMock

import pytest
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.mail.export import register


def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    client._get_session.return_value = {
        "downloadUrl": "https://api.fastmail.com/jmap/download/{accountId}/{blobId}/{name}?accept={type}",
    }
    return client


def _tool(client, name="mail_export_email"):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(text="", status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


@pytest.mark.asyncio
async def test_export_with_blob_id_provided():
    """When blob_id is given, skip Email/get and download directly."""
    client = mock_client()
    eml = "From: a@b.com\r\nSubject: Hi\r\n\r\nBody"
    client._http.get.return_value = _mock_response(text=eml)

    result = json.loads(await _tool(client)("e1", blob_id="blob1"))

    assert result["email_id"] == "e1"
    assert result["blob_id"] == "blob1"
    assert result["eml"] == eml
    client.call.assert_not_called()


@pytest.mark.asyncio
async def test_export_fetches_blob_id_when_not_provided():
    """When blob_id is omitted, fetches it via Email/get."""
    client = mock_client()
    eml = "From: x@y.com\r\n\r\nHello"
    client.call.return_value = [
        ("Email/get", {"list": [{"id": "e2", "blobId": "blob2"}]}, "g")
    ]
    client._http.get.return_value = _mock_response(text=eml)

    result = json.loads(await _tool(client)("e2"))

    assert result["blob_id"] == "blob2"
    assert result["eml"] == eml
    client.call.assert_called_once()


@pytest.mark.asyncio
async def test_export_email_not_found():
    """Returns error when Email/get returns empty list."""
    client = mock_client()
    client.call.return_value = [("Email/get", {"list": []}, "g")]

    result = json.loads(await _tool(client)("missing"))

    assert "error" in result
    assert "missing" in result["error"]


@pytest.mark.asyncio
async def test_export_http_error():
    """Returns error on HTTP failure during download."""
    client = mock_client()
    client._http.get.return_value = _mock_response(status_code=500)

    result = json.loads(await _tool(client)("e3", blob_id="blob3"))

    assert "error" in result


@pytest.mark.asyncio
async def test_export_jmap_error():
    """Returns error when client.call raises FastmailError."""
    from pyfastmail_mcp.exceptions import JMAPError

    client = mock_client()
    client.call.side_effect = JMAPError(
        method="Email/get", error_type="serverFail", description="oops"
    )

    result = json.loads(await _tool(client)("e4"))

    assert "error" in result


@pytest.mark.asyncio
async def test_export_url_contains_account_and_blob():
    """Verifies the download URL is built with account_id and blob_id."""
    client = mock_client()
    eml = "raw"
    client._http.get.return_value = _mock_response(text=eml)

    await _tool(client)("e5", blob_id="blobX")

    url = client._http.get.call_args[0][0]
    assert "acc99" in url
    assert "blobX" in url
