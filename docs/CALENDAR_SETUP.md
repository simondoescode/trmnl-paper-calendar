# Self-hosted calendar setup (initial implementation)

Start the companion calendar service with:

```bash
cp .env.example .env
# Edit .env and replace the example username and password.
docker compose -f compose.calendar.yaml up --build -d
```

Visit **http://localhost:8000**; sign in with the username and password configured in `.env`. The web UI supports multiple HTTPS ICS URLs, connection tests, enabling/disabling, and removal. Secret URLs are only stored in the Docker volume `calendar_data`, not committed to Git and not returned by GET endpoints.

Get merged events from `http://localhost:8000/api/events?days=7` using HTTP Basic auth. All-day events and recurring occurrences are expanded. Timezone is Europe/London. Google Calendar's *Secret address in iCal format* is one example of a compatible feed.

**Security and deployment limitations:** This is a local-only first iteration, bound to `127.0.0.1` by Compose, so other devices on the LAN cannot connect directly. Both username and password are configured via `.env` (do not commit this file). Changing the credentials requires restarting the container. HTTP Basic authentication sends reusable credentials on every request. Only use the service on the same trusted machine at localhost; for access from other devices, deploy behind HTTPS and authentication: never expose port 8000 publicly. If deploying for external access, add HTTPS, proper session/CSRF protection, rate limiting, per-user accounts where applicable, network egress controls, and DNS pinning to prevent DNS-rebinding SSRF. Secret ICS URLs are stored unencrypted in a Docker-managed local volume: restrict host access and backups. Never print or commit them. ICS subscriptions are generally read-only; they do not synchronise changes made elsewhere instantly.

This service deliberately **does not** yet implement the TRMNL image renderer or integrate with Terminus. It supplies the feed and setup UI; `src/full.liquid` is the independent Hello World plugin.

Tests: `docker compose -f compose.calendar.yaml run --rm --entrypoint python calendar -m unittest -v test_app`
