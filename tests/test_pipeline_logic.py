#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Logic, regression, and assertion tests for MKR Morphe Patches automatic pipeline.

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_empty_app_selection():
    print("[*] Testing: empty app selection fails immediately...")
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "patch_apk.py"),
        "--selected-apps", "",
        "--morphe-jar", "dummy.jar",
        "--patches-mpp", "dummy.mpp",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 2, f"Expected code 2, got {proc.returncode}"
    assert "No applications were selected" in proc.stderr
    print("    [PASS] Empty selection rejected as expected.")


def test_invalid_app_id():
    print("[*] Testing: invalid app ID is rejected...")
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "patch_apk.py"),
        "--selected-apps", "non_existent_app_12345",
        "--morphe-jar", "dummy.jar",
        "--patches-mpp", "dummy.mpp",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 2, f"Expected code 2, got {proc.returncode}"
    assert "Invalid app ID requested" in proc.stderr
    print("    [PASS] Invalid app ID rejected as expected.")


def test_yaml_workflow_triggers():
    print("[*] Testing: build-patched-apk.yml has schedule & workflow_dispatch without push/pull_request...")
    workflow_path = REPO_ROOT / ".github" / "workflows" / "build-patched-apk.yml"
    content = workflow_path.read_text(encoding="utf-8")
    for forbidden in ["push:", "pull_request:"]:
        assert forbidden not in content, f"Forbidden trigger {forbidden} found in build-patched-apk.yml!"
    assert "schedule:" in content, "Missing schedule trigger in build-patched-apk.yml!"
    assert "workflow_dispatch:" in content, "Missing workflow_dispatch trigger in build-patched-apk.yml!"
    assert "force_full_rebuild:" in content, "Missing force_full_rebuild input in build-patched-apk.yml!"
    print("    [PASS] Trigger constraints strictly satisfied.")


def test_upstream_update_no_apk_build():
    print("[*] Testing: update-upstream.yml contains no APK build steps...")
    workflow_path = REPO_ROOT / ".github" / "workflows" / "update-upstream.yml"
    content = workflow_path.read_text(encoding="utf-8")
    assert "patch_apk.py" not in content, "update-upstream.yml must never call patch_apk.py!"
    assert "build-apks" not in content, "update-upstream.yml must never contain APK build jobs!"
    print("    [PASS] Upstream workflow cannot build APKs.")


def test_incremental_planner_no_change():
    print("[*] Testing: incremental planner with all up-to-date apps results in 0 builds...")
    with open(REPO_ROOT / "config" / "apps.json", "r", encoding="utf-8") as f:
        apps = json.load(f)["apps"]

    mock_manifest = {
        "manifest_version": "1.0.0",
        "patch_bundle_revision": "v1.47.0",
        "apps": {
            a["id"]: {
                "input_version": a["compatible_versions"][0],
                "patch_revision": "v1.47.0",
                "status": "SUCCESS",
                "asset_available": True,
                "output_apk": f"{a['id']}-patched.apk"
            }
            for a in apps
        }
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(mock_manifest, tf)
        mpath = tf.name

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as pf:
        plan_out = pf.name

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "plan_builds.py"),
        "--dry-run",
        "--manifest-file", mpath,
        "--output-plan", plan_out,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Planner exited with code {proc.returncode}: {proc.stderr}"

    with open(plan_out, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert plan["has_updates"] is False, f"Expected has_updates=False, got {plan['has_updates']}"
    assert plan["build_count"] == 0, f"Expected 0 builds, got {plan['build_count']}"
    assert plan["skip_count"] == len(apps), f"Expected {len(apps)} skips, got {plan['skip_count']}"
    print("    [PASS] No-change scenario correctly skips all builds.")


def test_incremental_planner_single_app_bump():
    print("[*] Testing: incremental planner with single app version bump selects only that app...")
    with open(REPO_ROOT / "config" / "apps.json", "r", encoding="utf-8") as f:
        apps = json.load(f)["apps"]

    mock_manifest = {
        "manifest_version": "1.0.0",
        "patch_bundle_revision": "v1.47.0",
        "apps": {
            a["id"]: {
                "input_version": a["compatible_versions"][0] if a["id"] != "telegram" else "11.7.0",  # Older version
                "patch_revision": "v1.47.0",
                "status": "SUCCESS",
                "asset_available": True,
                "output_apk": f"{a['id']}-patched.apk"
            }
            for a in apps
        }
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(mock_manifest, tf)
        mpath = tf.name

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as pf:
        plan_out = pf.name

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "plan_builds.py"),
        "--dry-run",
        "--manifest-file", mpath,
        "--output-plan", plan_out,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Planner exited with code {proc.returncode}: {proc.stderr}"

    with open(plan_out, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert plan["has_updates"] is True, f"Expected has_updates=True, got {plan['has_updates']}"
    assert plan["build_count"] == 1, f"Expected exactly 1 build, got {plan['build_count']}"
    built_entry = [p for p in plan["plan"] if p["needs_build"]][0]
    assert built_entry["id"] == "telegram", f"Expected telegram to be rebuilt, got {built_entry['id']}"
    print("    [PASS] Single app update correctly isolated in build matrix.")


def test_incremental_planner_force_full():
    print("[*] Testing: --force-full rebuilds all eligible applications regardless of state...")
    with open(REPO_ROOT / "config" / "apps.json", "r", encoding="utf-8") as f:
        apps = json.load(f)["apps"]

    mock_manifest = {
        "manifest_version": "1.0.0",
        "patch_bundle_revision": "v1.47.0",
        "apps": {
            a["id"]: {
                "input_version": a["compatible_versions"][0],
                "patch_revision": "v1.47.0",
                "status": "SUCCESS",
                "asset_available": True,
                "output_apk": f"{a['id']}-patched.apk"
            }
            for a in apps
        }
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(mock_manifest, tf)
        mpath = tf.name

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as pf:
        plan_out = pf.name

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "plan_builds.py"),
        "--dry-run",
        "--manifest-file", mpath,
        "--output-plan", plan_out,
        "--force-full",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, f"Planner exited with code {proc.returncode}: {proc.stderr}"

    with open(plan_out, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert plan["has_updates"] is True
    assert plan["build_count"] == len(apps), f"Expected all {len(apps)} apps in full rebuild, got {plan['build_count']}"
    print("    [PASS] Force full rebuild successfully overrides incremental skip.")


def test_release_publisher_manifest_consolidation():
    print("[*] Testing: publish_release.py consolidates manifests and generates release notes...")
    with tempfile.TemporaryDirectory() as temp_dir:
        td = Path(temp_dir)
        manifests_dir = td / "manifests"
        apks_dir = td / "apks"
        out_dir = td / "release_dist"
        manifests_dir.mkdir()
        apks_dir.mkdir()

        # Create mock APK and manifest for Telegram
        mock_apk = apks_dir / "telegram-patched.apk"
        mock_apk.write_bytes(b"dummy_apk_bytes_for_testing" * 100)

        mock_manifest = manifests_dir / "telegram-build-manifest.json"
        with open(mock_manifest, "w", encoding="utf-8") as f:
            json.dump({
                "app_id": "telegram",
                "display_name": "Telegram",
                "package_id": "org.telegram.messenger",
                "output_package_id": "org.telegram.messenger.morphe",
                "input_version": "11.8.2",
                "output_sha256": "abcdef1234567890",
                "output_size_bytes": 2600,
                "output_apk": "telegram-patched.apk",
                "signature_status": "verified",
                "status": "SUCCESS",
                "build_timestamp": "2026-10-17T00:00:00Z"
            }, f)

        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "publish_release.py"),
            "--manifests-dir", str(manifests_dir),
            "--apks-dir", str(apks_dir),
            "--output-dir", str(out_dir),
            "--run-number", "42",
            "--run-id", "test-run-42",
            "--dry-run"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0, f"Publisher exited with code {proc.returncode}: {proc.stderr}"

        # Verify staged assets
        staged_manifest = out_dir / "manifest.json"
        staged_notes = out_dir / "release_notes.md"
        staged_apk = out_dir / "telegram-patched.apk"

        assert staged_manifest.is_file(), "manifest.json was not created!"
        assert staged_notes.is_file(), "release_notes.md was not created!"
        assert staged_apk.is_file(), "telegram-patched.apk was not copied to release_dist!"

        with open(staged_manifest, "r", encoding="utf-8") as f:
            mdata = json.load(f)
        assert "telegram" in mdata.get("apps", {}), "telegram missing from consolidated manifest!"
        assert mdata["apps"]["telegram"]["input_version"] == "11.8.2"

        notes_content = staged_notes.read_text(encoding="utf-8")
        assert "Telegram" in notes_content
        assert "org.telegram.messenger" in notes_content
        assert "Build #42" in notes_content

    print("    [PASS] Release publisher correctly aggregates state and builds release notes.")


def main():
    print("Running pipeline logic tests...")
    test_empty_app_selection()
    test_invalid_app_id()
    test_yaml_workflow_triggers()
    test_upstream_update_no_apk_build()
    test_incremental_planner_no_change()
    test_incremental_planner_single_app_bump()
    test_incremental_planner_force_full()
    test_release_publisher_manifest_consolidation()
    print("\n[ALL PIPELINE LOGIC TESTS PASSED]")


if __name__ == "__main__":
    main()
