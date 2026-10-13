"""Local-only preview orchestration; no private URLs or event data written to disk."""
import asyncio
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from calendar_data import TZ, ordered
from network import fetch
import weather

ROOT = Path(__file__).parent
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "preview", "testserver"])
lock = asyncio.Lock()
weather_cache = None
context = None
diagnostics = {}


class Controls(BaseModel):
    calendar_mode: Literal["mock", "live"] = "mock"
    weather_mode: Literal["mock", "live", "disabled"] = "mock"
    selected_date: date = date(2026, 10, 13)
    scenario: Literal["family", "empty", "spring-dst", "autumn-dst"] = "family"


async def bounded_parse(body, name, selected):
    # A pathological RRULE must not hang the web server or exhaust its memory.
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(ROOT / "parse_worker.py"), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(proc.communicate(json.dumps(
            {"ics": body.decode("utf-8-sig"), "name": name, "date": selected.isoformat()}).encode()), 5)
        if proc.returncode:
            raise ValueError("Calendar parsing failed or exceeded limits")
        return json.loads(output)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise


async def build(controls):
    global weather_cache
    events, sources = [], []
    selected = controls.selected_date
    if controls.calendar_mode == "mock":
        filenames = ["empty.ics"] if controls.scenario == "empty" else ["family.ics", "work.ics"]
        if controls.scenario in ("spring-dst", "autumn-dst"):
            filenames = ["dst.ics"]
        for filename in filenames:
            body = (ROOT / "fixtures" / filename).read_bytes()
            parsed = await bounded_parse(body, filename.removesuffix(".ics").title(), selected)
            events.extend(parsed)
            sources.append({"name": filename.removesuffix(".ics").title(), "status": "ok", "events": len(parsed)})
    else:
        try:
            config_path = Path(os.getenv("PREVIEW_CALENDARS_FILE", "/config/calendars.local.json"))
            calendars = json.loads(config_path.read_text())["calendars"]
            if not isinstance(calendars, list) or len(calendars) > 10:
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            calendars = []
            sources.append({"name": "Configuration", "status": "No valid local calendar configuration"})
        for index, item in enumerate(calendars):
            # Diagnostics identify sources by ordinal, never configuration text.
            label = f"Calendar {index + 1}"
            if not isinstance(item, dict) or not item.get("enabled", True):
                continue
            try:
                env_name = item["url_env"]
                if not isinstance(env_name, str) or not env_name.endswith("_CALENDAR_URL"):
                    raise ValueError()
                body = await fetch(os.environ[env_name])
                parsed = await bounded_parse(body, item.get("name", label), selected)
                events.extend(parsed)
                sources.append({"name": label, "status": "ok", "events": len(parsed)})
            except Exception:
                sources.append({"name": label, "status": "Source unavailable, missing configuration or invalid ICS"})
    timestamp = datetime.now(TZ).isoformat()
    weather_status = controls.weather_mode
    weather_data = None
    if controls.weather_mode == "mock":
        mock = json.loads((ROOT / "fixtures" / "weather.json").read_text())
        mock["daily"]["time"] = [(selected + timedelta(days=i)).isoformat() for i in range(3)]
        weather_data = weather.normalize(mock, local_timestamp(selected))
    elif controls.weather_mode == "live":
        try:
            weather_cache = await weather.live()
            weather_status = "live: ok (forecast dates are actual, not simulated)"
        except Exception:
            weather_status = "live: unavailable; using last successful response" if weather_cache else "live: unavailable; check coordinates"
        weather_data = weather_cache
    # One merged calendar gives native nested loops global chronological order.
    result = {"source_1": [{"name": "Merged calendars", "events": ordered(events), "ordered": True}],
              "preview_now": local_timestamp(selected),
              "preview_updated": local_timestamp(selected) if controls.calendar_mode == "mock" and controls.weather_mode != "live" else timestamp,
              "preview_week_end": local_timestamp(selected + timedelta(days=7 - selected.weekday())),
              "weather": weather_data, "connection_label": "Local preview"}
    if len(json.dumps(result).encode()) > 95_000:
        raise HTTPException(422, "Preview exceeds the native renderer data limit; choose a smaller feed")
    statuses_ok = all(s["status"] == "ok" for s in sources) and not weather_status.startswith("live: unavailable")
    return result, {"event_count": len(events), "calendars": sources, "weather": weather_status,
                    "last_successful_refresh": timestamp if statuses_ok else diagnostics.get("last_successful_refresh"),
                    "weather_updated": weather_data.get("last_successful_update") if weather_data else None,
                    "warnings": ["Live forecasts use actual API dates."] if controls.weather_mode == "live" else []}


def local_timestamp(selected):
    return datetime.combine(selected, datetime.min.time(), TZ).isoformat()


@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (ROOT / "dashboard.html").read_text(encoding="utf-8")


@app.post("/api/refresh")
async def refresh(controls: Controls, request: Request):
    origin = request.headers.get("origin")
    if (origin and origin not in (f"http://{request.headers.get('host')}", f"https://{request.headers.get('host')}")) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-origin refresh blocked")
    global context, diagnostics
    async with lock:
        result, status = await build(controls)
        context, diagnostics = result, status
    return status


@app.get("/api/context")
async def data():
    global context, diagnostics
    async with lock:
        if context is None:
            context, diagnostics = await build(Controls())
        return context


@app.get("/api/diagnostics")
async def status():
    await data()
    return diagnostics


@app.get("/preview", response_class=HTMLResponse)
async def preview():
    payload = await data()
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post("http://renderer:4567/render", json=payload)
            response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        raise HTTPException(503, "Native renderer unavailable; check docker compose logs renderer")


@app.get("/assets/{filename}")
async def asset(filename: str):
    from fastapi.responses import Response
    if not filename.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(404)
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.get(f"http://renderer:4567/assets/{filename}")
    return Response(response.content, status_code=response.status_code,
                    media_type=response.headers.get("content-type", "application/octet-stream"))
