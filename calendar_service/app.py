"""Private multi-ICS calendar setup service. Bind to localhost or protect behind HTTPS."""
import base64
from datetime import datetime, timedelta, timezone
from html import escape
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from icalendar import Calendar
import recurring_ical_events
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

DB_PATH = Path(os.getenv("CALENDAR_DB_PATH", "/data/calendars.sqlite"))
PASSWORD = os.getenv("CALENDAR_ADMIN_PASSWORD", "")
LOCAL_TZ = ZoneInfo("Europe/London")
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def require_auth(request: Request):
    if not PASSWORD:
        raise HTTPException(503, "Set CALENDAR_ADMIN_PASSWORD before starting")
    header = request.headers.get("authorization", "")
    if not header.startswith("Basic "):
        raise HTTPException(401, headers={"WWW-Authenticate": 'Basic realm="Paper Calendar"'})
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode()
        username, supplied = decoded.split(":", 1)
    except (ValueError, UnicodeError):
        raise HTTPException(401, headers={"WWW-Authenticate": 'Basic realm="Paper Calendar"'})
    if not (secrets.compare_digest(username, "admin") and secrets.compare_digest(supplied, PASSWORD)):
        raise HTTPException(401, headers={"WWW-Authenticate": 'Basic realm="Paper Calendar"'})


def csrf_guard(request: Request):
    # Same-origin POST requests only. No CORS middleware is installed.
    origin = request.headers.get("origin")
    if origin:
        origin_url = urlsplit(origin)
        if origin_url.scheme not in ("http", "https") or origin_url.netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin request blocked")
    elif request.headers.get("sec-fetch-site") not in (None, "same-origin", "none"):
        raise HTTPException(403, "Cross-origin request blocked")


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS calendars (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
    )""")
    return conn


def validate_url(raw: str) -> str:
    raw = raw.strip()
    if len(raw) > 2048:
        raise ValueError("Calendar URL is too long")
    parsed = urlsplit(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Use an HTTPS calendar URL without credentials or fragments")
    if parsed.port not in (None, 443):
        raise ValueError("Only HTTPS port 443 is allowed")
    host = parsed.hostname
    if host == "localhost" or host.endswith(".localhost") or "." not in host:
        raise ValueError("A public hostname is required")
    try:
        resolved = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved") from exc
    if not resolved:
        raise ValueError("Hostname could not be resolved")
    for entry in resolved:
        addr = ipaddress.ip_address(entry[4][0])
        if not addr.is_global:
            raise ValueError("Private or reserved network destinations are blocked")
    return raw


async def fetch_calendar(url: str):
    validate_url(url)
    # No redirects; proxy environment disabled. A pinned DNS resolver should be
    # added before exposing this service beyond a trusted local deployment.
    async with httpx.AsyncClient(follow_redirects=False, trust_env=False, timeout=12.0) as client:
        async with client.stream("GET", url, headers={"Accept": "text/calendar"}) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Calendar source returned an unexpected status")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError("Calendar feed exceeds the 2 MB limit")
    calendar = Calendar.from_ical(bytes(body))
    if calendar.name != "VCALENDAR":
        raise ValueError("Response is not a calendar")
    return calendar


class CalendarInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=8, max_length=2048)


def public_row(row):
    return {"id": row["id"], "name": row["name"], "enabled": bool(row["enabled"])}
    

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    require_auth(request)
    return Path(__file__).with_name("index.html").read_text()


@app.get("/api/calendars")
def list_calendars(request: Request):
    require_auth(request)
    with db() as con:
        return [public_row(r) for r in con.execute("SELECT * FROM calendars ORDER BY created_at, name")]


@app.post("/api/calendars", status_code=201)
async def add_calendar(item: CalendarInput, request: Request):
    require_auth(request)
    csrf_guard(request)
    name = item.name.strip()
    if not name:
        raise HTTPException(422, "A calendar name is required")
    try:
        url = validate_url(item.url)
        await fetch_calendar(url)
    except (ValueError, httpx.HTTPError, socket.error) as exc:
        raise HTTPException(422, "Unable to connect to this ICS calendar. Check its URL and accessibility.") from exc
    identifier = str(uuid4())
    with db() as con:
        con.execute("INSERT INTO calendars VALUES (?,?,?,?,?)", (identifier, name, url, 1, datetime.now(timezone.utc).isoformat()))
    return {"id": identifier, "name": name, "enabled": True}


@app.post("/api/calendars/test")
async def test_calendar(item: CalendarInput, request: Request):
    require_auth(request)
    csrf_guard(request)
    try:
        calendar = await fetch_calendar(item.url)
        count = sum(1 for x in calendar.walk() if x.name == "VEVENT")
        return {"ok": True, "event_count": count}
    except (ValueError, httpx.HTTPError, socket.error):
        raise HTTPException(422, "Could not read an ICS calendar from that URL")


@app.delete("/api/calendars/{calendar_id}")
def delete_calendar(calendar_id: str, request: Request):
    require_auth(request)
    csrf_guard(request)
    with db() as con:
        found = con.execute("DELETE FROM calendars WHERE id=?", (calendar_id,))
        if found.rowcount == 0:
            raise HTTPException(404, "Calendar not found")
    return {"ok": True}


@app.post("/api/calendars/{calendar_id}/toggle")
def toggle_calendar(calendar_id: str, request: Request):
    require_auth(request)
    csrf_guard(request)
    with db() as con:
        row = con.execute("SELECT enabled FROM calendars WHERE id=?", (calendar_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Calendar not found")
        enabled = int(not row["enabled"])
        con.execute("UPDATE calendars SET enabled=? WHERE id=?", (enabled, calendar_id))
    return {"ok": True, "enabled": bool(enabled)}


@app.get("/api/events")
async def events(request: Request, days: int = 7):
    require_auth(request)
    if not 1 <= days <= 31:
        raise HTTPException(422, "days must be between 1 and 31")
    start = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)
    with db() as con:
        rows = con.execute("SELECT * FROM calendars WHERE enabled=1").fetchall()
    result = []
    for row in rows:
        try:
            calendar = await fetch_calendar(row["url"])
            for event in recurring_ical_events.of(calendar).between(start, end):
                dtstart = event.decoded("DTSTART")
                dtend = event.decoded("DTEND", None)
                all_day = not isinstance(dtstart, datetime)
                if all_day:
                    begins = datetime.combine(dtstart, datetime.min.time(), LOCAL_TZ)
                else:
                    begins = dtstart if dtstart.tzinfo else dtstart.replace(tzinfo=LOCAL_TZ)
                result.append({
                    "calendar_id": row["id"], "calendar": row["name"],
                    "title": str(event.get("SUMMARY", "Untitled")),
                    "start": begins.astimezone(LOCAL_TZ).isoformat(),
                    "end": dtend.isoformat() if dtend else None,
                    "all_day": all_day
                })
        except (ValueError, httpx.HTTPError, socket.error, KeyError):
            continue  # An inaccessible feed must not block the other feeds.
    result.sort(key=lambda item: (item["start"], not item["all_day"], item["title"]))
    return {"timezone": "Europe/London", "events": result}
