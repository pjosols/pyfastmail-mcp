# pyfastmail-mcp

An [MCP](https://modelcontextprotocol.io/) server that gives AI assistants full access to your Fastmail account — email, contacts, calendars, and file storage.

> ⚠️ **This server can send email, delete messages, and modify contacts/calendars on your behalf.** AI assistants may act on content from untrusted sources (emails, web pages, files) which could contain prompt injection attacks. Review tool calls before approving them, especially actions that send email or delete data.

## Features

| Domain | Protocol | Tools |
|--------|----------|-------|
| Mail | JMAP | Send, reply, forward, search, read, pin, archive, keywords, masked email, attachments, threads, import/export, identities |
| Contacts | JMAP | List address books, CRUD contacts, query |
| Calendar | CalDAV | List calendars, CRUD events (optional — requires app password) |
| Files | WebDAV | List, upload, download, move, delete, create folders (optional — requires app password) |

## Installation

```bash
pip install pyfastmail-mcp
```

Or run directly with `uvx`:

```bash
uvx pyfastmail-mcp
```

## Configuration

### 1. Get Fastmail Credentials

You need an API token from Fastmail. An app password is optional (only needed for calendar and file storage).

- **API Token** (required — mail and contacts): [Fastmail Settings → Privacy & Security → API Tokens](https://app.fastmail.com/settings/security/tokens) — enable the `urn:ietf:params:jmap:contacts` capability
- **App Password** (optional — calendars and files): [Fastmail Settings → Privacy & Security → App Passwords](https://app.fastmail.com/settings/security/passwords) — create one with the **"DAV (CardDAV, CalDAV, WebDAV)"** scope

If you only set the API token, the server starts with mail and contacts tools. Calendar and file tools are registered only when the app password is also provided.

### 2. Set Environment Variables

```bash
export FASTMAIL_API_TOKEN="fmu1-..."
export FASTMAIL_APP_PASSWORD="your-app-password"
export FASTMAIL_EMAIL="you@fastmail.com"
```

### 3. Add to Your MCP Client

For Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fastmail": {
      "command": "uvx",
      "args": ["pyfastmail-mcp"],
      "env": {
        "FASTMAIL_API_TOKEN": "fmu1-...",
        "FASTMAIL_APP_PASSWORD": "your-app-password",
        "FASTMAIL_EMAIL": "you@fastmail.com"
      }
    }
  }
}
```

For Kiro CLI, add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "fastmail": {
      "command": "uvx",
      "args": ["pyfastmail-mcp"],
      "env": {
        "FASTMAIL_API_TOKEN": "${FASTMAIL_API_TOKEN}",
        "FASTMAIL_EMAIL": "${FASTMAIL_EMAIL}",
        "FASTMAIL_APP_PASSWORD": "${FASTMAIL_APP_PASSWORD}"
      }
    }
  }
}
```

## Tools

### Mail (`mail_*`)

| Tool | Description |
|------|-------------|
| `health_check` | Verify connection and auth |
| `mail_list_mailboxes` | List all mailboxes (folders/labels) |
| `mail_create_mailbox` | Create a mailbox |
| `mail_rename_mailbox` | Rename a mailbox |
| `mail_delete_mailbox` | Delete a mailbox |
| `mail_get_email` | Get email by ID (with optional headers) |
| `mail_get_recent_emails` | Get recent emails |
| `mail_search_emails` | Search by query |
| `mail_search_snippets` | Highlighted search result snippets |
| `mail_get_email_thread` | Get full thread |
| `mail_mark_email_read` | Mark read/unread |
| `mail_pin_email` | Pin/unpin (flag/star) |
| `mail_move_email` | Move to mailbox |
| `mail_delete_email` | Move to trash or permanently delete |
| `mail_archive_email` | Archive |
| `mail_manage_email_labels` | Add/remove keywords |
| `mail_export_email` | Download raw .eml file |
| `mail_import_email` | Import .eml into mail store |
| `mail_parse_email` | Parse a blob as email without importing |
| `mail_list_identities` | List send-as identities |
| `mail_set_identity` | Create/update/delete identities |
| `mail_send_email` | Send new email |
| `mail_reply_to_email` | Reply to email |
| `mail_forward_email` | Forward email |
| `mail_list_masked_emails` | List masked emails |
| `mail_create_masked_email` | Create masked email |
| `mail_update_masked_email` | Update masked email state, domain, description, or URL |
| `mail_download_attachment` | Download attachment |
| `mail_upload_attachment` | Upload blob for sending |

### Contacts (`contacts_*`)

| Tool | Description |
|------|-------------|
| `contacts_list_address_books` | List address books |
| `contacts_list` | List contacts (query+get combo) |
| `contacts_get_contact` | Get contact(s) by ID |
| `contacts_query_contacts` | Query contacts with filters and sorting |
| `contacts_create_contact` | Create contact |
| `contacts_update_contact` | Update contact fields |
| `contacts_delete_contact` | Delete contact(s) |

### Calendar (`calendar_*`)

| Tool | Description |
|------|-------------|
| `calendar_list_calendars` | List calendars |
| `calendar_list_events` | List events |
| `calendar_get_event` | Get event details |
| `calendar_create_event` | Create event |
| `calendar_update_event` | Update event |
| `calendar_delete_event` | Delete event |

### Files (`files_*`)

| Tool | Description |
|------|-------------|
| `files_list` | List files/folders |
| `files_get` | Download file |
| `files_upload` | Upload file |
| `files_create_folder` | Create folder |
| `files_move` | Move/rename file |
| `files_delete` | Delete file/folder |

## Development

```bash
git clone https://github.com/pjosols/pyfastmail-mcp.git
cd pyfastmail-mcp
uv sync --group dev
uv run pytest
```

## License

MIT
