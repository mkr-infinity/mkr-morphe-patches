#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Validation script for central app catalog, workflow inputs, and security constraints.

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "apps.json"
UPSTREAM_PATH = REPO_ROOT / "config" / "upstream.json"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "build-patched-apk.yml"

REQUIRED_APP_FIELDS = [
    "id",
    "display_name",
    "package_id",
    "upstream_source",
    "source_type",
    "source_revision",
    "compatible_versions",
    "tested_versions",
    "apk_input_policy",
    "has_custom_patches",
    "apk_build_supported",
    "side_by_side_supported",
    "signing_requirement",
    "enabled",
    "status",
]

PACKAGE_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")


def validate_apps_registry():
    print(f"[*] Validating {CONFIG_PATH.relative_to(REPO_ROOT)}...")
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    if not apps:
        raise ValueError("App catalog is empty or missing 'apps' list.")

    if len(apps) < 10:
        raise ValueError(f"Requirement not met: expected minimum 10 apps, found {len(apps)}.")

    seen_ids = set()
    seen_packages = set()

    for idx, app in enumerate(apps):
        app_id = app.get("id")
        if not app_id:
            raise ValueError(f"App at index {idx} has no 'id' field.")

        if app_id in seen_ids:
            raise ValueError(f"Duplicate app ID detected: {app_id}")
        seen_ids.add(app_id)

        # Validate required fields
        for field in REQUIRED_APP_FIELDS:
            if field not in app:
                raise ValueError(f"App '{app_id}' missing required field: '{field}'")

        # Validate package ID syntax
        package_id = app["package_id"]
        if not PACKAGE_REGEX.match(package_id):
            raise ValueError(f"App '{app_id}' has invalid package ID syntax: {package_id}")

        if package_id in seen_packages:
            raise ValueError(f"Duplicate package ID detected: {package_id}")
        seen_packages.add(package_id)

        # Validate versions list
        if not isinstance(app["compatible_versions"], list) or len(app["compatible_versions"]) == 0:
            raise ValueError(f"App '{app_id}' must have a non-empty 'compatible_versions' list.")

        # Validate status enum
        allowed_statuses = {"supported", "experimental", "unsupported_needs_patches"}
        if app["status"] not in allowed_statuses:
            raise ValueError(f"App '{app_id}' has invalid status '{app['status']}'. Must be one of {allowed_statuses}")

    print(f"[+] Successfully validated {len(apps)} applications in the central registry.")
    return seen_ids


def validate_workflow_inputs(registered_ids):
    print(f"[*] Validating workflow triggers and app inputs in {WORKFLOW_PATH.relative_to(REPO_ROOT)}...")
    if not WORKFLOW_PATH.is_file():
        raise FileNotFoundError(f"Missing workflow file: {WORKFLOW_PATH}")

    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Automated triggers: schedule and manual workflow_dispatch. Push and pull requests are excluded to prevent accidental runs on commit.
    if "pull_request:" in content:
        raise ValueError("Security violation: build-patched-apk.yml must have NO pull_request triggers.")

    if "push:" in content:
        raise ValueError("Trigger violation: build-patched-apk.yml must not run on push; use workflow_dispatch or schedule.")

    if "workflow_dispatch:" not in content or "schedule:" not in content:
        raise ValueError("Missing workflow_dispatch or schedule trigger in build-patched-apk.yml.")

    # Check for required inputs
    if "select_all:" not in content:
        raise ValueError("Missing 'select_all' boolean input in build-patched-apk.yml.")

    if "force_full_rebuild:" not in content:
        raise ValueError("Missing 'force_full_rebuild' boolean input in build-patched-apk.yml.")

    # Check each registered app ID exists as an input
    for app_id in registered_ids:
        # Match input key definition, e.g. "      youtube:"
        pattern = rf"^\s+{re.escape(app_id)}:\s*$"
        if not re.search(pattern, content, re.MULTILINE):
            raise ValueError(f"Workflow build-patched-apk.yml is missing manual input for app ID: '{app_id}'")

    print("[+] All registered apps have corresponding workflow dispatch inputs and safe triggers.")


def validate_secrets_and_binaries():
    print("[*] Verifying no private signing keys, secrets, or APK binaries are committed...")
    forbidden_extensions = {".apk", ".apkm", ".xapk", ".keystore", ".jks", ".p12"}
    violations = []

    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.suffix.lower() in forbidden_extensions:
            violations.append(str(path.relative_to(REPO_ROOT)))

    if violations:
        raise ValueError(f"Forbidden binary/signing files detected in repository: {violations}")

    print("[+] Repository clean: zero binaries or committed keystores found.")


def main():
    try:
        app_ids = validate_apps_registry()
        validate_workflow_inputs(app_ids)
        validate_secrets_and_binaries()
        print("\n[SUCCESS] All metadata, registry rules, and workflow parity checks passed.")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Validation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
