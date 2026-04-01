"""DAVClient — shared HTTP client for CalDAV and WebDAV."""

import os
from urllib.parse import urlparse

import defusedxml.ElementTree as ET
import requests

CALDAV_BASE = "https://caldav.fastmail.com"
WEBDAV_BASE = "https://myfiles.fastmail.com"

_PROPFIND_CALENDAR_HOME = """<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <C:calendar-home-set/>
  </D:prop>
</D:propfind>"""

_DAV_NS = "DAV:"
_CAL_NS = "urn:ietf:params:xml:ns:caldav"


class DAVClient:
    """Minimal DAV client using Basic auth (app password)."""

    def __init__(
        self,
        email: str | None = None,
        app_password: str | None = None,
    ):
        self.email = (
            email if email is not None else os.environ.get("FASTMAIL_EMAIL", "")
        )
        password = (
            app_password
            if app_password is not None
            else os.environ.get("FASTMAIL_APP_PASSWORD", "")
        )
        if not self.email or not password:
            self.available = False
            self._http = None
            return
        self.available = True
        self._http = requests.Session()
        self._http.max_redirects = 0
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

    def put(
        self, url: str, content: str, content_type: str, etag: str | None = None
    ) -> requests.Response:
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
        """Raise ValueError if url is not a known Fastmail DAV URL.

        Validates scheme (https), hostname (exact match against known bases),
        absence of userinfo, and absence of an explicit port, to prevent SSRF
        bypasses via @-injection, lookalike hostnames, or port redirection.
        """
        allowed = (CALDAV_BASE, WEBDAV_BASE)
        allowed_hostnames = {urlparse(b).hostname for b in allowed}
        try:
            parsed = urlparse(url)
            ok = (
                parsed.scheme == "https"
                and parsed.username is None
                and parsed.port is None
                and parsed.hostname in allowed_hostnames
            )
        except Exception:
            ok = False
        if not ok:
            raise ValueError(f"URL not allowed: {url!r}")

    def caldav_principal_url(self) -> str:
        return f"{CALDAV_BASE}/dav/principals/user/{self.email}/"

    def discover_caldav_home(self) -> str:
        """Return the calendar-home-set URL via two-step RFC 4791 discovery."""
        principal_url = self.caldav_principal_url()
        resp = self.propfind(principal_url, depth="0", body=_PROPFIND_CALENDAR_HOME)
        root = ET.fromstring(resp.text)
        href_el = root.find(f".//{{{_CAL_NS}}}calendar-home-set/{{{_DAV_NS}}}href")
        if href_el is None or not href_el.text:
            raise ValueError(
                "calendar-home-set not found in principal PROPFIND response"
            )
        href = href_el.text.strip()
        return href if href.startswith("http") else CALDAV_BASE + href
