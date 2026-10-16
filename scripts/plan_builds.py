#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Incremental build planner for MKR Morphe Patches.
# Evaluates target applications against release manifests and upstream revisions,
# producing a filtered build matrix and step summary.

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_APPS_CONFIG = REPO_ROOT / "config" / "apps.json"
DEFAULT_UPSTREAM_CONFIG = REPO_ROOT / "config" / "upstream.json"
DEFAULT_OUTPUT_PLAN = REPO_ROOT / "build" / "outputs" / "build_plan.json"

MANIFEST_FILENAME = "manifest.json"


def write_github_output(key: str, value: str) -> None:
    """Appends key=value to GITHUB_OUTPUT environment file if running in GitHub Actions."""
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            if "\n" in value:
                f.write(f"{key}<<EOF_PLANNER\n{value}\nEOF_PLANNER\n")
            else:
                f.write(f"{key}={value}\n")
    else:
        preview = value if len(value) < 120 else value[:120] + "..."
        print(f"[GITHUB_OUTPUT] {key}={preview}")


def run_gh_command(args, timeout=60):
    """Executes gh CLI command with environment auth token."""
    env = os.environ.copy()
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if token:
        env["GH_TOKEN"] = token
    try:
        proc = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "gh CLI binary not found in PATH"
    except Exception as e:
        return 1, "", str(e)


def fetch_latest_release_manifest(repo: str = None) -> dict:
    """Fetches and parses manifest.json from the latest GitHub Release of the repository."""
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY")

    if not repo:
        print("[*] No GITHUB_REPOSITORY set; skipping remote manifest fetch.")
        return {}

    print(f"[*] Probing previous build state from latest release in {repo}...")
    rc, stdout, stderr = run_gh_command(
        ["release", "view", "--repo", repo, "--json", "tagName,assets"]
    )
    if rc != 0:
        print(f"[*] No previous release found in {repo} (rc={rc}): {stderr.strip()}")
        return {}

    try:
        data = json.loads(stdout)
        assets = data.get("assets", [])
        has_manifest = any(a.get("name") == MANIFEST_FILENAME for a in assets)
        available_apks = {a.get("name") for a in assets if a.get("name", "").endswith(".apk")}

        if not has_manifest:
            print("[*] Latest release found, but contains no manifest.json.")
            return {}

        tag = data.get("tagName")
        temp_dest = REPO_ROOT / "build" / "previous_manifest.json"
        temp_dest.parent.mkdir(parents=True, exist_ok=True)

        rc_dl, _, err_dl = run_gh_command(
            ["release", "download", tag, "--repo", repo, "-p", MANIFEST_FILENAME, "-O", str(temp_dest), "--clobber"]
        )
        if rc_dl == 0 and temp_dest.is_file():
            with open(temp_dest, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            # Annotate with available APK assets
            manifest_apps = manifest_data.get("apps", {})
            for aid, ainfo in manifest_apps.items():
                expected_apk = ainfo.get("output_apk") or f"{aid}-patched.apk"
                ainfo["asset_available"] = expected_apk in available_apks
            print(f"[+] Successfully loaded previous manifest from release '{tag}' ({len(manifest_apps)} tracked apps).")
            return manifest_data
        else:
            print(f"[!] Failed to download manifest.json: {err_dl.strip()}")
    except Exception as e:
        print(f"[!] Error reading previous release manifest: {e}", file=sys.stderr)

    return {}


def get_current_patch_revision(upstream_path: Path) -> str:
    """Reads current tracked official Morphe patch release revision."""
    if not upstream_path.is_file():
        return "unknown"
    try:
        with open(upstream_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for src in data.get("upstream_sources", []):
            if (src.get("id") in ("morphe-patches", "official_morphe_patches") or src.get("repository") == "MorpheApp/morphe-patches") and src.get("enabled", True):
                return src.get("current_tracked_release", "unknown")
    except Exception:
        pass
    return "unknown"


def probe_telegram_public_version() -> str:
    """Detects latest official Telegram Android APK version from telegram.org."""
    url = "https://telegram.org/android"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        match = re.search(r"Telegram\s+([0-9]+\.[0-9]+\.[0-9]+)", html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[*] Telegram public version probe note: {e}")
    return ""


def resolve_app_target_version(app: dict) -> str:
    """Determines the target usable version for an application."""
    app_id = app["id"]
    compatible_versions = app.get("compatible_versions", [])
    top_compatible = compatible_versions[0] if compatible_versions else "latest"

    # For Telegram, check if official live version is discoverable
    if app_id == "telegram":
        live_ver = probe_telegram_public_version()
        if live_ver:
            return live_ver

    return top_compatible


def plan_application_build(
    app: dict,
    previous_manifest_apps: dict,
    current_patch_revision: str,
    force_full: bool,
    is_explicitly_selected: bool,
) -> dict:
    """Evaluates an application and determines if it is eligible for rebuild."""
    app_id = app["id"]
    display_name = app["display_name"]
    package_id = app["package_id"]
    enabled = app.get("enabled", True)
    target_version = resolve_app_target_version(app)

    if not enabled:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "SKIP",
            "status": "SKIPPED_DISABLED",
            "reason": "Application is disabled in catalog",
            "needs_build": False,
        }

    # Force full rebuild bypasses incremental skips
    if force_full:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": "Full rebuild forced via workflow configuration",
            "needs_build": True,
        }

    prev = previous_manifest_apps.get(app_id)
    if not prev:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": "No previous build recorded in release manifest",
            "needs_build": True,
        }

    # If previous build failed, retry
    prev_status = prev.get("status")
    if prev_status != "SUCCESS":
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": f"Previous build status was {prev_status} (retrying build)",
            "needs_build": True,
        }

    # Check version divergence
    prev_version = prev.get("input_version") or prev.get("version")
    if target_version != "latest" and prev_version and target_version != prev_version:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": f"Target version updated: {prev_version} -> {target_version}",
            "needs_build": True,
        }

    # Check patch bundle revision divergence
    prev_patch_rev = prev.get("patch_revision")
    if current_patch_revision != "unknown" and prev_patch_rev and current_patch_revision != prev_patch_rev:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": f"Morphe patch bundle updated: {prev_patch_rev} -> {current_patch_revision}",
            "needs_build": True,
        }

    # Check if artifact missing from release
    if not prev.get("asset_available", True):
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": "Previous APK asset missing from GitHub release",
            "needs_build": True,
        }

    # If explicitly selected by user in manual dispatch without force_full
    if is_explicitly_selected:
        return {
            "id": app_id,
            "display_name": display_name,
            "package_id": package_id,
            "version": target_version,
            "action": "BUILD",
            "status": "ELIGIBLE_FOR_BUILD",
            "reason": "Manually selected for build via workflow dispatch",
            "needs_build": True,
        }

    # Up to date
    return {
        "id": app_id,
        "display_name": display_name,
        "package_id": package_id,
        "version": target_version,
        "action": "SKIP",
        "status": "SKIPPED_NO_CHANGE",
        "reason": f"Up to date at version {prev_version} (patch {prev_patch_rev or current_patch_revision})",
        "needs_build": False,
    }


def main():
    parser = argparse.ArgumentParser(description="MKR Morphe Patches Build Planner")
    parser.add_argument("--config", default=str(DEFAULT_APPS_CONFIG), help="Path to config/apps.json")
    parser.add_argument("--upstream", default=str(DEFAULT_UPSTREAM_CONFIG), help="Path to config/upstream.json")
    parser.add_argument("--manifest-file", default="", help="Path to local manifest.json (overrides remote fetch)")
    parser.add_argument("--selected-apps", default="", help="Comma-separated app IDs or 'all'")
    parser.add_argument("--force-full", action="store_true", help="Force rebuilding all eligible applications")
    parser.add_argument("--output-plan", default=str(DEFAULT_OUTPUT_PLAN), help="Path to save build plan JSON")
    parser.add_argument("--dry-run", action="store_true", help="Dry run planning without writing GITHUB_OUTPUT")
    parser.add_argument("--repo", default="", help="GitHub repository name (owner/repo)")

    args = parser.parse_args()

    config_path = Path(args.config)
    upstream_path = Path(args.upstream)
    output_plan_path = Path(args.output_plan)

    if not config_path.is_file():
        print(f"[ERROR] Apps config file missing: {config_path}", file=sys.stderr)
        return 1

    with open(config_path, "r", encoding="utf-8") as f:
        apps_data = json.load(f)

    registered_apps = apps_data.get("apps", [])
    apps_by_id = {a["id"]: a for a in registered_apps}

    # Resolve selection
    selected_raw = args.selected_apps.strip()
    is_all = selected_raw.lower() in ("all", "select_all", "*", "")
    explicit_ids = set()
    if not is_all and selected_raw:
        explicit_ids = {s.strip() for s in selected_raw.split(",") if s.strip()}
        for aid in explicit_ids:
            if aid not in apps_by_id:
                print(f"[ERROR] Unknown app ID requested: '{aid}'", file=sys.stderr)
                return 2

    # Fetch previous manifest
    if args.manifest_file and Path(args.manifest_file).is_file():
        with open(args.manifest_file, "r", encoding="utf-8") as f:
            prev_manifest = json.load(f)
    else:
        prev_manifest = fetch_latest_release_manifest(args.repo)

    prev_apps = prev_manifest.get("apps", {})
    current_patch_revision = get_current_patch_revision(upstream_path)

    print("=" * 65)
    print("MKR MORPHE PATCHES — AUTOMATIC BUILD PLANNER")
    print(f"Timestamp:       {datetime.now(timezone.utc).isoformat()}")
    print(f"Patch Revision:  {current_patch_revision}")
    print(f"Force Full:      {args.force_full}")
    print(f"Selection Mode:  {'All Registered Apps' if is_all else ', '.join(sorted(explicit_ids))}")
    print("=" * 65)

    plan_entries = []
    matrix_include = []

    for app in registered_apps:
        aid = app["id"]
        # If user explicitly selected specific apps, skip unselected ones immediately
        if not is_all and aid not in explicit_ids:
            continue

        is_explicit = aid in explicit_ids
        eval_result = plan_application_build(
            app=app,
            previous_manifest_apps=prev_apps,
            current_patch_revision=current_patch_revision,
            force_full=args.force_full,
            is_explicitly_selected=is_explicit,
        )
        plan_entries.append(eval_result)

        if eval_result["needs_build"]:
            matrix_include.append({
                "id": aid,
                "name": app["display_name"],
                "package": app["package_id"],
                "version": eval_result["version"],
                "status": app.get("status", "supported"),
            })

    output_plan_path.parent.mkdir(parents=True, exist_ok=True)
    full_plan = {
        "planner_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patch_bundle_revision": current_patch_revision,
        "force_full": args.force_full,
        "total_targets_evaluated": len(plan_entries),
        "build_count": len(matrix_include),
        "skip_count": len(plan_entries) - len(matrix_include),
        "has_updates": len(matrix_include) > 0,
        "plan": plan_entries,
    }

    with open(output_plan_path, "w", encoding="utf-8") as pf:
        json.dump(full_plan, pf, indent=2)

    matrix_json = json.dumps({"include": matrix_include})
    has_updates_str = "true" if len(matrix_include) > 0 else "false"

    print(f"\n[+] Plan complete: {len(matrix_include)} to build, {len(plan_entries) - len(matrix_include)} to skip.")

    # Write GitHub Actions outputs
    if not args.dry_run:
        write_github_output("has_updates", has_updates_str)
        write_github_output("build_matrix", matrix_json)
        write_github_output("update_count", str(len(matrix_include)))
        write_github_output("skip_count", str(len(plan_entries) - len(matrix_include)))
        write_github_output("total_count", str(len(plan_entries)))
        write_github_output("patch_revision", current_patch_revision)

    # Render Step Summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    summary_lines = [
        "## 🧭 MKR Morphe Build Plan & Incremental Update Report",
        "",
        f"- **Patch Bundle Revision:** `{current_patch_revision}`",
        f"- **Evaluation Mode:** `{'Force Full Rebuild' if args.force_full else 'Incremental Change Detection'}`",
        f"- **Eligible Builds:** **{len(matrix_include)}** of {len(plan_entries)} applications",
        "",
        "| Application | Package ID | Target Version | Action | Decision Reason |",
        "|---|---|---|:---:|---|",
    ]

    for p in plan_entries:
        badge = "🔨 **BUILD**" if p["needs_build"] else "⏭️ **SKIP**"
        summary_lines.append(
            f"| **{p['display_name']}** | `{p['package_id']}` | `{p['version']}` | {badge} | {p['reason']} |"
        )

    summary_lines.extend([
        "",
        "> [!NOTE]",
        "> When incremental checks detect no version or patch bundle changes, unnecessary builds and duplicate releases are skipped automatically.",
        "",
    ])

    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)

    if summary_file and not args.dry_run:
        with open(summary_file, "a", encoding="utf-8") as sf:
            sf.write(summary_text + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
