"""Custom exception hierarchy for pyfastmail_mcp."""


class FastmailError(Exception):
    """Base exception for all Fastmail errors."""


class AuthenticationError(FastmailError):
    """Raised when API authentication fails."""


class JMAPError(FastmailError):
    """Raised when a JMAP method call returns an error."""

    def __init__(self, method: str, error_type: str, description: str = ""):
        self.method = method
        self.error_type = error_type
        self.description = description
        super().__init__(f"{method} failed [{error_type}]: {description}")


class MailboxNotFoundError(FastmailError):
    """Raised when a referenced mailbox does not exist."""


class IdentityNotFoundError(FastmailError):
    """Raised when a referenced sender identity does not exist."""
