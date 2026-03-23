"""CalDAV get_event tool."""

import json

import icalendar
import requests
from mcp.server.fastmcp import FastMCP

from pyfastmail_mcp.dav_client import CALDAV_BASE, DAVClient
from pyfastmail_mcp.exceptions import FastmailError


def _parse_event_full(ical_text: str, href: str) -> dict:
    """Parse a single iCalendar resource into a detailed event dict."""
    cal = icalendar.Calendar.from_ical(ical_text)
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        dtstart = comp.get("DTSTART")
        dtend = comp.get("DTEND")
        attendees_raw = comp.get("ATTENDEE")
        if attendees_raw is None:
            attendees = []
        elif isinstance(attendees_raw, list):
            attendees = [str(a) for a in attendees_raw]
        else:
            attendees = [str(attendees_raw)]
        rrule = comp.get("RRULE")
        return {
            "href": href,
            "uid": str(comp.get("UID", "")),
            "summary": str(comp.get("SUMMARY", "")),
            "dtstart": str(dtstart.dt) if dtstart else "",
            "dtend": str(dtend.dt) if dtend else "",
            "location": str(comp.get("LOCATION", "")),
            "description": str(comp.get("DESCRIPTION", "")),
            "attendees": attendees,
            "rrule": str(rrule.to_ical().decode()) if rrule else "",
            "status": str(comp.get("STATUS", "")),
            "organizer": str(comp.get("ORGANIZER", "")),
        }
    return {}


def register(server: FastMCP, dav_client: DAVClient) -> None:
    @server.tool()
    async def calendar_get_event(href: str) -> str:
        """Get full details of a single CalDAV event by its href.

        Args:
            href: The href/URL path of the .ics resource (as returned by calendar_list_events).
        """
        try:
            url = href if href.startswith("http") else f"{CALDAV_BASE}{href}"
            dav_client.validate_dav_url(url)
            resp = dav_client.get(url)
            event = _parse_event_full(resp.text, href)
            return json.dumps(event, indent=2)
        except (FastmailError, requests.RequestException, ValueError) as exc:
            return json.dumps({"error": str(exc)})
