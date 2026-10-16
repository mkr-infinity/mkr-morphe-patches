#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Logic and assertion tests for MKR Morphe Patches pipeline.

import json
import subprocess
import sys
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
    print("[*] Testing: build-patched-apk.yml only has workflow_dispatch...")
    workflow_path = REPO_ROOT / ".github" / "workflows" / "build-patched-apk.yml"
    content = workflow_path.read_text(encoding="utf-8")
    for forbidden in ["push:", "pull_request:", "schedule:"]:
        assert forbidden not in content, f"Forbidden trigger {forbidden} found in build-patched-apk.yml!"
    assert "workflow_dispatch:" in content
    print("    [PASS] Trigger constraints strictly satisfied.")


def test_upstream_update_no_apk_build():
    print("[*] Testing: update-upstream.yml contains no APK build steps...")
    workflow_path = REPO_ROOT / ".github" / "workflows" / "update-upstream.yml"
    content = workflow_path.read_text(encoding="utf-8")
    assert "patch_apk.py" not in content, "update-upstream.yml must never call patch_apk.py!"
    assert "build-apks" not in content, "update-upstream.yml must never contain APK build jobs!"
    print("    [PASS] Upstream workflow cannot build APKs.")


def main():
    print("Running pipeline logic tests...")
    test_empty_app_selection()
    test_invalid_app_id()
    test_yaml_workflow_triggers()
    test_upstream_update_no_apk_build()
    print("\n[ALL PIPELINE LOGIC TESTS PASSED]")


if __name__ == "__main__":
    main()
