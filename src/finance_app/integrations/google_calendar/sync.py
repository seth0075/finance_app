import json
import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httplib2
import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sqlalchemy import delete

from finance_app.features.calendar.models import HiddenCalendar
from finance_app.integrations.google_calendar.models import (
    GoogleCache,
    GoogleCalendar,
    GoogleEvent,
)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SERVICE = "PersonalDashboard.GoogleCalendar"
ACCOUNT = "oauth"


def connect(client_file):
    flow = InstalledAppFlow.from_client_secrets_file(
        client_file, SCOPES, autogenerate_code_verifier=True
    )
    # The OAuth library's INFO request log includes the authorization code.
    flow_logger = logging.getLogger("google_auth_oauthlib.flow")
    previous_level = flow_logger.level
    flow_logger.setLevel(logging.WARNING)
    try:
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
            timeout_seconds=180,
            authorization_prompt_message=None,
        )
    finally:
        flow_logger.setLevel(previous_level)
    keyring.set_password(SERVICE, ACCOUNT, credentials.to_json())
    return credentials


def load_credentials():
    value = keyring.get_password(SERVICE, ACCOUNT)
    return (
        Credentials.from_authorized_user_info(json.loads(value), SCOPES)
        if value
        else None
    )


def forget_credentials():
    if keyring.get_password(SERVICE, ACCOUNT):
        keyring.delete_password(SERVICE, ACCOUNT)


def local_datetime(value, default_zone):
    result = datetime.fromisoformat(value["dateTime"])
    if result.tzinfo is None:
        result = result.replace(tzinfo=ZoneInfo(value.get("timeZone", default_zone)))
    return result.astimezone().replace(tzinfo=None)


def fetch(credentials, today=None):
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        keyring.set_password(SERVICE, ACCOUNT, credentials.to_json())
    http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
    service = build("calendar", "v3", http=http, cache_discovery=False)
    today = today or date.today()
    start = today - timedelta(days=365)
    end = today + timedelta(days=365)
    # All-day events are filtered in their calendar's timezone, which may
    # differ from the computer's timezone by more than one day.
    start_time = (
        datetime.combine(start - timedelta(days=2), time.min)
        .astimezone()
        .astimezone(UTC)
    )
    end_time = (
        datetime.combine(end + timedelta(days=3), time.min).astimezone().astimezone(UTC)
    )
    calendars, events = [], []
    calendar_resource = service.calendarList()
    request = calendar_resource.list(showHidden=True, maxResults=250)
    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            color = item.get("backgroundColor", "#7395F5")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                raise ValueError("Google returned an invalid calendar color.")
            calendar_id = item["id"]
            calendars.append(
                GoogleCalendar(
                    id=calendar_id,
                    name=item.get("summaryOverride")
                    or item.get("summary")
                    or "(Unnamed calendar)",
                    color=color.upper(),
                )
            )
            event_resource = service.events()
            event_request = event_resource.list(
                calendarId=calendar_id,
                singleEvents=True,
                showDeleted=False,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                maxResults=2500,
            )
            while event_request is not None:
                event_response = event_request.execute()
                for event in event_response.get("items", []):
                    if event.get("status") == "cancelled":
                        continue
                    event_start, event_end = event["start"], event["end"]
                    all_day = "date" in event_start
                    if all_day:
                        starts_at = datetime.combine(
                            date.fromisoformat(event_start["date"]), time.min
                        )
                        ends_at = datetime.combine(
                            date.fromisoformat(event_end["date"]) - timedelta(days=1),
                            time.min,
                        )
                    else:
                        starts_at = local_datetime(
                            event_start, item.get("timeZone", "UTC")
                        )
                        ends_at = local_datetime(event_end, item.get("timeZone", "UTC"))
                    events.append(
                        GoogleEvent(
                            id=event["id"],
                            calendar_id=calendar_id,
                            title=event.get("summary") or "(No title)",
                            starts_at=starts_at,
                            ends_at=ends_at,
                            all_day=all_day,
                        )
                    )
                event_request = event_resource.list_next(event_request, event_response)
        request = calendar_resource.list_next(request, response)
    return calendars, events, start, end


def replace_cache(session, snapshot):
    calendars, events, start, end = snapshot
    session.execute(delete(GoogleEvent))
    session.execute(delete(GoogleCalendar))
    session.execute(delete(GoogleCache))
    session.add_all(calendars)
    session.add_all(events)
    session.add(
        GoogleCache(id=1, starts_on=start, ends_on=end, synced_at=datetime.now())
    )
    session.commit()


def clear_cache(session):
    session.execute(delete(GoogleEvent))
    session.execute(delete(GoogleCalendar))
    session.execute(delete(GoogleCache))
    session.execute(
        delete(HiddenCalendar).where(HiddenCalendar.calendar_id.startswith("google:"))
    )
    session.commit()
