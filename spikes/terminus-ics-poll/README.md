# Native Terminus ICS polling spike

## Goal

Test that Terminus can fetch an ICS URL using an imported Core-compatible extension and make parsed event hashes available to Liquid. Terminus source already routes the `text/calendar` response type through `Source.from_calendar`.

## Important: configure a reachable ICS URL first

The included `sample.ics` is a fixture. The `settings.yml` polling URL points to the fixture on the **main branch**, which becomes available **only after this PR is merged**. Before merging, change the URL to a public HTTPS ICS URL you control, or one you can access. Never commit a private calendar subscription URL.

The server must return `Content-Type: text/calendar`, or supply the `Accept: text/calendar` request header. Verify the server actually responds with ICS. Terminus's fetch client selects MIME types using the request's Accept header when provided.

## Package and import

From the repository root:

```bash
python3 scripts/package_ics_spike.py
```

Import `dist/terminus-ics-poll-spike.zip` via the Terminus extension import UI. Set up a screen, trigger a refresh, and inspect exchange data and screenshot preview.

## Success criteria

- HTTP request succeeds and source_1 contains parsed calendar objects.
- Template prints calendar name, event summary and start_at.
- Single and recurring VEVENT entries are both present in parsed output.
- RRULE is retained as metadata; recurrence occurrence expansion is **not** expected.
- No calendar secrets appear in exported ZIPs.

## Troubleshooting

If blank, inspect Terminus exchange errors and payloads. The exact variable name (`source_1`) and Core ZIP import behavior should be confirmed against the running Terminus version. `text/calendar; charset=utf-8` could require additional MIME handling depending on source headers.

This spike has not been executed against a running Terminus instance. It is deliberately isolated from the production Paper Calendar plugin and is not a working calendar integration.
