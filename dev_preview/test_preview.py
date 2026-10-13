import asyncio
from datetime import date, datetime
import json
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from fastapi.testclient import TestClient

import app
from calendar_data import parse, ordered
import network
import weather


class FetchTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler):
        client_class = httpx.AsyncClient
        with patch("network.destination", return_value=("calendar.example.org", "https://8.8.8.8/secret.ics")), patch("network.httpx.AsyncClient", side_effect=lambda **kw: client_class(transport=httpx.MockTransport(handler), **kw)):
            return await network.fetch("https://calendar.example.org/secret.ics")

    async def test_tls_sni_and_host_pinned(self):
        def handler(request):
            self.assertEqual(request.url.host, "8.8.8.8")
            self.assertEqual(request.headers["host"], "calendar.example.org")
            self.assertEqual(request.extensions["sni_hostname"], "calendar.example.org")
            return httpx.Response(200, content=b"calendar")
        self.assertEqual(await self.request(handler), b"calendar")

    async def test_redirect_not_followed(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={"location": "http://169.254.169.254/secret"})
        with self.assertRaises(ValueError):
            await self.request(handler)
        self.assertEqual(len(calls), 1)

    async def test_response_size_limit(self):
        with self.assertRaises(ValueError):
            await self.request(lambda request: httpx.Response(200, content=b"x" * (network.LIMIT + 1)))

    async def test_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("upstream private URL", request=request)
        with self.assertRaises(httpx.ReadTimeout):
            await self.request(handler)

FIXTURES = Path(__file__).parent / "fixtures"


class CalendarTests(unittest.TestCase):
    def events(self, fixture="family.ics", selected=date(2026, 10, 13)):
        return parse((FIXTURES / fixture).read_bytes(), "Test", selected)

    def test_recurrence_override_rdate_exdate(self):
        events = self.events()
        moved = [e for e in events if e["uid"] == "weekly@fixture.invalid"]
        self.assertEqual(len(moved), 2)
        self.assertTrue(any(e["start_at"].startswith("2026-10-13T18:30") for e in moved))
        self.assertTrue(any(e["start_at"].startswith("2026-10-15T18:00") for e in moved))
        self.assertFalse(any(e["uid"] == "weekly@fixture.invalid" for e in self.events(selected=date(2026, 10, 20))))

    def test_all_day_exclusive_end_and_continuation(self):
        events = self.events()
        trip = [e for e in events if e["uid"] == "trip@fixture.invalid"]
        self.assertEqual(len(trip), 3)
        self.assertTrue(all(e["all_day"] for e in trip))
        self.assertEqual([e["continuation"] for e in trip], [False, True, True])
        self.assertTrue(all(e["multi_day"] and e["last_day"] == "2026-10-16" for e in trip))
        self.assertFalse(any(e["start_at"].startswith("2026-10-17") for e in trip))
        ongoing = self.events(selected=date(2026, 10, 15))
        self.assertTrue(next(e for e in ongoing if e["uid"] == "trip@fixture.invalid")["continuation"])

    def test_cross_midnight(self):
        events = [e for e in self.events() if e["uid"] == "midnight@fixture.invalid"]
        self.assertEqual(len(events), 2)
        self.assertTrue(events[1]["continuation"])
        self.assertEqual(events[1]["last_day"], "2026-10-16")
        self.assertTrue(events[1]["start_at"].startswith("2026-10-16T00:00"))

    def test_spring_dst(self):
        event = self.events("dst.ics", date(2026, 3, 29))[0]
        self.assertEqual(event["start_at"], "2026-03-29T00:30:00+00:00")
        self.assertEqual(event["end_at"], "2026-03-29T03:30:00+01:00")

    def test_autumn_dst_repeated_hour_and_weekly_time(self):
        events = ordered(self.events("dst.ics", date(2026, 10, 25)))
        self.assertEqual(events[0]["start_at"], "2026-10-25T01:30:00+01:00")
        self.assertEqual(events[1]["start_at"], "2026-10-25T01:30:00+00:00")
        self.assertTrue(events[2]["start_at"].startswith("2026-10-25T09:00:00+00:00"))

    def test_multiple_calendar_sort_and_timezone(self):
        events = ordered(self.events() + self.events("work.ics"))
        work = next(e for e in events if e["uid"] == "overlap@fixture.invalid")
        self.assertTrue(work["start_at"].endswith("10:00:00+01:00"))
        stamps = [datetime.fromisoformat(e["start_at"]).timestamp() for e in events]
        self.assertEqual(stamps, sorted(stamps))

    def test_empty_and_malformed(self):
        self.assertEqual(self.events("empty.ics"), [])
        for body in (b"garbage", b"BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:bad\nEND:VEVENT\nEND:VCALENDAR"):
            with self.assertRaises(Exception):
                parse(body, "Test", date(2026, 10, 13))


class WeatherTests(unittest.TestCase):
    def test_wmo_groups(self):
        for code, icon in [(0, "sun"), (2, "sun-cloud"), (3, "cloud"), (45, "fog"), (55, "rain"),
                           (67, "rain"), (85, "snow"), (99, "storm"), (123, "cloud")]:
            self.assertEqual(weather.condition(code)[1], icon)
        self.assertEqual(weather.condition(0, False), ("Clear night", "moon"))

    def test_contract(self):
        result = weather.normalize(json.loads((FIXTURES / "weather.json").read_text()), "fixture")
        self.assertEqual(len(result["forecast"]), 3)
        self.assertEqual(result["current"]["precipitation_probability"], 20)
        self.assertEqual(result["last_successful_update"], "fixture")


class NetworkTests(unittest.TestCase):
    @patch("network.socket.getaddrinfo")
    def test_dns_pinned(self, lookup):
        lookup.return_value = [(None, None, None, None, ("8.8.8.8", 443))]
        host, pinned = network.destination("https://calendar.example.org/private-token.ics")
        self.assertEqual(host, "calendar.example.org")
        self.assertEqual(pinned, "https://8.8.8.8/private-token.ics")

    @patch("network.socket.getaddrinfo")
    def test_all_private_addresses_rejected(self, lookup):
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "192.168.1.2", "224.0.0.1"):
            lookup.return_value = [(None, None, None, None, (address, 443))]
            with self.assertRaises(ValueError):
                network.destination("https://example.org/feed")

    def test_bad_schemes_credentials_and_ports(self):
        for url in ("http://example.org/feed", "https://user:secret@example.org/feed", "https://example.org:123/feed", "https://example.org/feed#token"):
            with self.assertRaises(ValueError):
                network.destination(url)


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_offline_contract(self):
        with patch("network.socket.getaddrinfo", side_effect=AssertionError("network used")), patch("httpx.AsyncClient", side_effect=AssertionError("network used")):
            result, status = await app.build(app.Controls())
        self.assertGreater(status["event_count"], 0)
        self.assertEqual(result["preview_now"], "2026-10-13T00:00:00+01:00")
        self.assertEqual(result["preview_week_end"], "2026-10-19T00:00:00+01:00")
        self.assertEqual(len(result["source_1"]), 1)
        self.assertTrue(result["source_1"][0]["events"][0]["all_day"])
        self.assertEqual(len(result["weather"]["forecast"]), 3)

    async def test_weather_failure_retains_last_good(self):
        app.weather_cache = None
        good = {"current": {"temperature": 16}, "forecast": [], "last_successful_update": "prior"}
        controls = app.Controls(weather_mode="live", scenario="empty")
        with patch("weather.live", AsyncMock(return_value=good)):
            result, _ = await app.build(controls)
        with patch("weather.live", AsyncMock(side_effect=ValueError("private failure"))):
            result, status = await app.build(controls)
        self.assertEqual(result["weather"], good)
        self.assertIn("last successful", status["weather"])
        self.assertNotIn("private failure", json.dumps(status))

    async def test_missing_configuration_and_disabled_weather(self):
        with patch.dict(os.environ, {"PREVIEW_CALENDARS_FILE": "/does-not-exist"}):
            result, status = await app.build(app.Controls(calendar_mode="live", weather_mode="disabled"))
        self.assertIsNone(result["weather"])
        self.assertEqual(status["event_count"], 0)
        self.assertIsNone(status["last_successful_refresh"])

    async def test_private_url_redaction(self):
        secret = "https://example.org/private-credential.ics"
        config = {"calendars": [{"name": "Family", "url_env": "FAMILY_CALENDAR_URL"}]}
        with patch("pathlib.Path.read_text", return_value=json.dumps(config)), patch.dict(os.environ, {"FAMILY_CALENDAR_URL": secret}), patch("app.fetch", AsyncMock(side_effect=ValueError(secret))):
            result, status = await app.build(app.Controls(calendar_mode="live", weather_mode="disabled"))
        self.assertNotIn(secret, json.dumps(result) + json.dumps(status))
        self.assertNotIn("private-credential", json.dumps(status))

    async def test_weather_missing_coordinates(self):
        app.weather_cache = None
        with patch.dict(os.environ, {}, clear=True):
            result, status = await app.build(app.Controls(weather_mode="live", scenario="empty"))
        self.assertIsNone(result["weather"])
        self.assertIn("check coordinates", status["weather"])

    async def test_recurrence_resource_limit(self):
        body = b"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:large\nDTSTART:20261013T000000Z\nDTEND:20261013T000001Z\nRRULE:FREQ=SECONDLY\nEND:VEVENT\nEND:VCALENDAR"
        with self.assertRaises(ValueError):
            await app.bounded_parse(body, "Large", date(2026, 10, 13))


class HttpTests(unittest.TestCase):
    def test_control_validation_and_cross_origin(self):
        with TestClient(app.app) as client:
            self.assertEqual(client.post("/api/refresh", json={"calendar_mode": "bogus"}).status_code, 422)
            self.assertEqual(client.post("/api/refresh", json={}, headers={"origin": "https://evil.invalid"}).status_code, 403)
            self.assertEqual(client.get("/", headers={"host": "evil.invalid"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
