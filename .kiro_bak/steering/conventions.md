# Conventions

## Environment
- Virtual environment lives at `./.venv` (not `venv`)
- Use `uv` for package management (not pip): `uv sync`, `uv run pytest`
- Dev tools (black, isort, ruff, pytest, pytest-asyncio) in pyproject.toml `[project.optional-dependencies]` dev group

## Tool Registration Pattern
Each tool module exposes a `register(server, client)` function. Each subpackage's
`__init__.py` exposes `register_all`. `tools/__init__.py` calls them all:

```python
# tools/__init__.py
def register_all(server: FastMCP, client: JMAPClient, dav_client: DAVClient) -> None:
    from .contacts import register_all as register_contacts
    from .mail import register_all as register_mail
    register_mail(server, client)
    register_contacts(server, client)   # JMAPClient, not DAVClient
    if dav_client.available:
        from .calendar import register_all as register_calendar
        from .files import register_all as register_files
        register_calendar(server, dav_client)
        register_files(server, dav_client)
```

Tool functions are closures over their client — no global state.

## Module Naming
Split by domain concept, not by overflow. Current modules:
- `tools/mail/health.py` — health_check
- `tools/mail/mailbox.py` — mail_list_mailboxes, mail_create_mailbox, mail_rename_mailbox, mail_delete_mailbox
- `tools/mail/email.py` — mail_get_email, mail_search_emails, mail_get_recent_emails
- `tools/mail/actions.py` — mail_mark_email_read, mail_move_email, mail_delete_email, mail_archive_email, mail_pin_email
- `tools/mail/identities.py` — mail_list_identities, mail_set_identity
- `tools/mail/send.py` — mail_send_email
- `tools/mail/reply.py` — mail_reply_to_email
- `tools/mail/forward.py` — mail_forward_email
- `tools/mail/labels.py` — mail_manage_email_labels
- `tools/mail/masked_email.py` — mail_list_masked_emails, mail_create_masked_email, mail_update_masked_email
- `tools/mail/thread.py` — mail_get_email_thread
- `tools/mail/attachments.py` — mail_download_attachment, mail_upload_attachment
- `tools/mail/snippets.py` — mail_search_snippets
- `tools/mail/export.py` — mail_export_email
- `tools/mail/import_.py` — mail_import_email
- `tools/mail/parse.py` — mail_parse_email
- `tools/contacts/__init__.py` — registers contacts tools (JMAPClient)
- `tools/contacts/contacts.py` — contacts_list_address_books, contacts_query_contacts, contacts_list, contacts_get_contact
- `tools/contacts/contacts_write.py` — contacts_create_contact, contacts_update_contact, contacts_delete_contact
- `tools/calendar/caldav.py` — calendar_list_calendars, calendar_list_events
- `tools/calendar/caldav_get_event.py` — calendar_get_event
- `tools/calendar/caldav_write.py` — calendar_create_event, calendar_update_event, calendar_delete_event
- `tools/files/webdav.py` — files_list, files_get
- `tools/files/webdav_write.py` — files_upload, files_create_folder, files_delete, files_move

When a module approaches 300 lines, split by extracting a distinct sub-domain into a
new descriptively-named module. Test files can go up to 400 lines. Never use numbered suffixes (compose2.py, etc.).

## Tool Naming
Tools are prefixed by domain:
- Mail tools: `mail_` (e.g. `mail_list_mailboxes`, `mail_send_email`)
- Contacts tools: `contacts_` (e.g. `contacts_list_address_books`, `contacts_list`)
- CalDAV tools: `calendar_` (e.g. `calendar_list_calendars`)
- WebDAV tools: `files_` (e.g. `files_list`, `files_upload`)
- Health: `health_check` (standalone, no prefix)

## Client Architecture
Two separate clients, both created in `server.py` and injected:
- `JMAPClient` (`client.py`) — JMAP API, Bearer token auth (`FASTMAIL_API_TOKEN`)
- `DAVClient` (`dav_client.py`) — CardDAV/CalDAV/WebDAV, Basic auth (`FASTMAIL_EMAIL` + `FASTMAIL_APP_PASSWORD`)

`DAVClient` exposes: `propfind`, `report`, `get`, `put`, `put_bytes`, `delete`,
`mkcol`, `move`, `validate_dav_url`, `carddav_principal_url`, `caldav_principal_url`.
- `available` flag: `True` only when both `email` and `app_password` are non-empty.
  When `available` is `False`, `_http` is `None` and calendar/files tools are not registered.
- `put` accepts an optional `etag` parameter for `If-Match` safe updates (text content, encodes to bytes internally).
- `put_bytes(url, data, content_type)` — binary PUT, used by `files_upload`.
- `mkcol(url)` — WebDAV MKCOL, used by `files_create_folder`.
- `move(src_url, dest_url)` — WebDAV MOVE with `Destination` + `Overwrite: T` headers, used by `files_move`.
- `validate_dav_url(url)` raises `ValueError` if url doesn't start with `CARDDAV_BASE`, `CALDAV_BASE`, or `WEBDAV_BASE`.

Module-level constants in `dav_client.py`: `CARDDAV_BASE`, `CALDAV_BASE`, `WEBDAV_BASE`, `PROPFIND_ADDRESSBOOK`.

## Cross-Module Imports
- `reply.py` imports `_find_identity` from `identities.py`
- `forward.py` imports `_find_identity` from `identities.py` directly, and
  `_get_email`, `_quote_body` from `reply.py`
- `export.py` imports `_validate_jmap_url` from `attachments.py`
- `caldav.py` imports `CALDAV_BASE` from `dav_client.py`
- `webdav.py` and `webdav_write.py` import `WEBDAV_BASE` from `dav_client.py`

## Error Handling
- `FastmailError` is the base; `AuthenticationError`, `JMAPError`,
  `MailboxNotFoundError`, `IdentityNotFoundError` are the concrete types.
- `JMAPError` carries `.method`, `.error_type`, `.description`.
- Tools catch `(FastmailError, requests.RequestException, ValueError)` and return JSON error payloads.
- Programming errors (`AttributeError`, `KeyError`, `TypeError`) are NOT caught — they propagate.
- Client methods raise specific exceptions; tools decide how to surface them.

## WebDAV Path Validation
Both `webdav.py` and `webdav_write.py` define a module-level `_check_path` helper that
rejects `..` segments before constructing URLs (L4 path traversal guard):

```python
def _check_path(path: str) -> None:
    if ".." in path.split("/"):
        raise ValueError("Path must not contain '..' segments")
```

`ValueError` is in the caught exception set, so the error is returned as a JSON payload.
`validate_dav_url()` is also called on every constructed URL to enforce SSRF protection.

## JMAPClient Patterns
- Session fetched lazily and cached in `_session_data`.
- `call(using, method_calls)` is the single HTTP entry point; raises `JMAPError` on
  any `"error"` method response.
- `query_and_get(type_, filter_, properties, using, sort, limit)` batches query+get in
  one round trip. `using`, `sort`, and `limit` are optional.
- `set(type_, create, update, destroy, using)` wraps `/set` calls.
- `get_mailbox_by_name(name)` does a case-insensitive lookup, raises `MailboxNotFoundError`.
- `get_mailbox_by_role(role)` looks up by JMAP role, raises `MailboxNotFoundError`.
- `account_id` property reads from cached session.
- Module-level constants: `USING_MAIL`, `USING_SUBMISSION`, `USING_MASKED_EMAIL`,
  `USING_CONTACTS` in `client.py`.
  - `USING_CONTACTS = ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:contacts"]`
  - Note: `USING_VACATION` has been removed — vacation response is not available via API tokens.

## Import Organization
- Use absolute imports in all tool modules and source files.
- `from pyfastmail_mcp.client import JMAPClient` — not `from .client` or `from ..client`
- `from pyfastmail_mcp.tools.mail.identities import _find_identity` — not `from .identities`
- Exception: `__init__.py` files use relative imports inside `register_all()` to avoid
  circular imports at module load time (e.g. `from . import caldav, caldav_write`).

```python
# stdlib
import json
import os

# third-party
import requests
from mcp.server.fastmcp import FastMCP

# local (always absolute)
from pyfastmail_mcp.client import JMAPClient
from pyfastmail_mcp.exceptions import AuthenticationError, JMAPError
from pyfastmail_mcp.tools.mail.identities import _find_identity
```

## Type Hints
- Use `str | None` and `dict | None` (Python 3.10+ union syntax), not `Optional`.
- `list[str]`, `dict[str, Any]` — lowercase generics throughout.
