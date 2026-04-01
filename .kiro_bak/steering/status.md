# Project Status

## Overview
Fastmail JMAP + CalDAV + WebDAV MCP server. Exposes Fastmail operations as MCP tools via FastMCP.

## Current State
362 tests passing, 0 failing (`uv run pytest -q`). Last verified: 2026-03-23 22:22.

## Feature Checklist
- Mail tools: DONE (includes `mail_pin_email`, snippets, masked email overhaul,
  `mail_get_email` headers param, `mail_export_email`, `mail_import_email`, `mail_parse_email`,
  `mail_set_identity`, send/reply/forward submission error surfacing,
  `tooManyKeywords`/`tooManyMailboxes`/`blobNotFound` error humanization)
- Calendar tools: DONE
- Files tools: DONE
- Contacts tools: DONE — CRUD complete; `contacts_changes`, `contacts_query_changes`,
  `contacts_copy`, `contacts_set_address_book` all removed
- `contacts_list_address_books` uses `client.call` with `AddressBook/get` (RFC 9610 compliant)
- Optional DAV: DONE — `DAVClient.available` flag; calendar/files only register when DAV creds present
- Vacation response: REMOVED — Fastmail doesn't expose `vacationresponse` to API tokens
- SSRF validation: DONE — `validate_dav_url()` in all WebDAV tools (`test_ssrf_validation.py`, 245 lines)
- Redirect blocking: DONE — `max_redirects=0` on both clients (`test_redirect_blocking.py`, 54 lines)
- Path traversal guard: DONE — `..` segments rejected in all WebDAV file paths (`test_path_traversal.py`, 68 lines)
- `test_registration.py` is current — excludes `contacts_set_address_book`
- `test_set_errors.py` added — tests `_humanize_errors`, `tooManyKeywords`, `tooManyMailboxes` (98 lines)

## AGENT_TODO Checkbox Drift (resolved items with unchecked sub-items)
- `mail_export_email` — "Add tests" unchecked, but `test_export.py` (119 lines, 6 tests) exists and passes
- `mail_parse_email` — "Add tests" unchecked, but `test_parse.py` (187 lines, 7 tests) exists and passes
- `optional_dav_credentials` — "Add tests" unchecked, but `test_optional_dav.py` (113 lines, 9 tests) exists and passes
- `mail_pin_email` — "Update README tools table" unchecked; README now includes `mail_pin_email`

## File Tree (line counts)
```
src/pyfastmail_mcp/
├── __init__.py              (3)
├── server.py                (23)
├── client.py                (140)
├── dav_client.py            (161)
├── exceptions.py            (27)
└── tools/
    ├── __init__.py          (21)
    ├── mail/
    │   ├── __init__.py      (44)
    │   ├── health.py        (20)
    │   ├── mailbox.py       (141)  ⚠️ NEAR LIMIT
    │   ├── email.py         (183)  ⚠️ NEAR LIMIT
    │   ├── actions.py       (178)  ⚠️ NEAR LIMIT
    │   ├── identities.py    (147)  ⚠️ NEAR LIMIT
    │   ├── send.py          (126)
    │   ├── reply.py         (168)  ⚠️ NEAR LIMIT
    │   ├── forward.py       (103)
    │   ├── labels.py        (50)
    │   ├── masked_email.py  (162)  ⚠️ NEAR LIMIT
    │   ├── thread.py        (77)
    │   ├── attachments.py   (116)
    │   ├── snippets.py      (60)
    │   ├── export.py        (72)
    │   ├── import_.py       (87)
    │   └── parse.py         (105)
    ├── contacts/
    │   ├── __init__.py      (13)
    │   ├── contacts.py      (160)  ⚠️ NEAR LIMIT
    │   └── contacts_write.py (157)
    ├── calendar/
    │   ├── __init__.py      (14)
    │   ├── caldav.py        (180)  ⚠️ NEAR LIMIT
    │   ├── caldav_get_event.py (60)
    │   └── caldav_write.py  (159)
    └── files/
        ├── __init__.py      (13)
        ├── webdav.py        (137)
        └── webdav_write.py  (101)

tests/
├── __init__.py              (1)
├── conftest.py              (17)
├── test_registration.py     (111)
├── test_optional_dav.py     (113)
├── test_imports.py          (83)
├── test_ssrf_validation.py  (245)  🚨 OVER LIMIT
├── test_dav_client.py       (240)  🚨 OVER LIMIT
├── test_exception_handling.py (104)
├── test_redirect_blocking.py (54)
├── mail/
│   ├── test_setup_project.py (233) 🚨 OVER LIMIT
│   ├── test_actions.py      (256)  🚨 OVER LIMIT
│   ├── test_masked_email.py (271)  🚨 OVER LIMIT
│   ├── test_send.py         (236)  🚨 OVER LIMIT
│   ├── test_reply.py        (217)  🚨 OVER LIMIT
│   ├── test_mailbox.py      (255)  🚨 OVER LIMIT
│   ├── test_forward.py      (202)  🚨 OVER LIMIT
│   ├── test_email.py        (200)  🚨 OVER LIMIT
│   ├── test_parse.py        (187)  ⚠️ NEAR LIMIT
│   ├── test_identities.py   (151)  ⚠️ NEAR LIMIT
│   ├── test_export.py       (119)
│   ├── test_import.py       (120)
│   ├── test_attachments.py  (134)
│   ├── test_snippets.py     (102)
│   ├── test_set_errors.py   (98)
│   ├── test_pin_email.py    (76)
│   ├── test_thread.py       (80)
│   └── test_labels.py       (74)
├── contacts/
│   ├── test_contacts.py     (110)
│   ├── test_contacts_get.py (93)
│   ├── test_contacts_query.py (102)
│   ├── test_contacts_list.py (92)
│   ├── test_contacts_create.py (91)
│   ├── test_contacts_update.py (98)
│   └── test_contacts_delete.py (78)
├── calendar/
│   ├── test_caldav.py       (337)  🚨 OVER LIMIT
│   ├── test_caldav_get_event.py (140)
│   └── test_caldav_write.py (237)  🚨 OVER LIMIT
└── files/
    ├── test_webdav.py       (132)
    ├── test_webdav_write.py (110)
    └── test_path_traversal.py (68)
```

Note: Cross-cutting tests at root: `test_dav_client.py`, `test_exception_handling.py`,
`test_imports.py`, `test_optional_dav.py`, `test_redirect_blocking.py`,
`test_registration.py`, `test_ssrf_validation.py`.

## Registered Tools (48 total)
Mail (29): `health_check`, `mail_list_mailboxes`, `mail_create_mailbox`, `mail_rename_mailbox`,
`mail_delete_mailbox`, `mail_get_email`, `mail_search_emails`, `mail_get_recent_emails`,
`mail_get_email_thread`, `mail_mark_email_read`, `mail_move_email`, `mail_delete_email`,
`mail_archive_email`, `mail_pin_email`, `mail_list_identities`, `mail_set_identity`,
`mail_send_email`, `mail_reply_to_email`, `mail_forward_email`, `mail_manage_email_labels`,
`mail_list_masked_emails`, `mail_create_masked_email`, `mail_update_masked_email`,
`mail_download_attachment`, `mail_upload_attachment`,
`mail_search_snippets`, `mail_export_email`, `mail_import_email`, `mail_parse_email`

Contacts (7): `contacts_list_address_books`,
`contacts_get_contact`, `contacts_query_contacts`, `contacts_list`, `contacts_create_contact`,
`contacts_update_contact`, `contacts_delete_contact`

Calendar (6, DAV only): `calendar_list_calendars`, `calendar_list_events`, `calendar_get_event`,
`calendar_create_event`, `calendar_update_event`, `calendar_delete_event`

Files (6, DAV only): `files_list`, `files_get`, `files_upload`, `files_create_folder`,
`files_delete`, `files_move`
