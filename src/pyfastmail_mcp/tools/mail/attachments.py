"""Attachment download and upload tools."""

import base64
import json
from urllib.parse import quote, urlparse

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import FastmailError

_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _validate_jmap_url(url: str) -> None:
    """Raise ValueError if the assembled JMAP URL is not on a Fastmail hostname."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        ok = parsed.scheme == "https" and (
            hostname == "fastmail.com"
            or hostname.endswith(".fastmail.com")
            or hostname == "fastmailusercontent.com"
            or hostname.endswith(".fastmailusercontent.com")
        )
    except Exception:
        ok = False
    if not ok:
        raise ValueError(f"JMAP URL hostname not allowed: {url!r}")


def register(server: FastMCP, client: JMAPClient) -> None:
    @server.tool()
    async def mail_download_attachment(
        blob_id: str,
        name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Download an attachment blob by blobId.

        Args:
            blob_id: The blobId of the attachment (from email attachments list).
            name: The filename to use for the download.
            content_type: MIME type of the attachment (default: application/octet-stream).
        """
        try:
            session = client._get_session()
            account_id = client.account_id
            download_url = (
                session["downloadUrl"]
                .replace("{accountId}", quote(account_id, safe=""))
                .replace("{blobId}", quote(blob_id, safe=""))
                .replace("{type}", quote(content_type, safe=""))
                .replace("{name}", quote(name, safe=""))
            )
            _validate_jmap_url(download_url)
            resp = client._http.get(download_url)
            resp.raise_for_status()
            size = int(resp.headers.get("Content-Length", 0))
            if size > _MAX_DOWNLOAD_BYTES:
                return json.dumps(
                    {"error": f"Attachment too large ({size} bytes); limit is 50 MB"}
                )
            return json.dumps(
                {
                    "blobId": blob_id,
                    "name": name,
                    "type": content_type,
                    "size": len(resp.content),
                    "data": base64.b64encode(resp.content).decode(),
                }
            )
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def mail_upload_attachment(
        data: str,
        content_type: str,
        name: str,
    ) -> str:
        """Upload a blob for use in email composition.

        Args:
            data: Base64-encoded file content.
            content_type: MIME type of the file.
            name: Filename (informational only; not stored with the blob).
        """
        try:
            session = client._get_session()
            account_id = client.account_id
            upload_url = session["uploadUrl"].replace(
                "{accountId}", quote(account_id, safe="")
            )
            _validate_jmap_url(upload_url)
            if len(data) > _MAX_UPLOAD_BYTES * 4 // 3:
                return json.dumps({"error": "Data too large; limit is 50 MB"})
            raw = base64.b64decode(data)
            resp = client._http.post(
                upload_url,
                data=raw,
                headers={"Content-Type": content_type},
            )
            resp.raise_for_status()
            result = resp.json()
            return json.dumps(
                {
                    "blobId": result["blobId"],
                    "type": result["type"],
                    "size": result["size"],
                }
            )
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
