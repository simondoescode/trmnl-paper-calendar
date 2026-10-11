# Today / This Week — Terminus setup

This screen uses the **working 800 × 480 `screen screen--og` / `view view--full` wrappers** confirmed in a local Terminus preview. It is a two-column four-shade presentation of Terminus's already parsed ICS data.

## Configure the native Poll extension

1. In Terminus, create or edit a **Poll** extension, targeting **TRMNL OG (2-bit)**.
2. In Exchanges, add a GET request. Set Headers to `{"Accept":"text/calendar"}` and Template to your ICS subscription URL. Leave Body blank.
3. Add more exchanges for additional ICS calendars (the template supports `source_1`, `source_2`, and `source_3`).
4. In the extension Template editor, paste **the entire contents of `src/full.liquid`**, including the outer `screen` and `view` elements.
5. Save, refresh Exchanges, then open Preview for the 800 × 480 model.
6. Inspect Exchange Data and Errors if no events appear.

For a non-secret test URL, use:

```text
https://raw.githubusercontent.com/simondoescode/trmnl-paper-calendar/main/spikes/terminus-ics-poll/sample.ics
```

**Do not commit private ICS subscription URLs to the repository or export them in plugin packages.** Treat them as credentials.

## Current template behavior

- Left: Today (up to five timed event cards).
- Right: upcoming events in the next seven days (up to six), excluding today.
- Light-grey sidebar, white main panel, four greyscale-safe shades, black text and a last-updated footer.
- Escapes event titles to prevent HTML injection.
- Processes the first three Terminus Exchange sources without an additional application service.

## Known limitations — not a complete calendar implementation

1. Terminus's native ICS parser returns RRULE metadata but **does not expand occurrences**. This template only displays the original VEVENT and cannot show repeated future instances.
2. Dates are derived from Liquid's server timezone; set Terminus to **Europe/London** for correct local dates. DST boundaries must be verified.
3. Per-source events are sorted by start date, but **multiple feeds are not globally sorted**. Liquid alone is inadequate for correct multi-source ordering.
4. The ICS-to-hash representation loses an explicit all-day indicator in some cases. Accordingly the template does **not** claim to classify all-day events; midnight events may appear as `00:00`.
5. The right-hand panel uses a rolling seven-day range rather than a strict Monday–Sunday calendar week.
6. Footer time reflects render time, not actual source refresh time.
7. This is a paste-into-Terminus template until native export/import packaging has been validated. The separate static `trmnlp` settings file does not configure the Terminus Exchanges.

For a production-ready public release, normalize event feeds on the Terminus side: RFC 5545 recurrence expansion, all-day preservation, Europe/London conversion, cross-feed sorting and filtering. Add integration tests before release.
