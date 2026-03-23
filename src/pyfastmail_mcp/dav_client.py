"""DAVClient — shared HTTP client for CardDAV, CalDAV, and WebDAV."""

import os

import requests

from pyfastmail_mcp.exceptions import AuthenticationError

CARDDAV_BASE = "https://carddav.fastmail.com"
CALDAV_BASE = "https://caldav.fastmail.com"
WEBDAV_BASE = "https://myfiles.fastmail.com"

PROPFIND_ADDRESSBOOK = """<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:prop>
    <D:displayname/>
    <D:resourcetype/>
    <C:addressbook-description/>
  </D:prop>
</D:propfind>"""


class DAVClient:
    """Minimal DAV client using Basic auth (app password)."""

    def __init__(
        self,
        email: str | None = None,
        app_password: str | None = None,
    ):
        self.email = email or os.environ.get("FASTMAIL_EMAIL", "")
        password = app_password or os.environ.get("FASTMAIL_APP_PASSWORD", "")
        if not self.email:
            raise AuthenticationError("FASTMAIL_EMAIL is not set")
        if not password:
            raise AuthenticationError("FASTMAIL_APP_PASSWORD is not set")
        self._http = requests.Session()
        self._http.auth = (self.email, password)

    def propfind(self, url: str, depth: str = "1", body: str = "") -> requests.Response:
        headers = {"Depth": depth, "Content-Type": "application/xml"}
        resp = self._http.request("PROPFIND", url, headers=headers, data=body.encode())
        resp.raise_for_status()
        return resp

    def report(self, url: str, body: str) -> requests.Response:
        headers = {"Depth": "1", "Content-Type": "application/xml"}
        resp = self._http.request("REPORT", url, headers=headers, data=body.encode())
        resp.raise_for_status()
        return resp

    def get(self, url: str) -> requests.Response:
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp

    def put(self, url: str, content: str, content_type: str, etag: str | None = None) -> requests.Response:
        headers = {"Content-Type": content_type}
        if etag:
            headers["If-Match"] = etag
        resp = self._http.put(url, data=content.encode(), headers=headers)
        resp.raise_for_status()
        return resp

    def put_bytes(self, url: str, data: bytes, content_type: str) -> requests.Response:
        headers = {"Content-Type": content_type}
        resp = self._http.put(url, data=data, headers=headers)
        resp.raise_for_status()
        return resp

    def mkcol(self, url: str) -> requests.Response:
        resp = self._http.request("MKCOL", url)
        resp.raise_for_status()
        return resp

    def move(self, src_url: str, dest_url: str) -> requests.Response:
        headers = {"Destination": dest_url, "Overwrite": "T"}
        resp = self._http.request("MOVE", src_url, headers=headers)
        resp.raise_for_status()
        return resp

    def delete(self, url: str) -> requests.Response:
        resp = self._http.delete(url)
        resp.raise_for_status()
        return resp

    def validate_dav_url(self, url: str) -> None:
        """Raise ValueError if url does not start with a known DAV base URL."""
        allowed = (CARDDAV_BASE, CALDAV_BASE, WEBDAV_BASE)
        if not any(url == base or url.startswith(base + "/") for base in allowed):
            raise ValueError(f"URL not allowed: {url!r}")

    def carddav_principal_url(self) -> str:
        return f"{CARDDAV_BASE}/dav/principals/user/{self.email}/"

    def caldav_principal_url(self) -> str:
        return f"{CALDAV_BASE}/dav/principals/user/{self.email}/"
