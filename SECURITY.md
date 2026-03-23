# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately via [GitHub Security Advisories](https://github.com/pjosols/pyfastmail-mcp/security/advisories/new).

Do **not** open a public issue for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Credential Handling

This server requires Fastmail credentials passed via environment variables:

- `FASTMAIL_API_TOKEN` — JMAP Bearer token (mail operations)
- `FASTMAIL_APP_PASSWORD` — App-specific password (CardDAV/CalDAV/WebDAV)
- `FASTMAIL_EMAIL` — Account email address

**Never commit credentials to version control.** Use `.env` files (excluded via `.gitignore`) or your system's secret manager.

## Security Measures

- **SSRF protection**: All user-provided URLs are validated against expected DAV base URLs before authenticated requests are made.
- **Input validation**: HTTP header values (e.g., `Depth`) are validated against allowlists.
- **Download size limits**: File downloads are capped to prevent memory exhaustion.
- **No credential forwarding**: `requests.Session` auth is scoped to known Fastmail hostnames only.
