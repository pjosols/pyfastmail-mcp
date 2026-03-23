"""WebDAV read tools — list and get files via WebDAV (RFC 4918)."""

import base64
import json
from xml.etree import ElementTree as ET

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import WEBDAV_BASE, DAVClient
from pyfastmail_mcp.exceptions import FastmailError

_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

_DAV_NS = "DAV:"

_PROPFIND_FILES = """<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:">
  <D:prop>
    <D:displayname/>
    <D:resourcetype/>
    <D:getcontenttype/>
    <D:getcontentlength/>
    <D:getlastmodified/>
  </D:prop>
</D:propfind>"""


def _tag(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _parse_propfind(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    results = []
    for response in root.iter(_tag(_DAV_NS, "response")):
        href_el = response.find(_tag(_DAV_NS, "href"))
        href = href_el.text.strip() if href_el is not None and href_el.text else ""

        resourcetype = response.find(f".//{_tag(_DAV_NS, 'resourcetype')}")
        is_collection = (
            resourcetype is not None
            and resourcetype.find(_tag(_DAV_NS, "collection")) is not None
        )

        displayname_el = response.find(f".//{_tag(_DAV_NS, 'displayname')}")
        displayname = (
            displayname_el.text.strip()
            if displayname_el is not None and displayname_el.text
            else href.rstrip("/").rsplit("/", 1)[-1]
        )

        content_type_el = response.find(f".//{_tag(_DAV_NS, 'getcontenttype')}")
        content_type = (
            content_type_el.text.strip()
            if content_type_el is not None and content_type_el.text
            else ""
        )

        size_el = response.find(f".//{_tag(_DAV_NS, 'getcontentlength')}")
        size = int(size_el.text.strip()) if size_el is not None and size_el.text else 0

        modified_el = response.find(f".//{_tag(_DAV_NS, 'getlastmodified')}")
        last_modified = (
            modified_el.text.strip()
            if modified_el is not None and modified_el.text
            else ""
        )

        results.append({
            "href": href,
            "displayname": displayname,
            "is_collection": is_collection,
            "content_type": content_type,
            "size": size,
            "last_modified": last_modified,
        })
    return results


def register(server: FastMCP, dav_client: DAVClient) -> None:
    @server.tool()
    async def files_list(path: str = "/", depth: str = "1") -> str:
        """List files and folders at a WebDAV path on Fastmail Files.

        Args:
            path: Path to list (default: root "/").
            depth: "0" for the item itself only, "1" for immediate children (default).
        """
        if depth not in ("0", "1"):
            return json.dumps({"error": f"Invalid depth {depth!r}: must be '0' or '1'"})
        try:
            url = WEBDAV_BASE.rstrip("/") + "/" + path.lstrip("/")
            resp = dav_client.propfind(url, depth=depth, body=_PROPFIND_FILES)
            items = _parse_propfind(resp.text)
            return json.dumps(items, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def files_get(path: str) -> str:
        """Download a file from Fastmail Files (WebDAV), returned as base64.

        Args:
            path: Path to the file (e.g. "/Documents/report.pdf").
        """
        try:
            url = WEBDAV_BASE.rstrip("/") + "/" + path.lstrip("/")
            resp = dav_client.get(url)
            size = int(resp.headers.get("Content-Length", 0))
            if size > _MAX_DOWNLOAD_BYTES:
                return json.dumps({"error": f"File too large ({size} bytes); limit is 50 MB"})
            filename = path.rsplit("/", 1)[-1]
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            return json.dumps({
                "filename": filename,
                "content_type": content_type,
                "content": base64.b64encode(resp.content).decode(),
            })
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
