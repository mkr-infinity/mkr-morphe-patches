#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Logic, regression, and assertion tests for MKR Morphe Patches automatic pipeline.

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


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
    print("[*] Testing: build-patched-apk.yml has schedule & workflow_dispatch without pull_request or push...")
    workflow_path = REPO_ROOT / ".github" / "workflows" / "build-patched-apk.yml"
    content = workflow_path.read_text(encoding="utf-8")
    assert "pull_request:" not in content, "Forbidden trigger pull_request found in build-patched-apk.yml!"
    assert "push:" not in content, "Forbidden trigger push found in build-patched-apk.yml!"
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


def test_apk_fetcher_version_normalization():
    print("[*] Testing: apk_fetcher version normalization and matching logic...")
    from scripts.apk_fetcher import normalize_version, versions_match

    # Exact matching
    assert versions_match("21.20.405", "21.20.405")
    # 'v' prefix
    assert versions_match("v21.20.405", "21.20.405")
    # Release suffix
    assert versions_match("10.70.0-release.0", "10.70.0")
    # Build text suffix
    assert versions_match("6.4 build 049", "6.4")
    # In-parenthesis architecture noise
    assert versions_match("21.20.405 (arm64-v8a)", "21.20.405")
    # Different versions do not match
    assert not versions_match("21.20.405", "21.20.406")
    assert not versions_match("", "21.20.405")
    print("    [PASS] Version normalization and matching behave accurately.")


def test_apk_fetcher_bundle_detection():
    print("[*] Testing: apk_fetcher split bundle and zip detection...")
    import zipfile
    from scripts.apk_fetcher import is_split_bundle

    # Extension-based checks
    assert is_split_bundle(Path("app.xapk"))
    assert is_split_bundle(Path("app.apkm"))
    assert is_split_bundle(Path("app.apks"))

    with tempfile.TemporaryDirectory() as td:
        bundle_path = Path(td) / "split.zip"
        with zipfile.ZipFile(bundle_path, "w") as z:
            z.writestr("base.apk", b"base")
            z.writestr("split_config.arm64_v8a.apk", b"split")
        assert is_split_bundle(bundle_path)

        standalone_path = Path(td) / "standalone.apk"
        with zipfile.ZipFile(standalone_path, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
            z.writestr("classes.dex", b"dex")
        assert not is_split_bundle(standalone_path)

    print("    [PASS] Bundle detection correctly identifies split packages and standalone APKs.")


def test_release_publisher_clean_versioned_apks():
    print("[*] Testing: publish_release.py prioritizes clean versioned APKs over raw names...")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        apks_dir = p / "apks"
        apks_dir.mkdir()
        out_dir = p / "dist"
        manifests_dir = p / "manifests"
        manifests_dir.mkdir()

        # Place raw apk and clean versioned apk
        (apks_dir / "youtube-patched.apk").write_bytes(b"apk1" * 50)
        (apks_dir / "YouTube-v21.20.405-morphe-patched.apk").write_bytes(b"apk2" * 50)

        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "publish_release.py"),
            "--manifests-dir", str(manifests_dir),
            "--apks-dir", str(apks_dir),
            "--output-dir", str(out_dir),
            "--tag-name", "patched-apks",
            "--dry-run",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0, f"Publisher failed: {proc.stderr}"

        # Clean versioned APK must be staged, raw -patched.apk deduplicated away
        assert (out_dir / "YouTube-v21.20.405-morphe-patched.apk").is_file()
        assert not (out_dir / "youtube-patched.apk").is_file()

    print("    [PASS] Release publisher clean versioned asset naming and deduplication verified.")


def test_architecture_abi_stripping():
    print("[*] Testing: architecture ABI detection and library stripping...")
    import zipfile
    from scripts.patch_apk import get_apk_abis, strip_zip_entries

    with tempfile.TemporaryDirectory() as td:
        dummy_apk = Path(td) / "dummy_multi_abi.apk"
        with zipfile.ZipFile(dummy_apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
            z.writestr("classes.dex", b"dex")
            z.writestr("lib/arm64-v8a/libfoo.so", b"arm64")
            z.writestr("lib/armeabi-v7a/libfoo.so", b"armv7")
            z.writestr("lib/x86/libfoo.so", b"x86")
            z.writestr("lib/x86_64/libfoo.so", b"x86_64")

        abis = get_apk_abis(dummy_apk)
        assert "arm64-v8a" in abis
        assert "armeabi-v7a" in abis
        assert "x86" in abis

        # Test arm64 stripping
        arm64_apk = Path(td) / "arm64_only.apk"
        strip_zip_entries(dummy_apk, arm64_apk, ["lib/x86/*", "lib/x86_64/*", "lib/armeabi-v7a/*"])
        with zipfile.ZipFile(arm64_apk, "r") as z:
            names = z.namelist()
            assert "lib/arm64-v8a/libfoo.so" in names
            assert "lib/armeabi-v7a/libfoo.so" not in names
            assert "lib/x86/libfoo.so" not in names

    print("    [PASS] Architecture ABI detection and stripping work accurately.")


def test_architecture_variant_naming():
    print("[*] Testing: architecture variant generation produces armv8, armv7, universal packages...")
    import zipfile
    from scripts.patch_apk import get_apk_abis

    with tempfile.TemporaryDirectory() as td:
        # Multi-ABI
        multi_apk = Path(td) / "multi.apk"
        with zipfile.ZipFile(multi_apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
            z.writestr("classes.dex", b"dex")
            z.writestr("lib/arm64-v8a/libfoo.so", b"arm64")
            z.writestr("lib/armeabi-v7a/libfoo.so", b"armv7")

        multi_abis = get_apk_abis(multi_apk)
        assert "arm64-v8a" in multi_abis
        assert "armeabi-v7a" in multi_abis

        # No native libs (universal fallback scenario)
        pure_dex_apk = Path(td) / "pure_dex.apk"
        with zipfile.ZipFile(pure_dex_apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
            z.writestr("classes.dex", b"dex")

        pure_abis = get_apk_abis(pure_dex_apk)
        assert pure_abis == []

    print("    [PASS] Architecture variant naming prerequisites verified.")


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
    test_apk_fetcher_version_normalization()
    test_apk_fetcher_bundle_detection()
    test_release_publisher_clean_versioned_apks()
    test_architecture_abi_stripping()
    test_architecture_variant_naming()
    print("\n[ALL PIPELINE LOGIC TESTS PASSED]")


if __name__ == "__main__":
    main()

