"""Smoke tests verifying all subpackage modules import without errors."""


def test_import_client():
    from pyfastmail_mcp.client import JMAPClient  # noqa: F401


def test_import_dav_client():
    from pyfastmail_mcp.dav_client import DAVClient  # noqa: F401


def test_import_exceptions():
    from pyfastmail_mcp.exceptions import (  # noqa: F401
        AuthenticationError,
        FastmailError,
        IdentityNotFoundError,
        JMAPError,
        MailboxNotFoundError,
    )


def test_import_tools_init():
    from pyfastmail_mcp.tools import register_all  # noqa: F401


def test_import_mail_subpackage():
    from pyfastmail_mcp.tools.mail import register_all  # noqa: F401


def test_import_contacts_subpackage():
    from pyfastmail_mcp.tools.contacts import register_all  # noqa: F401


def test_import_calendar_subpackage():
    from pyfastmail_mcp.tools.calendar import register_all  # noqa: F401


def test_import_files_subpackage():
    from pyfastmail_mcp.tools.files import register_all  # noqa: F401


def test_import_mail_modules():
    from pyfastmail_mcp.tools.mail import (  # noqa: F401
        actions,
        attachments,
        email,
        forward,
        health,
        identities,
        labels,
        mailbox,
        masked_email,
        reply,
        send,
        thread,
    )


def test_import_contacts_modules():
    from pyfastmail_mcp.tools.contacts import register_all  # noqa: F401


def test_using_contacts_constant_exists():
    from pyfastmail_mcp.client import USING_CONTACTS

    assert USING_CONTACTS == [
        "urn:ietf:params:jmap:core",
        "urn:ietf:params:jmap:contacts",
    ]


def test_carddav_modules_removed():
    import importlib

    for mod in (
        "pyfastmail_mcp.tools.contacts.carddav",
        "pyfastmail_mcp.tools.contacts.carddav_write",
    ):
        assert importlib.util.find_spec(mod) is None, f"{mod} should not exist"


def test_import_calendar_modules():
    from pyfastmail_mcp.tools.calendar import caldav  # noqa: F401
