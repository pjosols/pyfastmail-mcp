"""Tests for setup_project: JMAPClient, exceptions, server, health_check."""

import json
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests

from pyfastmail_mcp.exceptions import (
    AuthenticationError,
    FastmailError,
    IdentityNotFoundError,
    JMAPError,
    MailboxNotFoundError,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


def test_exception_hierarchy():
    assert issubclass(AuthenticationError, FastmailError)
    assert issubclass(JMAPError, FastmailError)
    assert issubclass(MailboxNotFoundError, FastmailError)
    assert issubclass(IdentityNotFoundError, FastmailError)


def test_jmap_error_message():
    err = JMAPError("Email/get", "notFound", "No such email")
    assert "Email/get" in str(err)
    assert "notFound" in str(err)
    assert err.method == "Email/get"
    assert err.error_type == "notFound"
    assert err.description == "No such email"


# ---------------------------------------------------------------------------
# JMAPClient construction
# ---------------------------------------------------------------------------


def test_client_raises_without_token(monkeypatch):
    monkeypatch.delenv("FASTMAIL_API_TOKEN", raising=False)
    from pyfastmail_mcp.client import JMAPClient

    with pytest.raises(AuthenticationError):
        JMAPClient()


def test_client_accepts_explicit_token():
    from pyfastmail_mcp.client import JMAPClient

    client = JMAPClient(api_token="test-token")
    assert client._token == "test-token"


def test_client_reads_env_token(monkeypatch):
    monkeypatch.setenv("FASTMAIL_API_TOKEN", "env-token")
    from pyfastmail_mcp.client import JMAPClient

    client = JMAPClient()
    assert client._token == "env-token"


# ---------------------------------------------------------------------------
# JMAPClient._get_session
# ---------------------------------------------------------------------------


def _make_client():
    from pyfastmail_mcp.client import JMAPClient

    return JMAPClient(api_token="tok")


def _mock_response(json_data=None, status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


SESSION_PAYLOAD = {"primaryAccounts": {"urn:ietf:params:jmap:mail": "acc1"}}


def test_get_session_caches():
    client = _make_client()
    with patch.object(
        client._http, "get", return_value=_mock_response(SESSION_PAYLOAD)
    ) as mock_get:
        s1 = client._get_session()
        s2 = client._get_session()
    assert s1 is s2
    assert mock_get.call_count == 1


def test_get_session_401_raises():
    client = _make_client()
    with patch.object(
        client._http, "get", return_value=_mock_response(status_code=401)
    ):
        with pytest.raises(AuthenticationError):
            client._get_session()


def test_account_id():
    client = _make_client()
    payload = {"primaryAccounts": {"urn:ietf:params:jmap:mail": "acc42"}}
    with patch.object(client._http, "get", return_value=_mock_response(payload)):
        assert client.account_id == "acc42"


# ---------------------------------------------------------------------------
# JMAPClient.call
# ---------------------------------------------------------------------------


def test_call_returns_responses():
    client = _make_client()
    api_resp = {"methodResponses": [["Mailbox/get", {"list": []}, "g"]]}
    with patch.object(
        client._http, "get", return_value=_mock_response(SESSION_PAYLOAD)
    ):
        with patch.object(client._http, "post", return_value=_mock_response(api_resp)):
            responses = client.call(
                ["urn:ietf:params:jmap:mail"], [["Mailbox/get", {}, "g"]]
            )
    assert responses[0][0] == "Mailbox/get"


def test_call_raises_on_error_response():
    client = _make_client()
    api_resp = {
        "methodResponses": [
            ["error", {"type": "unknownMethod", "description": "bad"}, "g"]
        ]
    }
    with patch.object(
        client._http, "get", return_value=_mock_response(SESSION_PAYLOAD)
    ):
        with patch.object(client._http, "post", return_value=_mock_response(api_resp)):
            with pytest.raises(JMAPError) as exc_info:
                client.call(["urn:ietf:params:jmap:mail"], [["Mailbox/get", {}, "g"]])
    assert exc_info.value.error_type == "unknownMethod"


# ---------------------------------------------------------------------------
# JMAPClient.query_and_get
# ---------------------------------------------------------------------------


def test_query_and_get():
    client = _make_client()
    api_resp = {
        "methodResponses": [
            ["Mailbox/query", {"ids": ["mb1"]}, "q"],
            ["Mailbox/get", {"list": [{"id": "mb1", "name": "Inbox"}]}, "g"],
        ]
    }
    with patch.object(
        client._http, "get", return_value=_mock_response(SESSION_PAYLOAD)
    ):
        with patch.object(client._http, "post", return_value=_mock_response(api_resp)):
            result = client.query_and_get("Mailbox", None, ["id", "name"])
    assert result == [{"id": "mb1", "name": "Inbox"}]


# ---------------------------------------------------------------------------
# JMAPClient.set
# ---------------------------------------------------------------------------


def test_set():
    client = _make_client()
    api_resp = {"methodResponses": [["Email/set", {"updated": {"e1": None}}, "s"]]}
    with patch.object(
        client._http, "get", return_value=_mock_response(SESSION_PAYLOAD)
    ):
        with patch.object(client._http, "post", return_value=_mock_response(api_resp)):
            data = client.set("Email", update={"e1": {"keywords/$seen": True}})
    assert data["updated"] == {"e1": None}


# ---------------------------------------------------------------------------
# health_check tool
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    client = MagicMock()
    client._get_session.return_value = {"primaryAccounts": {}}
    client.account_id = "acc99"
    return client


@pytest.mark.asyncio
async def test_health_check_ok(mock_client):
    from mcp.server.fastmcp import FastMCP

    from pyfastmail_mcp.tools.mail.health import register

    server = FastMCP("test")
    register(server, mock_client)

    tool_fn = server._tool_manager._tools["health_check"].fn
    result = await tool_fn()
    data = json.loads(result)
    assert data["status"] == "ok"
    assert data["account_id"] == "acc99"


@pytest.mark.asyncio
async def test_health_check_error(mock_client):
    from mcp.server.fastmcp import FastMCP

    from pyfastmail_mcp.tools.mail.health import register

    type(mock_client).account_id = PropertyMock(side_effect=AuthenticationError("bad token"))
    server = FastMCP("test")
    register(server, mock_client)

    tool_fn = server._tool_manager._tools["health_check"].fn
    result = await tool_fn()
    data = json.loads(result)
    assert data["status"] == "error"
    assert "bad token" in data["message"]
