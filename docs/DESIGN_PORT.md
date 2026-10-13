# Design port: paper-calendar → trmnl-paper-calendar

Reference implementation: [original ESP32 renderer](https://github.com/simondoescode/paper-calendar/blob/main/src/calendar/calendar_renderer.cpp).

## What was ported

- Exact canvas size: 800 × 480; top header: 112 px; footer: 32 px.
- Approximate original column break at x=487 / 313 px.
- Black left header, large weekday, date, top-right weather slot.
- White Today cards: 72 px timed, 48 px light-grey all-day, split time/title fields, rounded outline.
- Full-height light-grey right sidebar with **Later this week** heading, three forecast slots, and narrow day-labelled upcoming cards.
- Footer with today count, last-rendered time, connection label and optional battery reading.
- Manrope typography using an embedded Latin variable WOFF2 subset (weights 400–800), with local/system fallbacks for unsupported glyphs. The font and its full SIL Open Font License are included in the Liquid template; see [font details](../assets/fonts/README.md).

The Liquid palette uses exactly four shades: black (`#000`), dark grey (`#555`) for Today card outlines, light grey (`#aaa`) for all-day cards and the sidebar, and white (`#fff`) for timed cards and the main panel. These shades survive the local preview's four-level quantization; the previous `#dedede` backgrounds mapped to white.

Readability refinements retain the canvas and card heights: narrower centred time columns leave more room for titles, secondary text shows location or calendar name, upcoming cards support two title lines and shaded weekday labels, and forecasts include optional daily highs/lows with a separator above the agenda.

## What is not identical yet

The C++ firmware has true native all-day flags, weather data and battery/Wi-Fi hardware state. Terminus's **native ICS parser does not expose a reliable normalized all-day flag** in its current event hashes; default ICS entries therefore render as timed entries, including midnight all-day dates. The all-day styling activates only if a future normalizer provides `all_day: true`.

Weather is only shown when a structured `weather` object is supplied to the Liquid context. A blank forecast placeholder is shown otherwise. Similarly, Wi-Fi and battery information are optional server context; the default footer says Terminus and Battery —.

The template reads at most three native ICS exchanges (`source_1`, `source_2`, `source_3`). Raw native exchanges do not expand recurring appointments and sort events within each calendar rather than globally. Date filters run in the server's Liquid timezone; confirm Europe/London for UK clock times, especially around DST transitions. The independent [local preview adapter](LOCAL_PREVIEW.md) supplies expanded, globally ordered day segments, explicit all-day flags and weather for development. These enhancements do not demonstrate native Terminus feature parity.

## Testing in Terminus

1. Create a Poll extension, target TRMNL OG (800 × 480).
2. Add a GET exchange with `{"Accept":"text/calendar"}` as Headers and an ICS HTTPS URL as Template.
3. Paste the entire `src/full.liquid` into the extension Template editor.
4. Save and preview; the `screen screen--og` / `view view--full` wrappers are required for correct positioning.
5. To see real cards, use a calendar with events on the current day and later in the current week. The sample test fixture from PR #4 may no longer be in the displayed date window.

This is a design port, not a complete release-ready ICS agenda solution. In particular, add recurrence expansion, normalized all-day detection, multi-feed event sorting, UK timezone tests, and weather exchange wiring before promoting it as feature parity with the original firmware.
