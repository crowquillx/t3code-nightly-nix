#!/usr/bin/env python3

import importlib.util
import os
import unittest
from pathlib import Path

SCRIPT = Path(
    os.environ.get(
        "UPDATE_SCRIPT",
        Path(__file__).resolve().parent.parent / "scripts" / "update.py",
    )
)
SPEC = importlib.util.spec_from_file_location("update", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
UPDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATE)


def release(tag: str, *, asset: bool = True, prerelease: bool = True):
    version = tag.removeprefix("v")
    assets = (
        [
            {
                "name": f"T3-Code-{version}-x86_64.AppImage",
                "browser_download_url": f"https://example.invalid/{version}",
            }
        ]
        if asset
        else []
    )
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": prerelease,
        "assets": assets,
    }


class SelectReleaseTests(unittest.TestCase):
    def test_selects_highest_valid_nightly(self):
        releases = [
            release("v0.0.35-nightly.20260826.1194"),
            release("v0.0.35-nightly.20260826.1195"),
            release("v0.0.34"),
        ]
        version, _ = UPDATE.select_release(releases)
        self.assertEqual(version, "0.0.35-nightly.20260826.1195")

    def test_ignores_preview_and_missing_linux_asset(self):
        releases = [
            release("desktop-preview"),
            release("v0.0.36-nightly.20260827.1200", asset=False),
            release("v0.0.35-nightly.20260826.1195"),
        ]
        version, _ = UPDATE.select_release(releases)
        self.assertEqual(version, "0.0.35-nightly.20260826.1195")

    def test_fails_closed_without_valid_release(self):
        with self.assertRaises(RuntimeError):
            UPDATE.select_release([release("v0.0.35", prerelease=False)])


if __name__ == "__main__":
    unittest.main()
