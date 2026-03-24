"""JMAPClient — all Fastmail API communication."""

import os
from typing import Any

import requests

from pyfastmail_mcp.exceptions import AuthenticationError, JMAPError

JMAP_SESSION_URL = "https://api.fastmail.com/jmap/session"
JMAP_API_URL = "https://api.fastmail.com/jmap/api/"

USING_MAIL = [
    "urn:ietf:params:jmap:core",
    "urn:ietf:params:jmap:mail",
]
USING_SUBMISSION = USING_MAIL + ["urn:ietf:params:jmap:submission"]
USING_MASKED_EMAIL = USING_MAIL + ["https://www.fastmail.com/dev/maskedemail"]
USING_CONTACTS = ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:contacts"]


class JMAPClient:
    """Stateful JMAP client with session reuse."""

    def __init__(self, api_token: str | None = None):
        self._token = api_token or os.environ.get("FASTMAIL_API_TOKEN", "")
        if not self._token:
            raise AuthenticationError("FASTMAIL_API_TOKEN is not set")
        self._session_data: dict | None = None
        self._http = requests.Session()
        self._http.max_redirects = 0
        self._http.headers.update({"Authorization": f"Bearer {self._token}"})

    @property
    def account_id(self) -> str:
        return self._get_session()["primaryAccounts"]["urn:ietf:params:jmap:mail"]

    def _get_session(self) -> dict:
        if self._session_data is None:
            resp = self._http.get(JMAP_SESSION_URL)
            if resp.status_code == 401:
                raise AuthenticationError("Invalid API token")
            resp.raise_for_status()
            self._session_data = resp.json()
        return self._session_data

    def call(self, using: list[str], method_calls: list) -> list:
        """Execute a JMAP API request and return method responses."""
        payload = {"using": using, "methodCalls": method_calls}
        resp = self._http.post(JMAP_API_URL, json=payload)
        resp.raise_for_status()
        responses = resp.json().get("methodResponses", [])
        for name, data, _ in responses:
            if name == "error":
                raise JMAPError(name, data.get("type", ""), data.get("description", ""))
        return responses

    def query_and_get(
        self,
        type_: str,
        filter_: dict | None,
        properties: list[str],
        using: list[str] | None = None,
        sort: list[dict] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Run a query+get in one round trip, return list of objects."""
        account_id = self.account_id
        query_args: dict[str, Any] = {"accountId": account_id}
        if filter_:
            query_args["filter"] = filter_
        if sort:
            query_args["sort"] = sort
        if limit is not None:
            query_args["limit"] = limit

        get_args: dict[str, Any] = {
            "accountId": account_id,
            "#ids": {
                "resultOf": "q",
                "name": f"{type_}/query",
                "path": "/ids",
            },
            "properties": properties,
        }

        responses = self.call(
            using or USING_MAIL,
            [
                [f"{type_}/query", query_args, "q"],
                [f"{type_}/get", get_args, "g"],
            ],
        )
        _, get_data, _ = responses[1]
        return get_data.get("list", [])

    def set(
        self,
        type_: str,
        create: dict | None = None,
        update: dict | None = None,
        destroy: list | None = None,
        using: list[str] | None = None,
    ) -> dict:
        """Run a /set call and return the response data."""
        account_id = self.account_id
        args: dict[str, Any] = {"accountId": account_id}
        if create:
            args["create"] = create
        if update:
            args["update"] = update
        if destroy:
            args["destroy"] = destroy

        responses = self.call(
            using or USING_MAIL,
            [[f"{type_}/set", args, "s"]],
        )
        _, data, _ = responses[0]
        return data

    def get_mailbox_by_name(self, name: str) -> dict:
        """Return mailbox dict for the given name, or raise MailboxNotFoundError."""
        from pyfastmail_mcp.exceptions import MailboxNotFoundError

        mailboxes = self.query_and_get("Mailbox", None, ["id", "name"])
        for mb in mailboxes:
            if mb.get("name", "").lower() == name.lower():
                return mb
        raise MailboxNotFoundError(f"Mailbox not found: {name!r}")

    def get_mailbox_by_role(self, role: str) -> dict:
        """Return mailbox dict for the given role, or raise MailboxNotFoundError."""
        from pyfastmail_mcp.exceptions import MailboxNotFoundError

        mailboxes = self.query_and_get("Mailbox", None, ["id", "name", "role"])
        for mb in mailboxes:
            if mb.get("role") == role:
                return mb
        raise MailboxNotFoundError(f"Mailbox with role {role!r} not found")
