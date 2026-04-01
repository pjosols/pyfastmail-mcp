# Testing

## Structure
- Tests in `tests/`, mirroring source layout
- One test file per source module; split files when approaching 200 lines
- `tests/__init__.py` is empty (required for pytest discovery)

## Configuration
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   # no @pytest.mark.asyncio needed per test
testpaths = ["tests"]
```

Note: most test files still use `@pytest.mark.asyncio` on individual tests —
redundant with `asyncio_mode = "auto"` but harmless.

## Fixtures
`tests/conftest.py` defines two helpers, but they are NOT imported by any subdir test file —
each subdir test file defines its own helpers inline:

```python
# tests/conftest.py — defined but unused by subdirectory tests
def mock_client():
    client = MagicMock()
    client.account_id = "acc99"
    return client

def get_tool(register_fn, client, name):
    server = FastMCP("test")
    register_fn(server, client)
    return server._tool_manager._tools[name].fn
```

Helper patterns across test files:
- `mock_client()` — plain function returning `MagicMock()` with `account_id = "acc99"`
- `_tool(client, name)` — creates `FastMCP("test")`, calls `register(server, client)`, returns `server._tool_manager._tools[name].fn`

`test_mailbox.py` (both flat and `tests/mail/`) is the exception: uses `@pytest.fixture` for `mock_client` and names its helper `_get_tool(mock_client, name)`. Now 20 tests (255 lines) including 3 docstring-assertion tests (`test_list_mailboxes_docstring_mentions_labels`, `test_create_mailbox_docstring_mentions_labels`, `test_delete_mailbox_docstring_mentions_child`).

`test_email.py` uses `_tool(mock_client, name)` with a default name of `"mail_get_email"` — uses `@pytest.fixture` for `mock_client` like `test_mailbox.py`, but the helper is named `_tool` not `_get_tool`. 19 tests (200 lines) including 4 header tests (`test_get_email_with_headers`, `test_get_email_headers_not_in_result_when_not_requested`, `test_get_email_headers_appended_to_default_props`, `test_get_email_docstring_mentions_export_for_all_headers`).

`test_snippets.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `mail_search_snippets` (6 tests) — verifies no-filter call, text filter, all-filters, error handling, and empty list response. Uses `client.call.return_value`.

`test_export.py` uses `mock_client()` (plain function with `_get_session` stub returning a `downloadUrl`) and `_tool(client, name)`. Also defines `_mock_response(text, status_code)`. Tests `mail_export_email` (6 tests) — verifies blob_id provided skips `Email/get`, auto-fetch of blob_id, email-not-found, HTTP error, JMAP error, and URL construction. Uses `client.call.return_value` for the `Email/get` path and `client._http.get.return_value` for the download.

`test_import.py` uses `mock_client()` (plain function) and `_tool(client, name)` with default name `"mail_import_email"`. Defines `_import_response(created, not_created)` helper. Tests `mail_import_email` (6 tests) — verifies success, request structure, `blobNotFound`, `invalidEmail`, `overQuota`, and exception handling. Uses `client.call.return_value`.

`test_parse.py` uses `mock_client()` (plain function) and `_tool(client, name)` with default name `"mail_parse_email"`. Tests `mail_parse_email` (7 tests) — verifies parsed fields, `notParsable` error, unknown blob, empty list guard, and exception handling. Uses `client.call.return_value`.

`test_pin_email.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `mail_pin_email` (5 tests) — verifies `$flagged` keyword set/unset via `client.set`. Same pattern as `test_actions.py`.

`test_identities.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `mail_list_identities` and `mail_set_identity` (151 lines). Uses `client.call.return_value` for list, `client.set.return_value` for set operations. Covers create, update, destroy, `forbiddenFrom`, `forbidden` (mayDelete), and no-op guard.

`test_masked_email.py` uses `_client()` (plain MagicMock with `account_id = "acc99"`) and `_tool(client, name)`. Tests `mail_list_masked_emails` (4 tests), `mail_create_masked_email` (6 tests), `mail_update_masked_email` (10 tests) — 20 tests total. Covers `url`/`createdBy` fields, `deleted` state, `rateLimit` error, null `state` defaulting to `"pending"`, multi-field update, and no-fields guard. Uses `client.call.return_value` for list/create, `client.set.return_value` for update.

`test_contacts.py` uses `mock_client()` (plain function, `account_id = "acc99"`) and `_tool(client, name)` — same pattern as most mail tests. Tests `contacts_list_address_books` (6 tests).

`test_contacts_get.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Defines a `_response(list_, not_found)` helper that returns a list of `(method, data, tag)` tuples. Tests `contacts_get_contact` (6 tests).

`test_contacts_query.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `contacts_query_contacts` (9 tests) — verifies filter construction, sort, limit, empty results, and error handling.

`test_contacts_list.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `contacts_list` (8 tests) — verifies filter construction, limit, empty results, and error handling. Same pattern as `test_contacts_query.py` but calls `client.query_and_get` directly (no sort parameter).

`test_contacts_create.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `contacts_create_contact` (6 tests) — verifies JSContact Card structure, field mapping, `notCreated` error handling, and exception handling. Uses `client.set.return_value` (not `client.call`) because `contacts_create_contact` calls `client.set()` directly.

`test_contacts_update.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `contacts_update_contact` (7 tests) — verifies JSON patch path construction, all-fields update, no-fields guard, `notUpdated` error handling, empty response handling, and exception handling. Uses `client.set.return_value` like `test_contacts_create.py`.

`test_contacts_delete.py` uses `mock_client()` (plain function) and `_tool(client, name)`. Tests `contacts_delete_contact` (6 tests) — verifies single/bulk delete, partial success, `notDestroyed` error mapping, and exception handling. Uses `client.set.return_value` like `test_contacts_create.py`.

`test_set_errors.py` imports `_humanize_errors` directly from `tools/mail/actions.py` and also imports `register` from both `actions.py` and `labels.py`. Uses inline `MagicMock()` (no shared factory). Tests `_humanize_errors` unit (5 tests) and integration via `mail_mark_email_read` and `mail_manage_email_labels` (3 tests) — 8 tests total. Verifies `tooManyKeywords`, `tooManyMailboxes`, `blobNotFound` humanization and unknown-error passthrough.

`test_caldav.py` uses `_client()` (DAVClient mock with `email`) and `_mock_response(xml_text)`.

`test_caldav_get_event.py` uses the same `_client()` / `_tool()` / `_mock_response(text)` pattern
as `test_caldav.py`. Tests `calendar_get_event` (6 tests).

`test_caldav_write.py` imports `register` from `tools/calendar/caldav_write.py`. Its `_mock_response`
accepts an optional `headers` dict (needed for ETag in update tests), matching `test_carddav_write.py`:
```python
def _mock_response(text: str = "", headers: dict | None = None):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp
```
Tests `calendar_create_event` (4), `calendar_update_event` (4), `calendar_delete_event` (4).

`test_webdav.py` imports `register` from `tools/files/webdav.py`. Its `_mock_response` accepts
`text`, `headers`, and `content: bytes` — the extra `content` field is intentional because
`files_get` reads `resp.content` (binary), unlike CardDAV/CalDAV tools that read `resp.text`:
```python
def _mock_response(text: str = "", headers: dict | None = None, content: bytes = b""):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.content = content
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp
```

`test_webdav_write.py` imports `register` from `tools/files/webdav_write.py`. Its `_mock_response`
takes no arguments (write tools don't parse response bodies):
```python
def _mock_response():
    resp = MagicMock(spec=requests.Response)
    resp.raise_for_status = MagicMock()
    return resp
```

`test_dav_client.py` tests `DAVClient` directly (not via tool registration). Uses
`patch.object(client._http, ...)` to mock the underlying `requests.Session` methods:
```python
def _client():
    return DAVClient(email="user@example.com", app_password="secret")

def _mock_response(status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp
```
Tests `put_bytes`, `mkcol`, and `move` — 4 tests each (happy path + HTTP error).

`test_optional_dav.py` tests `DAVClient.available` flag and conditional `register_all` behavior.
Uses real `DAVClient` instances (not mocks) for the `available` tests, and `MagicMock` with
`available = False/True` for the registration tests. 9 tests total.

`test_registration.py` uses `_jmap_client()` and `_dav_client()` factories and tests the full
`register_all` wiring, including:
```python
EXPECTED_CONTACTS_TOOLS = {
    "contacts_list_address_books", "contacts_get_contact",
    "contacts_query_contacts", "contacts_list", "contacts_create_contact",
    "contacts_update_contact", "contacts_delete_contact",
}
EXPECTED_CALENDAR_TOOLS = {
    "calendar_list_calendars", "calendar_list_events", "calendar_get_event",
    "calendar_create_event", "calendar_update_event", "calendar_delete_event",
}
EXPECTED_FILES_TOOLS = {
    "files_list", "files_get", "files_upload",
    "files_create_folder", "files_delete", "files_move",
}
```

`test_exception_handling.py` uses `_jmap_client()` and `_dav_client()` factories and a
`_tool(register_fn, client, name)` helper that accepts the register function as a parameter
(unlike other files where `register` is imported at module level). Verifies that
`FastmailError`, `requests.RequestException`, and `ValueError` are caught and returned as
JSON error payloads, while `AttributeError`, `TypeError`, and `KeyError` propagate.

## Mocking Pattern
HTTP calls are patched at the `requests.Session` method level (JMAP tests):

```python
def _make_client():
    from pyfastmail_mcp.client import JMAPClient
    return JMAPClient(api_token="tok")

def _mock_response(json_data=None, status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp
```

`_make_client` and `_mock_response` are defined only in `test_setup_project.py`.

CardDAV/CalDAV/WebDAV tests mock `DAVClient` directly (not `requests.Session`):

```python
def _client():
    c = MagicMock()
    c.email = "user@example.com"
    return c
```

`test_dav_client.py` is the exception — it tests the real `DAVClient` and patches `client._http`.

## Tool Testing Pattern
Registered tools are invoked by reaching into `server._tool_manager._tools`:

```python
def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn

result = await _tool(mock_client(), "mail_forward_email")(email_id="e1", to=["x@y.com"])
```

This is an internal FastMCP API — fragile if FastMCP changes its internals.

## Helper Naming Summary
| File | client factory | tool helper |
|---|---|---|
| `test_setup_project.py` | `@pytest.fixture mock_client` | direct `server._tool_manager._tools[name].fn` |
| `test_actions.py` | `mock_client()` | `_tool(client, name)` |
| `test_pin_email.py` | `mock_client()` | `_tool(client, name)` |
| `test_mailbox.py` | `@pytest.fixture mock_client` | `_get_tool(mock_client, name)` |
| `test_email.py` | `@pytest.fixture mock_client` | `_tool(mock_client, name)` (default name) |
| `test_send.py` | `mock_client()` | `_tool(client, name)` |
| `test_reply.py` | `mock_client()` | `_tool(client, name)` |
| `test_forward.py` | `mock_client()` | `_tool(client, name)` |
| `test_labels.py` | `_client()` | `_tool(client)` (name hardcoded) |
| `test_masked_email.py` | `_client()` | `_tool(client, name)` |
| `test_thread.py` | `_client()` | `_tool(client)` (name hardcoded) |
| `test_identities.py` | `mock_client()` | `_tool(client, name)` |
| `test_attachments.py` | `mock_client()` | `_tool(client, name)` |
| `test_snippets.py` | `mock_client()` | `_tool(client, name)` |
| `test_export.py` | `mock_client()` (with `_get_session` stub) | `_tool(client, name)` |
| `test_import.py` | `mock_client()` | `_tool(client, name)` (default name) |
| `test_parse.py` | `mock_client()` | `_tool(client, name)` (default name) |
| `test_contacts.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_get.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_query.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_list.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_create.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_update.py` | `mock_client()` | `_tool(client, name)` |
| `test_contacts_delete.py` | `mock_client()` | `_tool(client, name)` |
| `test_set_errors.py` | inline `MagicMock()` | `_actions_tool(client, name)` / `_labels_tool(client)` |
| `test_caldav.py` | `_client()` (DAVClient mock, `email` only) | `_tool(client, name)` |
| `test_caldav_get_event.py` | `_client()` (DAVClient mock, `email` only) | `_tool(client, name)` |
| `test_caldav_write.py` | `_client()` (DAVClient mock, `email` only) | `_tool(client, name)` |
| `test_webdav.py` | `_client()` (plain MagicMock) | `_tool(client, name)` |
| `test_webdav_write.py` | `_client()` (plain MagicMock) | `_tool(client, name)` |
| `test_dav_client.py` | `_client()` (real `DAVClient`) | n/a — calls methods directly |
| `test_optional_dav.py` | real `DAVClient` / `MagicMock` | n/a — tests `available` flag and `register_all` |
| `test_registration.py` | `_jmap_client()`, `_dav_client()` | direct `register_all` call |
| `test_exception_handling.py` | `_jmap_client()`, `_dav_client()` | `_tool(register_fn, client, name)` |
| `test_path_traversal.py` | inline `MagicMock()` per helper | `_read_tool(name)` / `_write_tool(name)` |
