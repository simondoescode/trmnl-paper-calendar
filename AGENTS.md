# Repository guidance

- This is a TRMNL Liquid plugin, not ESP32 firmware.
- Prefer official TRMNL Framework components/utilities for device screens.
- The target display is 800 × 480 and supports four greys.
- Use UK locale and Europe/London timezone for calendar features.
- Do not commit Google Calendar private ICS URLs, API keys, or user data.
- Keep local development working with Docker Compose and VS Code Dev Containers.
- Run `docker compose run --rm trmnlp lint` before proposing changes.
- Keep the local plugin preview independent of the full Terminus server.
