import json
import tempfile
import unittest
from pathlib import Path

import bump


class BumpVersionTests(unittest.TestCase):
    def test_validate_version_normalizes_short_versions(self):
        self.assertEqual(bump.validate_version("1.2"), "1.2.0")

    def test_increment_version_handles_supported_parts_and_alias(self):
        self.assertEqual(bump.increment_version("1.2.3", "major"), "2.0.0")
        self.assertEqual(bump.increment_version("1.2.3", "minor"), "1.3.0")
        self.assertEqual(bump.increment_version("1.2.3", "path"), "1.2.4")

    def test_sync_version_updates_manifest_and_version_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            addon_dir = Path(tmpdir)
            manifest_path = addon_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps({"version": "0.0.1", "human_version": "0.0.1"}),
                encoding="utf-8",
            )

            bump.sync_version("3.4.5", addon_dir)

            self.assertEqual(bump.read_current_version(addon_dir), "3.4.5")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "3.4.5")
            self.assertEqual(manifest["human_version"], "3.4.5")
            self.assertEqual(
                (addon_dir / "VERSION").read_text(encoding="utf-8"),
                "3.4.5\n",
            )


if __name__ == "__main__":
    unittest.main()
