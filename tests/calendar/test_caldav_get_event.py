"""Tests for calendar_get_event in tools/calendar/caldav.py."""

import json
from unittest.mock import MagicMock

import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.tools.calendar.caldav import register


def _client():
    c = MagicMock()
    c.email = "user@example.com"
    return c


def _tool(client, name):
    server = FastMCP("test")
    register(server, client)
    return server._tool_manager._tools[name].fn


def _mock_response(text: str):
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


_ICAL_FULL = """\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event-uid-1@fastmail.com
SUMMARY:Board Meeting
DTSTART:20260401T140000Z
DTEND:20260401T150000Z
LOCATION:Room 42
DESCRIPTION:Quarterly review
ORGANIZER:mailto:boss@example.com
ATTENDEE:mailto:alice@example.com
ATTENDEE:mailto:bob@example.com
STATUS:CONFIRMED
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
END:VCALENDAR"""

_HREF = "/dav/calendars/user/user@example.com/default/event1.ics"


async def test_get_event_returns_full_details():
    client = _client()
    client.get.return_value = _mock_response(_ICAL_FULL)
    fn = _tool(client, "calendar_get_event")

    result = json.loads(await fn(href=_HREF))

    assert result["uid"] == "event-uid-1@fastmail.com"
    assert result["summary"] == "Board Meeting"
    assert "2026-04-01" in result["dtstart"]
    assert result["location"] == "Room 42"
    assert result["description"] == "Quarterly review"
    assert result["status"] == "CONFIRMED"
    assert "boss@example.com" in result["organizer"]
    assert len(result["attendees"]) == 2
    assert result["rrule"] != ""
    assert result["href"] == _HREF


async def test_get_event_prepends_caldav_base_for_relative_href():
    from pyfastmail_mcp.dav_client import CALDAV_BASE

    client = _client()
    client.get.return_value = _mock_response(_ICAL_FULL)
    fn = _tool(client, "calendar_get_event")

    await fn(href=_HREF)

    url = client.get.call_args[0][0]
    assert url == f"{CALDAV_BASE}{_HREF}"


async def test_get_event_uses_absolute_href_unchanged():
    abs_href = "https://caldav.fastmail.com/dav/calendars/user/user@example.com/default/event1.ics"
    client = _client()
    client.get.return_value = _mock_response(_ICAL_FULL)
    fn = _tool(client, "calendar_get_event")

    await fn(href=abs_href)

    url = client.get.call_args[0][0]
    assert url == abs_href


async def test_get_event_no_attendees():
    ical = """\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:solo@fastmail.com
SUMMARY:Solo Task
DTSTART:20260402T090000Z
DTEND:20260402T100000Z
END:VEVENT
END:VCALENDAR"""
    client = _client()
    client.get.return_value = _mock_response(ical)
    fn = _tool(client, "calendar_get_event")

    result = json.loads(await fn(href=_HREF))

    assert result["attendees"] == []
    assert result["rrule"] == ""
    assert result["organizer"] == ""


async def test_get_event_returns_error_on_exception():
    client = _client()
    client.get.side_effect = requests.RequestException("not found")
    fn = _tool(client, "calendar_get_event")

    result = json.loads(await fn(href=_HREF))

    assert "error" in result
    assert "not found" in result["error"]


async def test_get_event_empty_ical_returns_empty_dict():
    ical = """\
BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""
    client = _client()
    client.get.return_value = _mock_response(ical)
    fn = _tool(client, "calendar_get_event")

    result = json.loads(await fn(href=_HREF))

    assert result == {}
