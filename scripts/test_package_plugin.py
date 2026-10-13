import tempfile
from pathlib import Path
import unittest
import zipfile

from package_plugin import package


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "src"
        self.source.mkdir()
        self.output = self.root / "dist" / "paper-calendar.zip"
        (self.source / "settings.yml").write_text("strategy: static\n")
        (self.source / "full.liquid").write_text('<div class="screen screen--og">Calendar</div>')

    def test_flat_allowlist_exact_source_and_determinism(self):
        (self.source / ".env").write_text("SECRET=not-for-export")
        (self.source / "calendars.local.json").write_text("private")
        (self.source / "unrelated.json").write_text("user data")
        package(self.source, self.output)
        first = self.output.read_bytes()
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ["settings.yml", "full.liquid"])
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.read("full.liquid"), (self.source / "full.liquid").read_bytes())
        package(self.source, self.output)
        self.assertEqual(first, self.output.read_bytes())

    def test_missing_required_file(self):
        (self.source / "full.liquid").unlink()
        with self.assertRaises(SystemExit):
            package(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_oversized_source_preserves_previous_archive(self):
        package(self.source, self.output)
        first = self.output.read_bytes()
        (self.source / "full.liquid").write_bytes(b"x" * 1_000_001)
        with self.assertRaises(SystemExit):
            package(self.source, self.output)
        self.assertEqual(first, self.output.read_bytes())


if __name__ == "__main__":
    unittest.main()
