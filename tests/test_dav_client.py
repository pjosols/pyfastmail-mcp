"""Tests for DAVClient.put_bytes, mkcol, move, and credential validation."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from pyfastmail_mcp.dav_client import DAVClient
from pyfastmail_mcp.exceptions import AuthenticationError


def _client():
    return DAVClient(email="user@example.com", app_password="secret")


def _mock_response(status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def test_put_bytes_sends_correct_request():
    client = _client()
    resp = _mock_response()
    with patch.object(client._http, "put", return_value=resp) as mock_put:
        result = client.put_bytes("https://myfiles.fastmail.com/f.bin", b"data", "application/octet-stream")
    mock_put.assert_called_once_with(
        "https://myfiles.fastmail.com/f.bin",
        data=b"data",
        headers={"Content-Type": "application/octet-stream"},
    )
    resp.raise_for_status.assert_called_once()
    assert result is resp


def test_put_bytes_raises_on_http_error():
    client = _client()
    resp = _mock_response(status_code=403)
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    with patch.object(client._http, "put", return_value=resp):
        try:
            client.put_bytes("https://myfiles.fastmail.com/f.bin", b"x", "text/plain")
            assert False, "expected HTTPError"
        except requests.HTTPError:
            pass


def test_mkcol_sends_correct_request():
    client = _client()
    resp = _mock_response()
    with patch.object(client._http, "request", return_value=resp) as mock_req:
        result = client.mkcol("https://myfiles.fastmail.com/NewFolder/")
    mock_req.assert_called_once_with("MKCOL", "https://myfiles.fastmail.com/NewFolder/")
    resp.raise_for_status.assert_called_once()
    assert result is resp


def test_mkcol_raises_on_http_error():
    client = _client()
    resp = _mock_response(status_code=405)
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    with patch.object(client._http, "request", return_value=resp):
        try:
            client.mkcol("https://myfiles.fastmail.com/Dup/")
            assert False, "expected HTTPError"
        except requests.HTTPError:
            pass


def test_move_sends_correct_request():
    client = _client()
    resp = _mock_response()
    with patch.object(client._http, "request", return_value=resp) as mock_req:
        result = client.move(
            "https://myfiles.fastmail.com/a.txt",
            "https://myfiles.fastmail.com/b.txt",
        )
    mock_req.assert_called_once_with(
        "MOVE",
        "https://myfiles.fastmail.com/a.txt",
        headers={
            "Destination": "https://myfiles.fastmail.com/b.txt",
            "Overwrite": "T",
        },
    )
    resp.raise_for_status.assert_called_once()
    assert result is resp


def test_move_raises_on_http_error():
    client = _client()
    resp = _mock_response(status_code=409)
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    with patch.object(client._http, "request", return_value=resp):
        try:
            client.move(
                "https://myfiles.fastmail.com/a.txt",
                "https://myfiles.fastmail.com/b.txt",
            )
            assert False, "expected HTTPError"
        except requests.HTTPError:
            pass


# --- credential validation ---


def test_empty_email_raises():
    with pytest.raises(AuthenticationError, match="FASTMAIL_EMAIL"):
        DAVClient(email="", app_password="secret")


def test_empty_password_raises():
    with pytest.raises(AuthenticationError, match="FASTMAIL_APP_PASSWORD"):
        DAVClient(email="user@example.com", app_password="")


def test_valid_credentials_ok():
    client = DAVClient(email="user@example.com", app_password="secret")
    assert client.email == "user@example.com"
