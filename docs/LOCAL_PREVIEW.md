# Local preview audit and data contract

The original Compose service ran `trmnlp serve` with static Liquid settings and no data. The Dev Container started a second serve process. The separate optional `calendar_service` handled authenticated ICS setup but did not connect to the preview. It remains separate and unchanged; its fetcher is not used by the new preview.

Repository documentation and the ICS spike establish Terminus's `source_n: [{events: [...]}]` shape. The Liquid loops consume `summary`, `start_at`, `location` and optional `all_day`. Raw Terminus exchanges have not been integration-tested here. Existing documentation records loss of reliable all-day classification and lack of expanded recurrence. Local normalization is not verified production support.

The [original renderer](https://github.com/simondoescode/paper-calendar/blob/main/src/calendar/calendar_renderer.cpp) was reviewed: it draws a 112 px black header, 72 px timed and 48 px all-day cards, three forecasts, 52 px upcoming cards and a 32 px status footer. Weather reads current temperature/condition/day state and forecast highs/lows/rain probability. The adapter supplies equivalent display fields to the existing Liquid design and retains its SVG weather icons.

The installed [trmnlp Context](https://github.com/usetrmnl/trmnlp/blob/main/lib/trmnlp/context.rb) accepts `source_data:` and its [renderer](https://github.com/usetrmnl/trmnlp/blob/main/lib/trmnlp/renderer.rb) exposes `render_full_page`. Direct injection bypasses static-data/polling without changing exported settings or writing private data to disk. A small Ruby HTTP adapter reuses the native engine, filters and configuration. The image is pinned by digest because this API is an implementation dependency. Review it and run browser tests when upgrading.

## Context contract

`source_1` contains one merged calendar with `name`, `ordered: true` and `events`. Each event has `summary`, `location`, `calendar_name`, `start_at`, `end_at`, `original_start_at`, `all_day`, `continuation` and `uid`. Dates are ISO 8601 London timestamps with offsets. The ordered flag preserves sorting by actual instant across repeated DST hours. Production sources without the flag retain existing per-calendar Liquid sorting.

`preview_now`, `preview_week_end` and `preview_updated` are optional ISO timestamps. Without them, the template uses its existing render clock. The local calendar range ends at next Monday midnight, exclusively, using civil London dates. All-day DTEND is exclusive. Events crossing midnight create continuation segments at local midnight, retaining original start/end. Floating ICS times use Europe/London. Cancelled occurrences are excluded. Titles and locations have whitespace collapsed and are bounded to 300 characters; Liquid escapes them.

`weather.current` has `temperature`, `description`, `icon`, `high`, `low`, `precipitation_probability` and `range`. Each of three `weather.forecast` entries has `date`, `day`, `high`, `low`, `precipitation_probability`, `description` and `symbol`. Icons use sun, sun-cloud, cloud, rain, storm, snow, fog or moon. `weather.last_successful_update` is an ISO timestamp. Disabled/unavailable weather is null.

The dashboard maintains one shared in-memory context; tabs share the last refreshed controls. Restarting clears context/cache. No scheduling or background polling runs. Live calendar failures omit that source with diagnostics; only weather retains last-good data. Event counts are display segments, not unique VEVENT counts. Mock weather and footer timestamps are fixed for deterministic screenshots; diagnostics show real refresh times. Live forecasts use actual API dates rather than the simulated calendar date.

## Verification and limits

- Docker build/start, offline unit tests and native TRMNL lint run locally.
- Native Firefox checks canvas, card styling, forecasts, date/DST/continuation/empty states, dashboard iframe and permanent four-shade simulation.
- Mock renders are compared byte-for-byte with the committed `docs/mock-preview.png` baseline and a repeated capture; CI uploads screenshots. Review artifacts before updating the baseline. Browser/framework upgrades can legitimately change the image.
- Unit tests block network in mock data mode and check public DNS pinning, private destination rejection, TLS hostname preservation, redirect rejection, response bounds and timeouts.
- Browser assets are local. Initial builds still download images, packages and official framework assets.
- A real public HTTPS ICS fixture was fetched and parsed. Private subscriptions were not tested without user credentials. Live Open-Meteo verification in this environment encountered an untrusted `Zen Personal CA` certificate; verification remains enabled and mocked weather transports/failure tests pass. Production Terminus parity and physical e-ink fidelity are not claimed.
- Production limitations remain documented in the README and Terminus setup notes. This is a local development environment, not a hosted calendar service.
