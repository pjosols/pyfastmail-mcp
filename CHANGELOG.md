# Changelog

## 0.2.0 (2026-03-23)

### Breaking Changes
- Contacts migrated from CardDAV to JMAP (RFC 9610)
- CalDAV/WebDAV now optional — server starts with just mail + contacts if no app password set

### Added
- `mail_pin_email` — pin/unpin emails
- `mail_search_snippets` — highlighted search result snippets
- `mail_export_email` — download raw `.eml` files
- `mail_import_email` — import `.eml` into mail store
- `mail_parse_email` — parse a blob as email without importing
- `mail_set_identity` — create/update/delete sender identities
- `mail_get_email` — optional `headers` param (e.g. SimpleLogin headers)

## 0.1.0 (2026-03-22)

Initial release. 42 tools across JMAP (mail), CardDAV (contacts), CalDAV (calendars), and WebDAV (files).
