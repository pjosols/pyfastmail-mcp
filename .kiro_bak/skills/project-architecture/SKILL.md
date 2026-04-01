# Project Architecture

## Package Layout
```
src/pyfastmail_mcp/
├── __init__.py
├── server.py            # FastMCP setup, registers all tool subpackages
├── client.py            # JMAPClient — JMAP API communication
├── dav_client.py        # DAVClient — CardDAV/CalDAV/WebDAV communication
├── exceptions.py        # Custom exception hierarchy
└── tools/
    ├── __init__.py      # register_all() wires up all subpackages
    ├── health.py        # Standalone health check
    ├── mail/            # JMAP mail tools
    │   ├── __init__.py  # register_all(server, client)
    │   └── *.py         # mailbox, email, send, reply, forward, etc.
    ├── contacts/        # CardDAV contact tools
    │   ├── __init__.py
    │   └── *.py
    ├── calendar/        # CalDAV calendar tools
    │   ├── __init__.py
    │   └── *.py
    └── files/           # WebDAV file tools
        ├── __init__.py
        └── *.py
```

## Key Patterns
- Two clients: `JMAPClient` (mail) and `DAVClient` (contacts/calendar/files)
- `server.py` creates both clients and passes them to `register_all()`
- Each subpackage has `register_all(server, client)` that registers its tools
- Tool names are prefixed by domain: `mail_*`, `contacts_*`, `calendar_*`, `files_*`
- Tools are thin: validate input → call client → format output

## Adding a New Tool
1. Add the function in the right subpackage (e.g. `tools/mail/`)
2. Register in that subpackage's `__init__.py`
3. Tests go in `tests/mail/`, `tests/contacts/`, etc.
