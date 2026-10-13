#!/usr/bin/env python3
"""Build a reproducible, flat TRMNL private plugin archive."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
OUTPUT = ROOT / "dist" / "paper-calendar.zip"
FILES = ["settings.yml", "full.liquid", "half_horizontal.liquid", "half_vertical.liquid", "quadrant.liquid"]


def package(source=SOURCE, output=OUTPUT):
    source = Path(source)
    output = Path(output)
    for mandatory in FILES[:2]:
        if not (source / mandatory).is_file():
            raise SystemExit(f"Missing required plugin source: {mandatory}")
    entries = []
    for filename in FILES:
        path = source / filename
        if not path.is_file():
            continue
        data = path.read_bytes()
        if len(data) > 1_000_000:
            raise SystemExit(f"Plugin file too large: {filename}")
        entries.append((filename, data))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename, data in entries:
                entry = zipfile.ZipInfo(filename, date_time=(2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, data)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


if __name__ == "__main__":
    print(package())
