#!/usr/bin/env python3
"""Pin the newest valid T3 Code nightly Linux AppImage release."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_URL = "https://api.github.com/repos/pingdotgg/t3code/releases?per_page=100"
TAG_PATTERN = re.compile(
    r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"-nightly\.(?P<date>\d{8})\.(?P<build>\d+)$"
)
PIN_PATH = (
    Path(__file__).resolve().parent.parent
    / "pkgs"
    / "t3code-nightly"
    / "pin.json"
)


def release_key(release: dict[str, Any]) -> tuple[int, ...] | None:
    if release.get("draft") or not release.get("prerelease"):
        return None
    match = TAG_PATTERN.fullmatch(str(release.get("tag_name", "")))
    if match is None:
        return None
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch", "date", "build"))


def select_release(releases: list[dict[str, Any]]) -> tuple[str, str]:
    candidates: list[tuple[tuple[int, ...], str, str]] = []
    for release in releases:
        key = release_key(release)
        if key is None:
            continue
        version = str(release["tag_name"])[1:]
        expected_asset = f"T3-Code-{version}-x86_64.AppImage"
        for asset in release.get("assets", []):
            if asset.get("name") == expected_asset:
                candidates.append((key, version, str(asset["browser_download_url"])))
                break
    if not candidates:
        raise RuntimeError("no valid T3 Code nightly x86_64 AppImage release found")
    _, version, url = max(candidates)
    return version, url


def github_token() -> str | None:
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "t3code-nightly-nix-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _should_send_token(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host == "github.com" or host.endswith(
        (
            ".github.com",
            ".githubusercontent.com",
            ".githubassets.com",
            ".blob.core.windows.net",
            ".objects.githubusercontent.com",
        )
    ) or host in ("api.github.com", "objects.githubusercontent.com")


def _describe_rate_limit(error: urllib.error.HTTPError) -> str:
    remaining = error.headers.get("X-RateLimit-Remaining")
    reset = error.headers.get("X-RateLimit-Reset")
    retry_after = error.headers.get("Retry-After")
    detail = f"HTTP Error {error.code}: {error.reason}"
    try:
        body = error.read().decode("utf-8", "replace")[:500]
    except Exception:
        body = ""
    if body:
        detail += f" ({body.strip()})"
    hints: list[str] = []
    if remaining is not None:
        hints.append(f"remaining={remaining}")
    if reset is not None:
        hints.append(f"reset={reset}")
    if retry_after is not None:
        hints.append(f"retry-after={retry_after}s")
    if error.code in (403, 429) and not github_token():
        hints.append("set GITHUB_TOKEN to raise the GitHub API rate limit")
    if hints:
        detail += " [" + ", ".join(hints) + "]"
    return detail


def fetch_json(url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers=github_headers())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub releases request failed: {_describe_rate_limit(error)}") from error
    if not isinstance(payload, list):
        raise RuntimeError("GitHub releases response was not a list")
    return payload


def hash_url(url: str) -> str:
    digest = hashlib.sha256()
    headers: dict[str, str] = {"User-Agent": "t3code-nightly-nix-updater"}
    token = github_token()
    if token and _should_send_token(url):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"nightly asset download failed: {_describe_rate_limit(error)}") from error
    encoded = base64.b64encode(digest.digest()).decode("ascii")
    return f"sha256-{encoded}"


def write_pin(version: str, hash_value: str) -> None:
    payload = {"version": version, "hash": hash_value}
    rendered = json.dumps(payload, indent=2) + "\n"
    PIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=PIN_PATH.parent,
        delete=False,
    ) as handle:
        handle.write(rendered)
        temporary_path = Path(handle.name)
    temporary_path.replace(PIN_PATH)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help="GitHub-compatible releases API URL",
    )
    args = parser.parse_args()

    current = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    version, asset_url = select_release(fetch_json(args.api_url))
    if current.get("version") == version:
        print(f"T3 Code nightly {version} is already pinned")
        return 0

    hash_value = hash_url(asset_url)
    write_pin(version, hash_value)
    print(f"Updated T3 Code nightly to {version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
