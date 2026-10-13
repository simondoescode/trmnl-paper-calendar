#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root = Path(__file__).resolve().parents[1]
source = root / "spikes" / "terminus-ics-poll"
output = root / "dist" / "terminus-ics-poll-spike.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", compression=ZIP_DEFLATED) as z:
    for name in ("settings.yml", "full.liquid"):
        z.write(source / name, arcname=name)
print(output)
