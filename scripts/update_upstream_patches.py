#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Upstream patch monitor and update sync helper.
# Inspects MorpheApp/morphe-patches and MorpheApp/morphe-desktop official releases.

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_CONFIG = REPO_ROOT / "config" / "upstream.json"
APPS_CONFIG = REPO_ROOT / "config" / "apps.json"


def fetch_json(url, token=None):
    headers = {"User-Agent": "mkr-morphe-patches-updater"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error {e.code} for {url}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[!] Network error for {url}: {e}", file=sys.stderr)
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check official Morphe upstream releases for updates")
    parser.add_argument("--dry-run", action="store_true", help="Check upstream without writing changes to disk")
    args = parser.parse_args()

    print("[*] Checking official Morphe upstream repositories for updates...")
    if args.dry_run:
        print("[i] Dry-run mode active. No files will be modified.")
    token = os.environ.get("GITHUB_TOKEN")


    if not UPSTREAM_CONFIG.is_file():
        print(f"[ERROR] Missing config: {UPSTREAM_CONFIG}", file=sys.stderr)
        return 1

    with open(UPSTREAM_CONFIG, "r", encoding="utf-8") as f:
        upstream_data = json.load(f)

    with open(APPS_CONFIG, "r", encoding="utf-8") as f:
        apps_data = json.load(f)

    updates_found = []
    github_output = os.environ.get("GITHUB_OUTPUT")

    for src in upstream_data.get("upstream_sources", []):
        if not src.get("enabled", True):
            continue

        repo = src["repository"]
        current = src["current_tracked_release"]
        api_url = src["api_url"]
        print(f"[*] Querying upstream {repo} (current tracked: {current})...")

        release = fetch_json(api_url, token)
        if not release:
            print(f"[WARN] Could not retrieve release for {repo}, skipping.")
            continue

        latest_tag = release.get("tag_name")
        if not latest_tag:
            print(f"[WARN] No tag found in release response for {repo}.")
            continue

        print(f"[+] Found upstream release {latest_tag} for {repo}.")

        if latest_tag != current:
            print(f"[!] Update detected for {repo}: {current} -> {latest_tag}")
            updates_found.append({
                "source": src,
                "current": current,
                "latest": latest_tag,
                "release": release,
            })
            src["current_tracked_release"] = latest_tag
            src["latest_checked_at"] = release.get("published_at")
            src["release_html_url"] = release.get("html_url")

    if not updates_found:
        print("[+] Upstream sources are up to date. No updates needed.")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("update_detected=false\n")
        return 0

    # If morphe-patches updated, update compatible versions for official apps
    for upd in updates_found:
        if upd["source"]["id"] == "morphe-patches":
            new_tag = upd["latest"]
            print(f"[*] Synchronizing compatible versions from official morphe-patches {new_tag}...")
            # Fetch upstream patches-list.json from raw main or release
            raw_url = f"https://raw.githubusercontent.com/MorpheApp/morphe-patches/{new_tag}/patches-list.json"
            patches_list = fetch_json(raw_url, token)
            if not patches_list:
                # Fallback to main
                raw_url = "https://raw.githubusercontent.com/MorpheApp/morphe-patches/main/patches-list.json"
                patches_list = fetch_json(raw_url, token)

            if patches_list and "patches" in patches_list:
                # Extract targets per package
                targets_by_pkg = {}
                for p in patches_list["patches"]:
                    for cp in p.get("compatiblePackages") or []:
                        pkg = cp.get("packageName")
                        if not pkg:
                            continue
                        if pkg not in targets_by_pkg:
                            targets_by_pkg[pkg] = set()
                        for t in cp.get("targets") or []:
                            v = t.get("version")
                            if v:
                                targets_by_pkg[pkg].add(v)

                # Update apps.json for matching official packages
                for app in apps_data.get("apps", []):
                    pkg = app.get("package_id")
                    if pkg in targets_by_pkg:
                        discovered_versions = sorted(list(targets_by_pkg[pkg]), reverse=True)
                        existing_versions = set(app.get("compatible_versions", []))
                        merged = sorted(list(existing_versions.union(discovered_versions)), reverse=True)
                        app["compatible_versions"] = merged
                        app["source_revision"] = new_tag
                        print(f"[+] Updated {app['display_name']} compatible versions: {len(merged)} versions now tracked.")

    if not args.dry_run:
        # Save updated configs
        with open(UPSTREAM_CONFIG, "w", encoding="utf-8") as f:
            json.dump(upstream_data, f, indent=2)
            f.write("\n")

        with open(APPS_CONFIG, "w", encoding="utf-8") as f:
            json.dump(apps_data, f, indent=2)
            f.write("\n")
    else:
        print("[i] Dry-run: skipping writing config/upstream.json and config/apps.json.")


    # Generate PR description markdown
    summary_path = REPO_ROOT / "upstream_update_summary.md"
    summary_lines = [
        "## 🔄 Official Upstream Morphe Update Detected",
        "",
        "This pull request was automatically generated by the upstream monitoring workflow.",
        "It updates tracked upstream releases and app compatibility targets from official Morphe repositories.",
        "",
        "### Detected Upstream Changes",
        "",
        "| Source | Previous Version | New Version | Release Link |",
        "|---|---|---|---|",
    ]

    for upd in updates_found:
        src = upd["source"]
        name = src["name"]
        curr = upd["current"]
        latest = upd["latest"]
        link = upd["release"].get("html_url", "#")
        summary_lines.append(f"| **{name}** | `{curr}` | `{latest}` | [Release Notes]({link}) |")

    summary_lines.extend([
        "",
        "> [!IMPORTANT]",
        "> - Patched APKs are **never** built automatically on upstream updates.",
        "> - Please review the changes, run CI validation, and merge when ready.",
        "> - After merging, manually trigger **Build Patched APKs** to produce new APK builds on demand.",
        "",
        f"*Maintained by @mkr-infinity for [mkr-morphe-patches](https://github.com/mkr-infinity/mkr-morphe-patches)*",
    ])

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"[+] Generated update summary at {summary_path.relative_to(REPO_ROOT)}")

    # Set GitHub Actions output parameters
    primary_update = updates_found[0]["latest"]
    branch_name = f"morphe/upstream-update-{primary_update}"
    pr_title = f"chore(upstream): sync official Morphe patches {primary_update}"

    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("update_detected=true\n")
            f.write(f"new_version={primary_update}\n")
            f.write(f"branch_name={branch_name}\n")
            f.write(f"pr_title={pr_title}\n")
            f.write(f"pr_body_file={summary_path}\n")

    print("[SUCCESS] Upstream sync completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
