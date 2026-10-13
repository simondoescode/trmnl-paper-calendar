# Production plugin packaging and Terminus import

The packager exports the current production `src/full.liquid` and `src/settings.yml` unchanged into a flat TRMNL Core-format ZIP. It does not export the development backend, mock fixtures, `.env`, calendar configuration, or user data. The current plugin supports the 800 × 480 full-screen layout; it has no demo event data in its production settings.

## Build and test

With Python 3.12:

```sh
python -m unittest discover -s scripts -p test_package_plugin.py -v
python scripts/package_plugin.py
```

Without local Python, use Docker from PowerShell on Windows 11 or Ubuntu WSL2:

```sh
docker compose run --rm --no-deps --volume .:/plugin --workdir /plugin preview python -m unittest discover -s scripts -p test_package_plugin.py -v
docker compose run --rm --no-deps --volume .:/plugin --workdir /plugin preview python scripts/package_plugin.py
docker compose run --rm trmnlp lint
```

Build the preview image first with `docker compose build preview` if needed. The output is `dist/paper-calendar.zip`. The allowlist includes required `settings.yml` and `full.liquid`, plus optional half-horizontal, half-vertical and quadrant Liquid files if they exist. It never recursively packages the repository. Missing required files or files over 1 MB fail validation before replacing the previous archive. Entries use fixed timestamps and permissions for repeatable builds in the same Python environment.

GitHub Actions tests and packages PRs, main pushes and manual runs, uploading the ZIP as an artifact. Pushing a version tag such as `v0.1.0` additionally publishes a GitHub release with that ZIP attached. Only the tag-release job receives repository write permission; PR packaging remains read-only. Creating a tag is a separate release action, not part of building the archive locally.

## Terminus compatibility and data setup

This is a **TRMNL Core-format package**, not a Terminus-native extension export. End-to-end import of this exact archive into a running Terminus instance has not been verified. Use a Terminus version with Core plugin import support, select the TRMNL OG 2-bit model, and verify the imported template and settings before adding it to a playlist.

Importing static production settings does not create Poll exchanges or connect calendars. The verified repository workflow for native feeds is [manual Poll setup](TERMINUS_TODAY_WEEK.md): configure exchanges privately in Terminus and paste the entire production Liquid template, retaining its `screen screen--og` and `view view--full` wrappers. Do not put subscription URLs into the ZIP, template or static settings.

The template consumes `source_1`, `source_2` and `source_3`, each an array of calendar hashes with `events`. Events use `summary`, `start_at`, optional `location` and optional normalized `all_day`. It no longer consumes the early `today`/`week` prototype contract. Weather requires a compatible `weather` object. Refer to [the current data contract](LOCAL_PREVIEW.md) for optional normalized metadata and weather fields.

Terminus already parses native ICS exchanges, but raw parsing is not recurrence expansion. Reliable all-day classification, multi-day continuation, global ordering and Europe/London DST behavior need production-side normalization and runtime verification. The development preview supplies these attributes independently; it is not included in the package and does not demonstrate production feature parity.

References: [Terminus extension documentation](https://github.com/usetrmnl/terminus/blob/main/doc/extensions.adoc), [TRMNL private-plugin import/export](https://help.trmnl.com/en/articles/10542599-importing-and-exporting-private-plugins).
