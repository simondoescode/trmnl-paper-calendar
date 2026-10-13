"""Adapter from RFC 5545 to Terminus-shaped source arrays plus explicit metadata."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar
import recurring_ical_events

TZ = ZoneInfo("Europe/London")
MAX_EVENTS = 500


def local(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=TZ) if value.tzinfo is None else value.astimezone(TZ)
    return datetime.combine(value, time.min, TZ)


def clean(value, fallback=""):
    return " ".join(str(value or fallback).split())[:300]


def parse(body, name, selected):
    if len(body) > 2_000_000 or b"BEGIN:VCALENDAR" not in body:
        raise ValueError("Invalid ICS calendar")
    calendar = Calendar.from_ical(body)
    if calendar.name != "VCALENDAR" or any(c.errors for c in calendar.walk()):
        raise ValueError("Malformed ICS calendar")
    if len(calendar.walk("VEVENT")) > MAX_EVENTS:
        raise ValueError("Calendar contains too many event definitions")
    start = local(selected)
    end = local(selected + timedelta(days=7 - selected.weekday()))
    result = []
    # Query overlaps, including events which begin before the selected date.
    occurrences = recurring_ical_events.of(calendar).between(start, end)
    if len(occurrences) > MAX_EVENTS:
        raise ValueError("Calendar expansion exceeds 500 occurrences")
    for event in occurrences:
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        raw = event.decoded("DTSTART")
        all_day = not isinstance(raw, datetime)
        begins = local(raw)
        ends = local(event.decoded("DTEND", raw + (timedelta(days=1) if all_day else timedelta(0))))
        if ends.timestamp() < begins.timestamp():
            raise ValueError("Event ends before its start")
        last_day = (datetime.fromtimestamp(ends.timestamp() - 0.000001, TZ).date()
                    if ends.timestamp() > begins.timestamp() else begins.date())
        # Split into display-day segments; DTEND is exclusive, including dates.
        day = max(selected, begins.date())
        while day < end.date() and (local(day).timestamp() < ends.timestamp() or (ends.timestamp() == begins.timestamp() and day == begins.date())):
            segment = max(begins, local(day))
            result.append({"summary": clean(event.get("SUMMARY"), "Untitled"),
                           "location": clean(event.get("LOCATION")), "calendar_name": clean(name),
                           "start_at": segment.isoformat(), "end_at": ends.isoformat(),
                           "original_start_at": begins.isoformat(), "all_day": all_day,
                           "continuation": day > begins.date(), "uid": clean(event.get("UID"))})
            result[-1].update(multi_day=last_day > begins.date(), last_day=last_day.isoformat())
            if len(result) > MAX_EVENTS:
                raise ValueError("Calendar exceeds 500 display segments")
            day += timedelta(days=1)
    return result


def ordered(events):
    return sorted(events, key=lambda e: (datetime.fromisoformat(e["start_at"]).timestamp(), not e["all_day"], e["summary"], e["calendar_name"]))
