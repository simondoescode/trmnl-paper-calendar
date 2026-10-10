#!/usr/bin/env python3
"""Build a reproducible, flat TRMNL private plugin archive."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
OUTPUT = ROOT / "dist" / "paper-calendar.zip"
FILES = ["settings.yml", "full.liquid", "half_horizontal.liquid", "half_vertical.liquid", "quadrant.liquid"]


def package():
    for mandatory in FILES[:2]:
        if not (SOURCE / mandatory).is_file():
            raise SystemExit(f"Missing required plugin source: {mandatory}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in FILES:
            source = SOURCE / filename
            if not source.is_file():
                continue
            data = source.read_bytes()
            if filename.endswith(".liquid") and len(data) > 1_000_000:
                raise SystemExit(f"Template too large: {filename}")
            entry = zipfile.ZipInfo(filename, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, data)
    print(OUTPUT)


if __name__ == "__main__":
    package()
