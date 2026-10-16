#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Patching engine driver for MKR Morphe Patches.
# Executes Morphe Desktop CLI, validates APK inputs/outputs, handles side-by-side clones,
# signature verification, and generates build manifests with step summaries.

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "apps.json"


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def inspect_apk(apk_path):
    """Inspects an APK file using zipfile to verify its integrity and basic layout."""
    if not zipfile.is_zipfile(apk_path):
        raise ValueError(f"File {apk_path} is not a valid APK/ZIP archive.")

    with zipfile.ZipFile(apk_path, "r") as z:
        names = set(z.namelist())
        if "AndroidManifest.xml" not in names:
            raise ValueError(f"APK {apk_path} is missing AndroidManifest.xml")
        if not any(name.startswith("classes") and name.endswith(".dex") for name in names):
            raise ValueError(f"APK {apk_path} contains no DEX bytecode files.")

    size = os.path.getsize(apk_path)
    checksum = sha256_file(apk_path)
    return {
        "size": size,
        "sha256": checksum,
    }


def parse_binary_manifest_fallback(apk_path):
    """Fallback parser: extracts string candidates from binary AndroidManifest.xml when aapt is unavailable."""
    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            data = z.read("AndroidManifest.xml")

        # Binary XML header check
        if len(data) < 8 or struct.unpack("<H", data[:2])[0] != 0x0003:
            return None

        # Search for ASCII package string candidates within string pool
        text = data.decode("latin-1", errors="ignore")
        # Extract reverse-domain strings
        import re
        matches = re.findall(r"([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(\.[a-z0-9_]+)+)", text)
        if matches:
            candidates = [m[0] for m in matches if not m[0].startswith("android.") and not m[0].startswith("schemas.")]
            if candidates:
                return candidates[0]
    except Exception:
        pass
    return None


def parse_app_manifest_aapt(apk_path):
    """Attempts to extract package and version using aapt2 or aapt, with binary XML fallback."""
    aapt_cmd = shutil.which("aapt2") or shutil.which("aapt")
    if aapt_cmd:
        try:
            proc = subprocess.run([aapt_cmd, "dump", "badging", str(apk_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                pkg_name = None
                ver_name = None
                for line in proc.stdout.splitlines():
                    if line.startswith("package:"):
                        for part in line.split():
                            if part.startswith("name='"):
                                pkg_name = part.split("'")[1]
                            elif part.startswith("versionName='"):
                                ver_name = part.split("'")[1]
                return pkg_name, ver_name
        except Exception as e:
            print(f"[!] aapt inspection error: {e}", file=sys.stderr)

    # Fallback if aapt is unavailable or failed
    fallback_pkg = parse_binary_manifest_fallback(apk_path)
    return fallback_pkg, None


def verify_apk_signature(apk_path):
    """Verifies output APK cryptographic signature using apksigner if available."""
    apksigner_cmd = shutil.which("apksigner")
    if not apksigner_cmd:
        return {"status": "unverified", "details": "apksigner tool not in PATH"}

    try:
        proc = subprocess.run([apksigner_cmd, "verify", "--verbose", str(apk_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        is_valid = proc.returncode == 0
        return {
            "status": "verified" if is_valid else "signature_verification_failed",
            "valid": is_valid,
            "stdout": proc.stdout.strip()[:500] if proc.stdout else "",
            "stderr": proc.stderr.strip()[:500] if proc.stderr else "",
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Mkr-Morphe APK Patching Driver")
    parser.add_argument("--selected-apps", required=True, help="Comma-separated app IDs or 'all'")
    parser.add_argument("--morphe-jar", required=True, help="Path to morphe-desktop-*-all.jar")
    parser.add_argument("--patches-mpp", required=True, help="Path to patches-*.mpp bundle")
    parser.add_argument("--input-dir", default="input-apks", help="Directory where input APKs are stored")
    parser.add_argument("--output-dir", default="build/outputs", help="Directory to save patched APKs")
    parser.add_argument("--experimental-mode", action="store_true", help="Allow experimental versions and pass --force")
    parser.add_argument("--enable-side-by-side", action="store_true", help="Enable Clone app patch for coexistence")
    parser.add_argument("--custom-clone-pkg", default="", help="Custom package name for side-by-side clone")
    parser.add_argument("--app-version", default="latest_compatible", help="Requested target version or 'latest_compatible'")
    parser.add_argument("--apk-url", default="", help="Direct APK download URL fallback")
    parser.add_argument("--extra-options", default="", help="Optional additional patch flags/options to forward to Morphe")

    args = parser.parse_args()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    apps_by_id = {app["id"]: app for app in config.get("apps", [])}

    # Resolve target apps
    if args.selected_apps.strip().lower() == "all":
        targets = [app for app in config["apps"] if app.get("enabled", True)]
    else:
        req_ids = [s.strip() for s in args.selected_apps.split(",") if s.strip()]
        if not req_ids:
            print("[ERROR] No applications were selected. Please select at least one app.", file=sys.stderr)
            sys.exit(2)
        targets = []
        for aid in req_ids:
            if aid not in apps_by_id:
                print(f"[ERROR] Invalid app ID requested: '{aid}'. Not in registry.", file=sys.stderr)
                sys.exit(2)
            targets.append(apps_by_id[aid])

    print("=" * 60)
    print("MKR MORPHE PATCHES — BUILD PIPELINE ENGINE")
    print(f"Target apps count: {len(targets)}")
    for t in targets:
        print(f"  • {t['display_name']} ({t['id']} -> {t['package_id']}) [Status: {t['status']}]")
    print(f"Experimental mode: {args.experimental_mode}")
    print(f"Side-by-side clone: {args.enable_side_by_side}")
    print("=" * 60)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    input_dir = Path(args.input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)

    build_results = []
    github_run_id = os.environ.get("GITHUB_RUN_ID", "local-run")

    for app in targets:
        app_id = app["id"]
        display_name = app["display_name"]
        expected_pkg = app["package_id"]
        print(f"\n[{display_name}] Starting build processing...")

        # 1. Locate APK
        candidate_apks = list(input_dir.glob(f"{app_id}*.apk")) + list(input_dir.glob(f"{expected_pkg}*.apk"))
        input_apk = candidate_apks[0] if candidate_apks else None

        # Auto-download from official source for Telegram if no APK was uploaded
        if not input_apk and app_id == "telegram":
            telegram_url = app.get("direct_download_url", "https://telegram.org/dl/android/apk")
            print(f"[{display_name}] Auto-fetching official Telegram APK from {telegram_url}...")
            dl_target = input_dir / f"{app_id}.apk"
            try:
                import urllib.request
                urllib.request.urlretrieve(telegram_url, dl_target)
                input_apk = dl_target
                print(f"[{display_name}] Downloaded official APK successfully ({os.path.getsize(dl_target)} bytes).")
            except Exception as e:
                print(f"[{display_name}] Failed to auto-download Telegram APK: {e}", file=sys.stderr)

        # Download from custom URL if passed via input
        if not input_apk and args.apk_url:
            print(f"[{display_name}] Downloading input APK from specified URL: {args.apk_url}")
            dl_target = input_dir / f"{app_id}.apk"
            try:
                import urllib.request
                urllib.request.urlretrieve(args.apk_url, dl_target)
                input_apk = dl_target
            except Exception as e:
                print(f"[{display_name}] Failed to download APK from URL: {e}", file=sys.stderr)

        if not input_apk or not input_apk.is_file():
            err_msg = f"No input APK found for {display_name}. Upload an artifact named 'apk-{app_id}' or provide a direct download URL."
            print(f"[FAIL] {err_msg}", file=sys.stderr)
            build_results.append({
                "app_id": app_id,
                "display_name": display_name,
                "package_id": expected_pkg,
                "status": "FAILED",
                "reason": err_msg,
            })
            continue

        # 2. Inspect and validate input APK
        try:
            inspect_info = inspect_apk(input_apk)
            actual_pkg, actual_ver = parse_app_manifest_aapt(input_apk)
            print(f"[{display_name}] Input APK validated. Size: {inspect_info['size']} bytes, SHA256: {inspect_info['sha256'][:16]}...")
            if actual_pkg and actual_pkg != expected_pkg:
                allowed_variants = app.get("package_variants", [expected_pkg])
                if actual_pkg not in allowed_variants:
                    err = f"Package mismatch! Expected '{expected_pkg}', detected '{actual_pkg}'."
                    print(f"[FAIL] {err}", file=sys.stderr)
                    build_results.append({
                        "app_id": app_id,
                        "display_name": display_name,
                        "package_id": expected_pkg,
                        "status": "FAILED",
                        "reason": err,
                    })
                    continue
        except Exception as e:
            err = f"Invalid input APK: {e}"
            print(f"[FAIL] {err}", file=sys.stderr)
            build_results.append({
                "app_id": app_id,
                "display_name": display_name,
                "package_id": expected_pkg,
                "status": "FAILED",
                "reason": err,
            })
            continue

        # 3. Check version compatibility (defaults to latest available version)
        top_available_ver = app.get("compatible_versions", ["unknown"])[0]
        if args.app_version in ("latest", "latest_compatible", ""):
            resolved_version = actual_ver or top_available_ver
            force_patch = True  # Always allow patching the latest available app version
        else:
            resolved_version = args.app_version
            force_patch = args.experimental_mode

        is_compatible = resolved_version in app.get("compatible_versions", [])
        if not is_compatible and not force_patch and not args.experimental_mode:
            err = f"Version '{resolved_version}' is not verified compatible with {display_name}. Enable experimental_mode to bypass."
            print(f"[FAIL] {err}", file=sys.stderr)
            build_results.append({
                "app_id": app_id,
                "display_name": display_name,
                "package_id": expected_pkg,
                "version": resolved_version,
                "status": "REJECTED_UNSUPPORTED_VERSION",
                "reason": err,
            })
            continue


        # 4. Construct Morphe CLI command
        out_apk = out_dir / f"{app_id}-patched.apk"
        result_json = out_dir / f"{app_id}-result.json"

        cmd = [
            "java",
            "-jar", str(args.morphe_jar),
            "patch",
            "-p", str(args.patches_mpp),
            "-o", str(out_apk),
            "-r", str(result_json),
        ]

        if args.experimental_mode or not is_compatible or force_patch:
            cmd.append("-f")


        applied_patches = []
        if args.enable_side_by_side:
            if app.get("side_by_side_supported", False):
                print(f"[{display_name}] Enabling side-by-side 'Clone app' patch...")
                cmd.extend(["-e", "Clone app"])
                applied_patches.append("Clone app")
                if args.custom_clone_pkg:
                    cmd.extend(["-O", f"Clone app:packageName={args.custom_clone_pkg}"])
            else:
                note = app.get("side_by_side_note", "Side-by-side cloning is not supported for this app target.")
                print(f"[{display_name}] WARNING: {note}")

        if app_id in ("youtube", "youtube_music"):
            print(f"[{display_name}] Adding GmsCore support patch...")
            cmd.extend(["-e", "GmsCore support"])
            applied_patches.append("GmsCore support")

        # Forward any extra user-defined options
        if args.extra_options:
            import shlex
            extra_tokens = shlex.split(args.extra_options)
            cmd.extend(extra_tokens)

        cmd.append(str(input_apk))

        # 5. Execute Morphe patcher
        print(f"[{display_name}] Executing Morphe Patcher command:")
        print("  " + " ".join(cmd))
        t_start = time.time()
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        t_duration = round(time.time() - t_start, 2)

        # Save build log
        log_path = out_dir / f"{app_id}-patch.log"
        log_path.write_text(proc.stdout, encoding="utf-8")

        if proc.returncode != 0 or not out_apk.is_file() or os.path.getsize(out_apk) == 0:
            err = f"Patcher failed with exit code {proc.returncode}."
            print(f"[FAIL] {err}", file=sys.stderr)
            print("--- LOG TAIL ---")
            print("\n".join(proc.stdout.splitlines()[-25:]))
            print("----------------")
            build_results.append({
                "app_id": app_id,
                "display_name": display_name,
                "package_id": expected_pkg,
                "version": resolved_version,
                "status": "FAILED",
                "reason": err,
                "log": str(log_path.relative_to(REPO_ROOT)),
            })
            continue

        # 6. Validate output APK and signature
        try:
            out_inspect = inspect_apk(out_apk)
            out_pkg, out_ver = parse_app_manifest_aapt(out_apk)
            sig_info = verify_apk_signature(out_apk)
        except Exception as e:
            err = f"Patched APK validation failed: {e}"
            print(f"[FAIL] {err}", file=sys.stderr)
            build_results.append({
                "app_id": app_id,
                "display_name": display_name,
                "package_id": expected_pkg,
                "status": "INVALID_OUTPUT_APK",
                "reason": err,
            })
            continue

        result_details = {}
        if result_json.is_file():
            try:
                with open(result_json, "r", encoding="utf-8") as rf:
                    result_details = json.load(rf)
            except Exception:
                pass

        # 7. Create build manifest
        manifest = {
            "app_id": app_id,
            "display_name": display_name,
            "package_id": expected_pkg,
            "output_package_id": out_pkg or (f"{expected_pkg}.morphe" if args.enable_side_by_side else expected_pkg),
            "input_version": resolved_version,
            "input_sha256": inspect_info["sha256"],
            "output_sha256": out_inspect["sha256"],
            "output_size_bytes": out_inspect["size"],
            "signature_status": sig_info.get("status"),
            "side_by_side_enabled": args.enable_side_by_side and app.get("side_by_side_supported", False),
            "experimental_mode": args.experimental_mode,
            "build_duration_seconds": t_duration,
            "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "github_run_id": github_run_id,
            "status": "SUCCESS",
            "applied_patches": applied_patches,
            "result_details": result_details,
        }

        manifest_path = out_dir / f"{app_id}-build-manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        print(f"[SUCCESS] {display_name} patched successfully in {t_duration}s!")
        print(f"  Artifact: {out_apk.name} ({out_inspect['size']} bytes)")
        print(f"  Manifest: {manifest_path.name}")
        build_results.append(manifest)

    # 8. Render GitHub Actions Step Summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    summary_lines = [
        "## 🛠️ MKR Morphe Patched APK Build Results",
        "",
        f"**Run ID:** `{github_run_id}` | **Date:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        "",
        "| Application | Package ID | Version | Status | Output Size | Side-by-Side |",
        "|---|---|---|---|---|---|",
    ]

    for res in build_results:
        app_name = res.get("display_name", res.get("app_id"))
        pkg = res.get("package_id", "-")
        ver = res.get("input_version", res.get("version", "-"))
        status = res.get("status", "UNKNOWN")
        badge = "✅ **Success**" if status == "SUCCESS" else f"❌ **{status}**"
        size = f"{res.get('output_size_bytes', 0) // 1024} KB" if "output_size_bytes" in res else "-"
        sxs = "Yes" if res.get("side_by_side_enabled") else "No"
        summary_lines.append(f"| **{app_name}** | `{pkg}` | `{ver}` | {badge} | {size} | {sxs} |")

    summary_lines.extend([
        "",
        "> [!NOTE]",
        "> Download your patched APKs and build manifests from the **Artifacts** section of this workflow run.",
        "> Cloned side-by-side installations can coexist with the official app installations.",
        "",
        "*MKR Morphe Patches engine maintained by @mkr-infinity*",
    ])

    summary_md = "\n".join(summary_lines)
    print("\n" + summary_md)

    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as sf:
            sf.write(summary_md + "\n")

    any_failures = any(r.get("status") != "SUCCESS" for r in build_results)
    if any_failures:
        print("\n[!] One or more apps failed patching. Review log artifacts for diagnostics.")
        if not any(r.get("status") == "SUCCESS" for r in build_results):
            sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
