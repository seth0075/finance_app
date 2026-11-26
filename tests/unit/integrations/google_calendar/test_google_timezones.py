import pytest

from finance_app.integrations.google_calendar.sync import local_datetime


@pytest.mark.parametrize(
    ("value", "default_zone", "same_instant"),
    [
        (
            {"dateTime": "2024-01-15T10:00:00"},
            "America/New_York",
            "2024-01-15T15:00:00+00:00",
        ),
        (
            {"dateTime": "2024-07-15T10:00:00"},
            "America/New_York",
            "2024-07-15T14:00:00+00:00",
        ),
        (
            {"dateTime": "2024-07-15T10:00:00", "timeZone": "America/Los_Angeles"},
            "America/New_York",
            "2024-07-15T17:00:00+00:00",
        ),
        (
            {
                "dateTime": "2024-07-15T10:00:00-04:00",
                "timeZone": "America/Los_Angeles",
            },
            "UTC",
            "2024-07-15T14:00:00+00:00",
        ),
    ],
)
def test_google_event_times_represent_the_correct_local_instant(
    value, default_zone, same_instant
):
    local = local_datetime(value, default_zone)
    assert local.tzinfo is None
    assert local == local_datetime({"dateTime": same_instant}, "UTC")
