#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Release publisher and manifest consolidator for MKR Morphe Patches.
# Collects build manifests, updates persistent release state, generates release notes,
# and publishes APK assets to GitHub Releases.

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_CONFIG = REPO_ROOT / "config" / "upstream.json"


def run_gh_command(args, timeout=120):
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


def get_current_patch_revision():
    if not UPSTREAM_CONFIG.is_file():
        return "unknown"
    try:
        with open(UPSTREAM_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        for src in data.get("upstream_sources", []):
            if src.get("id") == "morphe-patches" or src.get("repository") == "MorpheApp/morphe-patches":
                return src.get("current_tracked_release", "unknown")
    except Exception:
        pass
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Publish Patched APKs and Manifest to GitHub Release")
    parser.add_argument("--manifests-dir", default="build/outputs", help="Directory containing per-app build manifests")
    parser.add_argument("--apks-dir", default="release_apks", help="Directory where patched APK artifacts were downloaded")
    parser.add_argument("--previous-manifest", default="", help="Path to previous manifest.json downloaded from latest release")
    parser.add_argument("--output-dir", default="release_dist", help="Directory to stage release assets")
    parser.add_argument("--tag-name", default="patched-apks", help="Release tag name to create/update (default: patched-apks)")
    parser.add_argument("--run-number", default=os.environ.get("GITHUB_RUN_NUMBER", "1"), help="GitHub run number")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"), help="GitHub run ID")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "mkr-infinity/mkr-morphe-patches"), help="Target repository")
    parser.add_argument("--delete-previous-release", action="store_true", help="Delete previous release and old APK assets before publishing fresh release")
    parser.add_argument("--dry-run", action="store_true", help="Stage assets and print notes without calling gh release")

    args = parser.parse_args()

    manifests_dir = Path(args.manifests_dir)
    apks_dir = Path(args.apks_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    patch_revision = get_current_patch_revision()
    run_num = str(args.run_number)
    run_id = str(args.run_id)

    # 1. Load previous manifest if provided and not deleting previous release
    consolidated_apps = {}
    if not args.delete_previous_release and args.previous_manifest and Path(args.previous_manifest).is_file():
        try:
            with open(args.previous_manifest, "r", encoding="utf-8") as pf:
                prev_data = json.load(pf)
            consolidated_apps = prev_data.get("apps", {})
            print(f"[*] Loaded previous manifest with {len(consolidated_apps)} tracked applications.")
        except Exception as e:
            print(f"[!] Warning reading previous manifest: {e}", file=sys.stderr)

    # 2. Gather per-app build manifests from current run
    new_success_manifests = []
    new_non_success_manifests = []

    if manifests_dir.is_dir():
        for mf in sorted(manifests_dir.glob("*-build-manifest.json")):
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                aid = entry.get("app_id")
                status = entry.get("status")
                if not aid:
                    continue

                if status == "SUCCESS":
                    new_success_manifests.append(entry)
                    consolidated_apps[aid] = entry
                else:
                    new_non_success_manifests.append(entry)
            except Exception as e:
                print(f"[!] Error reading {mf}: {e}", file=sys.stderr)

    # 3. Locate newly built APKs and stage them
    staged_apks = []
    candidate_apks = []
    if apks_dir.is_dir():
        candidate_apks.extend(apks_dir.rglob("*.apk"))
    if manifests_dir.is_dir():
        candidate_apks.extend(manifests_dir.rglob("*.apk"))

    seen_apk_names = set()
    has_versioned = any("-morphe-patched.apk" in p.name for p in candidate_apks)
    for apk_path in candidate_apks:
        if has_versioned and apk_path.name.endswith("-patched.apk") and not apk_path.name.endswith("-morphe-patched.apk"):
            continue
        if apk_path.name in seen_apk_names or apk_path.stat().st_size == 0:
            continue
        dest = out_dir / apk_path.name
        if apk_path.resolve() != dest.resolve():
            shutil.copy2(apk_path, dest)
        seen_apk_names.add(apk_path.name)
        staged_apks.append(dest)

    # If no successful builds and no staged APKs, exit without creating a release
    if not staged_apks and not new_success_manifests:
        print("[*] No newly built APKs found to publish. Skipping release creation.")
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as sf:
                sf.write("### ℹ️ Release Publishing Skipped\n\nNo newly built APKs were generated in this run. No empty release was created.\n")
        return 0

    # 4. Save consolidated manifest.json
    manifest_doc = {
        "manifest_version": "1.0.0",
        "repository": args.repo,
        "github_run_number": int(run_num) if run_num.isdigit() else 1,
        "github_run_id": run_id,
        "patch_bundle_revision": patch_revision,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "apps": consolidated_apps,
    }

    manifest_dest = out_dir / "manifest.json"
    with open(manifest_dest, "w", encoding="utf-8") as f:
        json.dump(manifest_doc, f, indent=2)

    # 5. Build clean release notes markdown
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tag_name = args.tag_name
    release_title = f"MKR Morphe Patched APKs (Latest)"

    notes_lines = [
        f"### 📱 MKR Morphe Patched Android APKs",
        "",
        f"- **Updated At:** `{date_str}`",
        f"- **Morphe Patches Revision:** `{patch_revision}`",
        f"- **Workflow Run ID:** `{run_id}` (Build #{run_num})",
        "",
        f"#### ✅ Available Patched APKs ({len(staged_apks)}):",
        "",
        "| Application | Package ID | Version | Output Size | SHA-256 Checksum | Signature |",
        "|---|---|---|:---:|---|:---:|",
    ]

    for m in new_success_manifests:
        name = m.get("display_name", m.get("app_id"))
        pkg = m.get("package_id", "-")
        ver = m.get("input_version", "-")
        size = f"{m.get('output_size_bytes', 0) // (1024 * 1024)} MB"
        sha = m.get("output_sha256", "-")
        sig = "Verified" if m.get("signature_status") == "verified" else "Unverified"
        notes_lines.append(f"| **{name}** | `{pkg}` | `{ver}` | {size} | `{sha[:16]}...` | {sig} |")

    if new_non_success_manifests:
        notes_lines.extend([
            "",
            "#### ⚠️ Targets Skipped or Unavailable:",
            "",
            "| Application | Status | Reason |",
            "|---|---|---|",
        ])
        for m in new_non_success_manifests:
            notes_lines.append(f"| **{m.get('display_name', m.get('app_id'))}** | `{m.get('status')}` | {m.get('reason', '-')} |")

    if staged_apks:
        notes_lines.extend([
            "",
            "#### 📦 Downloadable APK Packages:",
            "",
            "| Package File | Size | Architecture |",
            "|---|:---:|:---:|",
        ])
        for apk in sorted(staged_apks, key=lambda p: p.name):
            size_mb = f"{apk.stat().st_size / (1024 * 1024):.1f} MB"
            if "arm64-v8a" in apk.name or "armv8" in apk.name:
                arch_tag = "`armv8` / `arm64-v8a` (64-bit ARM)"
            elif "armeabi-v7a" in apk.name or "armv7" in apk.name:
                arch_tag = "`armv7` / `armeabi-v7a` (32-bit ARM)"
            elif "universal" in apk.name:
                arch_tag = "`universal` (All Devices)"
            else:
                arch_tag = "`standard`"
            notes_lines.append(f"| `{apk.name}` | {size_mb} | {arch_tag} |")

    notes_lines.extend([
        "",
        "#### 📦 Assets & Verification Manifest:",
        "- Download individual `.apk` packages below.",
        "- Verify package checksums and build metadata in `manifest.json`.",
        "- Apps patched with Clone app (`.morphe`) can be installed side-by-side with official installations.",
        "",
        "> Maintained by @mkr-infinity for [mkr-morphe-patches](https://github.com/mkr-infinity/mkr-morphe-patches).",
    ])

    notes_text = "\n".join(notes_lines)
    notes_file = out_dir / "release_notes.md"
    notes_file.write_text(notes_text, encoding="utf-8")

    print("\n" + notes_text)

    # 6. Call gh release
    if args.dry_run:
        print("[i] Dry-run mode: staged assets in release_dist without uploading.")
        return 0

    release_assets = [str(manifest_dest)] + [str(p) for p in staged_apks]
    print(f"[*] Publishing release '{tag_name}' to {args.repo} with {len(release_assets)} assets...")

    if not args.dry_run and args.delete_previous_release:
        print(f"[*] Deleting previous release '{tag_name}' and clearing prior release APKs...")
        run_gh_command(["release", "delete", tag_name, "--repo", args.repo, "--yes", "--cleanup-tag"])
        rc_list, stdout_list, _ = run_gh_command(["release", "list", "--repo", args.repo, "--limit", "50"])
        if rc_list == 0 and stdout_list.strip():
            for line in stdout_list.strip().splitlines():
                parts = line.split()
                if parts:
                    old_t = parts[0]
                    print(f"[*] Deleting old release '{old_t}'...")
                    run_gh_command(["release", "delete", old_t, "--repo", args.repo, "--yes", "--cleanup-tag"])

    # Check if release tag already exists
    rc_view, _, _ = run_gh_command(["release", "view", tag_name, "--repo", args.repo])
    if rc_view == 0 and not args.delete_previous_release:
        print(f"[*] Release '{tag_name}' exists; uploading assets with --clobber...")
        rc_up, _, err_up = run_gh_command(
            ["release", "upload", tag_name, *release_assets, "--repo", args.repo, "--clobber"]
        )
        if rc_up != 0:
            print(f"[!] Warning uploading assets: {err_up}", file=sys.stderr)
        # Refresh release title and notes
        run_gh_command([
            "release", "edit", tag_name,
            "--repo", args.repo,
            "--title", release_title,
            "--notes-file", str(notes_file),
            "--latest",
        ])
    else:
        print(f"[*] Creating clean release '{tag_name}'...")
        rc_cr, _, err_cr = run_gh_command([
            "release", "create", tag_name,
            *release_assets,
            "--repo", args.repo,
            "--title", release_title,
            "--notes-file", str(notes_file),
            "--latest",
        ])
        if rc_cr != 0:
            print(f"[!] Warning creating release: {err_cr}", file=sys.stderr)
            return 1

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as sf:
            sf.write(f"\n### 🚀 GitHub Release Published\n\nRelease **[{release_title}](https://github.com/{args.repo}/releases/tag/{tag_name})** was published with **{len(staged_apks)}** APKs and `manifest.json`.\n")

    print(f"[SUCCESS] Release {tag_name} published successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
