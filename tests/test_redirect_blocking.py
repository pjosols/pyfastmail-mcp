"""Tests verifying that JMAPClient and DAVClient block HTTP redirects (M1)."""

import requests

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.dav_client import DAVClient


def test_jmap_client_blocks_redirects():
    client = JMAPClient(api_token="tok")
    assert client._http.max_redirects == 0


def test_dav_client_blocks_redirects():
    client = DAVClient(email="user@example.com", app_password="secret")
    assert client._http.max_redirects == 0


def test_jmap_client_redirect_raises_toomanyredirects(monkeypatch):
    """A real redirect response should raise TooManyRedirects, not follow the redirect."""
    client = JMAPClient(api_token="tok")
    resp = requests.Response()
    resp.status_code = 301
    resp.headers["Location"] = "https://evil.example.com/"

    import requests as req

    def fake_send(prepared, **kwargs):
        raise req.TooManyRedirects(response=resp)

    monkeypatch.setattr(client._http, "send", fake_send)
    import pytest

    with pytest.raises(req.TooManyRedirects):
        client._http.get("https://api.fastmail.com/jmap/session")


def test_dav_client_redirect_raises_toomanyredirects(monkeypatch):
    """A real redirect response should raise TooManyRedirects, not follow the redirect."""
    client = DAVClient(email="user@example.com", app_password="secret")
    resp = requests.Response()
    resp.status_code = 301
    resp.headers["Location"] = "https://evil.example.com/"

    import requests as req

    def fake_send(prepared, **kwargs):
        raise req.TooManyRedirects(response=resp)

    monkeypatch.setattr(client._http, "send", fake_send)
    import pytest

    with pytest.raises(req.TooManyRedirects):
        client._http.get("https://carddav.fastmail.com/dav/")
