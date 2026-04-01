# Issues

<!-- Reviewer: flag real problems only. Don't invent issues. -->

## Test Files Over Size Limit
Several test files exceed 400 lines (test limit per testing.md):
None currently exceed 400 lines.

Several test files exceed 200 lines (soft guideline):
- `tests/calendar/test_caldav.py` (337) 🚨
- `tests/mail/test_masked_email.py` (271) 🚨
- `tests/mail/test_actions.py` (256) 🚨
- `tests/mail/test_mailbox.py` (255) 🚨
- `tests/test_ssrf_validation.py` (245) 🚨
- `tests/test_dav_client.py` (240) 🚨
- `tests/calendar/test_caldav_write.py` (237) 🚨
- `tests/mail/test_send.py` (236) 🚨
- `tests/mail/test_setup_project.py` (233) 🚨
- `tests/mail/test_reply.py` (217) 🚨
- `tests/mail/test_forward.py` (202) 🚨
- `tests/mail/test_email.py` (200) 🚨

`tests/mail/test_parse.py` (187) is near the limit — will exceed on next additions.

## AGENT_TODO Checkbox Drift
Three items are marked DONE in `AGENT_TODO.md` but have unchecked sub-items:
- `mail_export_email` — "Add tests" unchecked, but `test_export.py` (119 lines, 6 tests) exists and passes
- `mail_parse_email` — "Add tests" unchecked, but `test_parse.py` (187 lines, 7 tests) exists and passes
- `optional_dav_credentials` — "Add tests" unchecked, but `test_optional_dav.py` (113 lines, 9 tests) exists and passes
- `mail_pin_email` — "Update README tools table" unchecked; README now includes `mail_pin_email`

## Inconsistencies (low priority)
- `test_mailbox.py` uses `@pytest.fixture` while most others use plain functions
- `test_labels.py` and `test_thread.py` hardcode tool name in `_tool(client)`
- Duplicated `mock_client()`/`_tool()` across mail test files — shared conftest would help

## ~~test_contacts_write.py Over Size Limit~~ — RESOLVED
`test_contacts_write.py` removed entirely when `contacts_set_address_book` was removed.
`contacts/` test suite now has no files over the limit.

## ~~Source File Over Size Limit~~ — RESOLVED
`contacts_write.py` dropped from 255 to 157 lines after `contacts_set_address_book` removal.

## ~~Pending Work: remove_contacts_set_address_book~~ — RESOLVED
`contacts_set_address_book` removed from `contacts_write.py`, registration, tests, README, CHANGELOG.

## ~~mail_set_error_handling~~ — RESOLVED
`test_set_errors.py` (98 lines) added — tests `_humanize_errors`, `tooManyKeywords`,
`tooManyMailboxes` in `actions.py`/`labels.py`.

## ~~README Out of Date~~ — RESOLVED
README now includes all current tools: `mail_pin_email`, `mail_search_snippets`,
`mail_update_masked_email`, `mail_export_email`, `mail_import_email`, `mail_parse_email`,
`mail_set_identity`.

## ~~Failing Tests: test_registration.py~~ — RESOLVED
## ~~mail_send_error_handling~~ — RESOLVED
## ~~mail_mailbox_error_handling~~ — RESOLVED
## ~~optional_dav_credentials~~ — RESOLVED
## ~~masked_email_create_state_default~~ — RESOLVED
## ~~mail_set_identity~~ — RESOLVED
## ~~mail_parse_email~~ — RESOLVED
## ~~mail_import_email~~ — RESOLVED
## ~~mail_export_email~~ — RESOLVED
## ~~mail_get_email_headers~~ — RESOLVED
## ~~masked_email_fixes~~ — RESOLVED
## ~~fix_set_address_book_capability_check~~ — RESOLVED
## ~~remove_contacts_copy~~ — RESOLVED
## ~~remove_contacts_changes~~ — RESOLVED
## ~~mail_search_snippets~~ — RESOLVED
## ~~vacation_response_removed~~ — RESOLVED
## ~~fix_list_address_books_query~~ — RESOLVED
## ~~mail_pin_email Missing Tests~~ — RESOLVED
## ~~contacts_* Missing~~ — RESOLVED (all 7 CRUD tools tested)
## ~~Missing Input Validation~~ — FIXED
## ~~Missing Credential Validation~~ — FIXED
## ~~Broad Exception Handling~~ — FIXED
## ~~DAV Discovery Broken~~ — FIXED
## ~~Files Over Size Limit (source)~~ — FIXED
## ~~H1_webdav_ssrf_validation~~ — RESOLVED (test_ssrf_validation.py, 245 lines)
## ~~M1_redirect_credential_leak~~ — RESOLVED (test_redirect_blocking.py, 54 lines)
## ~~L4_path_traversal_guard~~ — RESOLVED (test_path_traversal.py, 68 lines, 7 tests)
## ~~Pending Security Items (L4)~~ — RESOLVED
