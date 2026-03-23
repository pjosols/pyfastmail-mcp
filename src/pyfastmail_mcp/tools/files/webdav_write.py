"""WebDAV write tools — upload, create folder, delete, move via WebDAV (RFC 4918)."""

import base64
import json
import posixpath

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import WEBDAV_BASE, DAVClient
from pyfastmail_mcp.exceptions import FastmailError

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _url(path: str) -> str:
    return WEBDAV_BASE.rstrip("/") + posixpath.normpath("/" + path.lstrip("/"))


def register(server: FastMCP, dav_client: DAVClient) -> None:
    @server.tool()
    async def files_upload(
        path: str,
        content: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to Fastmail Files (WebDAV).

        Args:
            path: Destination path (e.g. "/Documents/report.pdf").
            content: Base64-encoded file content.
            content_type: MIME type of the file (default: application/octet-stream).
        """
        try:
            if len(content) > _MAX_UPLOAD_BYTES * 4 // 3:
                return json.dumps({"error": "Content too large; limit is 50 MB"})
            raw = base64.b64decode(content)
            url = _url(path)
            dav_client.put_bytes(url, raw, content_type)
            return json.dumps({"path": path, "uploaded": True})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def files_create_folder(path: str) -> str:
        """Create a folder on Fastmail Files (WebDAV).

        Args:
            path: Path of the new folder (e.g. "/Documents/NewFolder").
        """
        try:
            dav_client.mkcol(_url(path))
            return json.dumps({"path": path, "created": True})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def files_delete(path: str) -> str:
        """Delete a file or folder on Fastmail Files (WebDAV).

        Args:
            path: Path to delete (e.g. "/Documents/old.txt").
        """
        try:
            dav_client.delete(_url(path))
            return json.dumps({"path": path, "deleted": True})
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def files_move(source: str, destination: str) -> str:
        """Move or rename a file or folder on Fastmail Files (WebDAV).

        Args:
            source: Source path (e.g. "/Documents/old.txt").
            destination: Destination path (e.g. "/Archive/old.txt").
        """
        try:
            src_url = _url(source)
            dst_url = _url(destination)
            dav_client.move(src_url, dst_url)
            return json.dumps(
                {"source": source, "destination": destination, "moved": True}
            )
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
