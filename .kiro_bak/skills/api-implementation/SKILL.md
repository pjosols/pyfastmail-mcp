# API Implementation

## JMAP (Mail, Masked Email)
- Endpoint: `https://api.fastmail.com/jmap/api/`
- Auth: `Authorization: Bearer {FASTMAIL_API_TOKEN}`
- All calls: POST with `using` and `methodCalls` arrays
- Query+Get pattern: combine in one round trip using `#ids` back-references
- Set pattern: `create`, `update`, `destroy` in one call
- URNs: `urn:ietf:params:jmap:mail`, `urn:ietf:params:jmap:submission`, `https://www.fastmail.com/dev/maskedemail`

## DAV Protocols (Contacts, Calendars, Files)
- Auth: Basic auth with `(FASTMAIL_EMAIL, FASTMAIL_APP_PASSWORD)` — app password, not API token
- Create `DAVClient` in `dav_client.py` with shared auth, base URLs, and DAV methods

### CardDAV (RFC 6352) — Contacts
- Server: `https://carddav.fastmail.com/dav/principals/user/{email}/`
- PROPFIND depth=1 to discover address books
- vCard format — use `vobject` library to parse/generate
- PUT with `Content-Type: text/vcard` to create, DELETE to remove

### CalDAV (RFC 4791) — Calendars
- Server: `https://caldav.fastmail.com/dav/principals/user/{email}/`
- PROPFIND depth=1 to discover calendars
- iCalendar format — use `icalendar` library to parse/generate
- REPORT with `calendar-query` + `time-range` filter for date queries
- PUT with `Content-Type: text/calendar` to create, DELETE to remove

### WebDAV (RFC 4918) — Files
- Server: `https://myfiles.fastmail.com/`
- PROPFIND depth=0 (self) or 1 (children), MKCOL for folders, PUT/GET/DELETE/MOVE for files

## References
- RFC 6352 (CardDAV): https://www.rfc-editor.org/rfc/rfc6352
- RFC 4791 (CalDAV): https://www.rfc-editor.org/rfc/rfc4791
- RFC 8621 (JMAP Mail): https://www.rfc-editor.org/rfc/rfc8621.html
