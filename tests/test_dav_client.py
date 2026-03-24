"""Tests for DAVClient.put_bytes, mkcol, move, credential validation, and discovery."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from pyfastmail_mcp.dav_client import DAVClient


def _client():
    return DAVClient(email="user@example.com", app_password="secret")


def _mock_response(status_code=200, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_put_bytes_sends_correct_request():
    client = _client()
    resp = _mock_response()
    with patch.object(client._http, "put", return_value=resp) as mock_put:
        result = client.put_bytes(
            "https://myfiles.fastmail.com/f.bin", b"data", "application/octet-stream"
        )
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


def test_empty_email_unavailable():
    with patch.dict("os.environ", {"FASTMAIL_EMAIL": "", "FASTMAIL_APP_PASSWORD": ""}):
        client = DAVClient(email="", app_password="secret")
        assert client.available is False


def test_empty_password_unavailable():
    with patch.dict("os.environ", {"FASTMAIL_EMAIL": "", "FASTMAIL_APP_PASSWORD": ""}):
        client = DAVClient(email="user@example.com", app_password="")
        assert client.available is False


def test_valid_credentials_ok():
    client = DAVClient(email="user@example.com", app_password="secret")
    assert client.email == "user@example.com"
    assert client.available is True


# --- discover_carddav_home ---

_CARDDAV_HOME_XML = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <C:addressbook-home-set>
          <D:href>/dav/addressbooks/user/user@example.com/</D:href>
        </C:addressbook-home-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

_CARDDAV_HOME_XML_ABSOLUTE = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <C:addressbook-home-set>
          <D:href>https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/</D:href>
        </C:addressbook-home-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


def test_discover_carddav_home_relative_href():
    client = _client()
    resp = _mock_response(text=_CARDDAV_HOME_XML)
    with patch.object(client, "propfind", return_value=resp):
        url = client.discover_carddav_home()
    assert url == "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/"


def test_discover_carddav_home_absolute_href():
    client = _client()
    resp = _mock_response(text=_CARDDAV_HOME_XML_ABSOLUTE)
    with patch.object(client, "propfind", return_value=resp):
        url = client.discover_carddav_home()
    assert url == "https://carddav.fastmail.com/dav/addressbooks/user/user@example.com/"


def test_discover_carddav_home_missing_raises():
    client = _client()
    resp = _mock_response(text='<?xml version="1.0"?><D:multistatus xmlns:D="DAV:"/>')
    with patch.object(client, "propfind", return_value=resp):
        with pytest.raises(ValueError, match="addressbook-home-set"):
            client.discover_carddav_home()


# --- discover_caldav_home ---

_CALDAV_HOME_XML = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-home-set>
          <D:href>/dav/calendars/user/user@example.com/</D:href>
        </C:calendar-home-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

_CALDAV_HOME_XML_ABSOLUTE = """<?xml version="1.0"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/dav/principals/user/user@example.com/</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-home-set>
          <D:href>https://caldav.fastmail.com/dav/calendars/user/user@example.com/</D:href>
        </C:calendar-home-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


def test_discover_caldav_home_relative_href():
    client = _client()
    resp = _mock_response(text=_CALDAV_HOME_XML)
    with patch.object(client, "propfind", return_value=resp):
        url = client.discover_caldav_home()
    assert url == "https://caldav.fastmail.com/dav/calendars/user/user@example.com/"


def test_discover_caldav_home_absolute_href():
    client = _client()
    resp = _mock_response(text=_CALDAV_HOME_XML_ABSOLUTE)
    with patch.object(client, "propfind", return_value=resp):
        url = client.discover_caldav_home()
    assert url == "https://caldav.fastmail.com/dav/calendars/user/user@example.com/"


def test_discover_caldav_home_missing_raises():
    client = _client()
    resp = _mock_response(text='<?xml version="1.0"?><D:multistatus xmlns:D="DAV:"/>')
    with patch.object(client, "propfind", return_value=resp):
        with pytest.raises(ValueError, match="calendar-home-set"):
            client.discover_caldav_home()
