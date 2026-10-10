# Terminus extension: import and calendar integration

## What this PR delivers

An importable TRMNL Core-style private plugin ZIP, a two-column full-screen e-ink design, demo content, release packaging and documentation. Terminus documents both Core-format import and its own native extension import/export.

**Important:** This is a **display-only preview**, not a working ICS integration. The ZIP starts in static/demo mode. Installing it does **not** connect to a calendar, and the Screen Title / Week Start fields are *display preferences*, not a calendar setup wizard.

## Import on Terminus

1. In this repo, package the flat TRMNL archive using `python3 scripts/package_plugin.py` (output: `dist/paper-calendar.zip`).
2. In Terminus go to Extensions and use the import facility for a TRMNL Core plugin ZIP.
3. Select the **TRMNL OG (2-bit)** build model, preview the design, and place the generated screen into a device playlist.
4. The example events are fake. Do **not** enter personal ICS URLs in the template or static_data.

This imports a Core-format plugin, not a Terminus-native extension export. Terminus's import UI and supported field types can change; verify with your installed Terminus version.

## Expected normalized display data

The Liquid template expects top-level arrays:

```json
{
  "today": [
    {"title":"School run","time":"08:30","all_day":false},
    {"title":"Holiday","time":"All day","all_day":true}
  ],
  "week": [
    {"day":"Tuesday","title":"Dentist"}
  ],
  "updated":"2026-10-10 09:00"
}
```

Events are already sorted and bucketed by **Europe/London** dates before rendering. All-day events should appear first in `today`. The template escapes event titles.

## Real calendars — integration still required

Terminus' documented Poll extensions fetch exchange data and then render the Liquid template. The documented Liquid filters do not include an ICS parser or RRULE expansion. An ICS endpoint returns text/calendar, **not** the normalized JSON expected by this screen. Directly inserting a user's private ICS URL into a public template or a static plugin archive is unsafe.

Two viable options to complete:

- A **built-in Terminus calendar exchange/transform** if a current Terminus release exposes a supported ICS-to-JSON capability. This must be verified in the target version.
- An **optional local adapter**, such as the separate ICS service proposed in PR #1, which stores subscriptions privately and provides normalized JSON behind authenticated local networking. This is not a no-service install.

Before advertising a one-click calendar connection, implement and test one supported approach end-to-end, including multiple sources, recurring event expansion, network/security boundaries, UI for configuration, and deployment.

## Supported format and release packaging

TRMNL Core private-plugin archive files are flat: `settings.yml`, `full.liquid`, and optionally additional viewport templates. The Python packaging script validates presence and produces a deterministic ZIP. GitHub Actions packages the archive as a workflow artifact on pushes and attaches it to a release when a version tag is pushed.

References:
- https://github.com/usetrmnl/terminus/blob/main/doc/extensions.adoc
- https://help.trmnl.com/en/articles/10542599-importing-and-exporting-private-plugins
