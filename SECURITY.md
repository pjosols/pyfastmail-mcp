# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately via [GitHub Security Advisories](https://github.com/pjosols/pyfastmail-mcp/security/advisories/new).

Do **not** open a public issue for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅        |
| 0.1.x   | ❌        |

## Credential Handling

This server requires Fastmail credentials passed via environment variables:

- `FASTMAIL_API_TOKEN` — JMAP Bearer token (mail, contacts) — **required**
- `FASTMAIL_APP_PASSWORD` — App-specific password (CalDAV/WebDAV) — optional
- `FASTMAIL_EMAIL` — Account email address — optional (required if app password is set)

If only the API token is provided, the server starts with mail and contacts tools. Calendar and file tools require the app password.

**Never commit credentials to version control.** Use `.env` files (excluded via `.gitignore`) or your system's secret manager.

## Protocol Surface

| Domain | Protocol | Auth |
|--------|----------|------|
| Mail | JMAP | Bearer token |
| Contacts | JMAP | Bearer token |
| Calendar | CalDAV | Basic auth (app password) |
| Files | WebDAV | Basic auth (app password) |

## Security Measures

- **SSRF protection**: All user-provided URLs are validated against expected base URLs (JMAP API hostnames and DAV base URLs) before authenticated requests are made.
- **Input validation**: HTTP header values (e.g., `Depth`) are validated against allowlists.
- **Download size limits**: File downloads are capped to prevent memory exhaustion.
- **No credential forwarding**: `requests.Session` auth is scoped to known Fastmail hostnames only.
