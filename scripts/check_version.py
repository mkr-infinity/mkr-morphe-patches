#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Public version detector and comparison tool for target apps.

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "apps.json"


def fetch_url(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}", file=sys.stderr)
        return None


def check_telegram_version():
    """Detects latest official Telegram Android APK version from telegram.org."""
    html = fetch_url("https://telegram.org/android")
    if not html:
        return None
    # Match patterns like Telegram 11.8.2 for Android
    match = re.search(r"Telegram\s+([0-9]+\.[0-9]+\.[0-9]+)", html)
    if match:
        return match.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description="Check latest public versions for registered apps")
    parser.add_argument("--app", help="Check specific app ID or all if omitted")
    args = parser.parse_args()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    apps = config.get("apps", [])
    if args.app:
        apps = [a for a in apps if a["id"] == args.app]

    print("=" * 60)
    print("MKR MORPHE PATCHES — PUBLIC APP VERSION CHECKER")
    print("=" * 60)

    for app in apps:
        app_id = app["id"]
        name = app["display_name"]
        pkg = app["package_id"]
        tracked = app.get("compatible_versions", ["N/A"])[0]

        detected = None
        if app_id == "telegram":
            detected = check_telegram_version()

        print(f"App: {name} ({pkg})")
        print(f"  • Current top supported version: {tracked}")
        if detected:
            print(f"  • Latest public release found:   {detected}")
            if detected != tracked:
                print(f"  • Status: New public version available ({detected})")
            else:
                print("  • Status: Up to date")
        else:
            print("  • Public version discovery: Manual / APK artifact policy")
        print("-" * 60)


if __name__ == "__main__":
    main()
