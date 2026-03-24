"""Mail tools subpackage."""

from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.client import JMAPClient


def register_all(server: FastMCP, client: JMAPClient) -> None:
    """Register all mail tools with the server."""
    from . import (
        actions,
        attachments,
        email,
        export,
        forward,
        health,
        identities,
        import_,
        labels,
        mailbox,
        masked_email,
        parse,
        reply,
        send,
        snippets,
        thread,
    )

    health.register(server, client)
    mailbox.register(server, client)
    email.register(server, client)
    thread.register(server, client)
    actions.register(server, client)
    identities.register(server, client)
    send.register(server, client)
    reply.register(server, client)
    forward.register(server, client)
    labels.register(server, client)
    masked_email.register(server, client)
    attachments.register(server, client)
    snippets.register(server, client)
    export.register(server, client)
    import_.register(server, client)
    parse.register(server, client)
