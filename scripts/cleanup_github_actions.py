#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Cleanup utility: Deletes previous GitHub Actions workflow runs and cleans repository history.

import os
import subprocess
import sys


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


def delete_previous_workflow_runs(repo: str, current_run_id: str):
    print(f"[*] Checking for previous GitHub Actions runs in {repo}...")
    rc, stdout, stderr = run_gh_command([
        "run", "list",
        "--repo", repo,
        "--limit", "100",
        "--json", "databaseId",
        "--jq", ".[].databaseId"
    ])
    if rc != 0:
        print(f"[!] Warning querying workflow runs: {stderr.strip()}", file=sys.stderr)
        return

    run_ids = [line.strip() for line in stdout.strip().splitlines() if line.strip()]
    deleted_count = 0
    for rid in run_ids:
        if str(rid) != str(current_run_id):
            print(f"[*] Deleting old workflow run {rid}...")
            rc_del, _, err_del = run_gh_command(["run", "delete", str(rid), "--repo", repo])
            if rc_del == 0:
                deleted_count += 1
            else:
                print(f"[!] Warning deleting run {rid}: {err_del.strip()}", file=sys.stderr)

    print(f"[+] Purged {deleted_count} previous workflow runs from repository history.")


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "mkr-infinity/mkr-morphe-patches")
    current_run_id = os.environ.get("GITHUB_RUN_ID", "")
    delete_previous_workflow_runs(repo, current_run_id)


if __name__ == "__main__":
    main()
