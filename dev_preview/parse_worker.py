"""Disposable bounded parser process; its stderr never reaches service logs."""
import json
import resource
import sys
from datetime import date
from calendar_data import parse

resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
payload = json.load(sys.stdin)
json.dump(parse(payload["ics"].encode(), payload["name"], date.fromisoformat(payload["date"])), sys.stdout)
