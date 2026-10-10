# Terminus native ICS proof of concept

## Unexpected finding from Terminus source inspection

Terminus **already parses ICS**. There is no need to add a new parser, JavaScript
runtime, or dependency just to decode `text/calendar`:

- `Gemfile` already includes `icalendar ~> 2.12`.
- `app/aspects/extensions/fetcher/client.rb` recognizes `text/calendar`
  and dispatches to `Source.from_calendar`.
- `app/aspects/extensions/source.rb` parses ICS using `Icalendar::Parser`.
- `lib/terminus/refines/icalendar/calendar.rb` serializes calendars and events
  into hashes (including `events`, `start_at`, `end_at`, and `recurrence_rule`).
- Importing a `transform.js` is explicitly rejected by the remote importer.

See upstream code:
- https://github.com/usetrmnl/terminus/blob/main/app/aspects/extensions/fetcher/client.rb
- https://github.com/usetrmnl/terminus/blob/main/app/aspects/extensions/source.rb
- https://github.com/usetrmnl/terminus/blob/main/lib/terminus/refines/icalendar/event.rb
- https://github.com/usetrmnl/terminus/blob/main/app/aspects/extensions/importers/remote/transformer.rb

## Proof of concept

`normalizer.rb` is dependency-free Ruby taking **parsed** Terminus calendar hashes and producing
`{today:, week:, warnings:}` for the existing Paper Calendar Liquid template.
It demonstrates normalization, UK-facing time formatting, all-day-first ordering,
date filtering, and handling of malformed events.

Run:

```bash
ruby poc/terminus_native_ics/test_normalizer.rb
```

This is intentionally **not** an importable Terminus patch: it is an isolated
prototype we can iterate on safely before submitting changes upstream.

## Important limitations

- Recurring events are **explicitly skipped** and counted in warnings; we must
  expand RRULE, RDATE, EXDATE, and RECURRENCE-ID (including modified instances)
  before this can be used as a real family calendar.
- Fixed UTC offset is used only by the minimal prototype. Production must use
  Europe/London timezone rules across DST transitions (not hard-coded +01:00).
- No remote feed acquisition, settings UI, secret encryption, SSRF controls, or
  support for multiple configured subscriptions is implemented here.
- Import tests, runtime preview, and native Terminus integration remain outstanding.

## Proposed upstream change, now much smaller

1. Reuse the existing Terminus `text/calendar` polling/parse path.
2. Add an **opt-in calendar agenda projection** for the parsed exchange data;
   retain existing generic calendar hashes unchanged for current consumers.
3. Implement RFC 5545 recurrence expansion bounded to a configured range and
   protect against pathological feeds, missing TZIDs, and runaway recurrences.
4. Add native private calendar subscription fields, secure URL storage and
   outbound fetch protections; support multiple feeds without embedding secrets
   in exported templates or plugin ZIPs.
5. Normalize by Europe/London local dates, combine feeds, then expose today's
   and this week's sorted events for Liquid.
6. Cover DST changeover, all-day/multi-day boundaries, overridden occurrences,
   cancellations, invalid ICS and private-network URLs with fixture tests.
7. Add Terminus importer/UI integration tests and user docs, then propose a
   Terminus upstream PR through a fork with maintainer feedback.

### GitHub workflow

Our account currently has read-only permissions on `usetrmnl/terminus`, so this
prototype lives in `simondoescode/trmnl-paper-calendar`. An upstream PR needs a
fork and changes that match the upstream extension architecture; do not treat
this as merged native functionality.
