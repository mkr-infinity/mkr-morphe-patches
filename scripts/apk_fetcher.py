#!/usr/bin/env python3
# Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
# Multi-source automated APK downloader and bundle merger for MKR Morphe Patches.
# Inspired by RookieEnough/Morphe-AutoBuilds: fetches base APKs from multiple sources
# (APKPure API, Aptoide, Uptodown, official direct URLs) and merges split bundles using APKEditor.

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    cffi_requests = None
    HAS_CURL_CFFI = False

# Standard desktop & mobile user agents
DESKTOP_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

APKPURE_API_URL = "https://tapi.pureapk.com/v3/get_app_his_version"
APKPURE_API_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 5 Build/TQ3A.230901.001); APKPure/3.20.34 (Aegon)",
    "Ual-Access-Businessid": "projecta",
    "Ual-Access-ProjectA": json.dumps({
        "device_info": {
            "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"],
            "android_id": "50f838123d9a9c94",
            "brand": "google",
            "country": "United States",
            "country_code": "US",
            "language": "en-US",
            "manufacturer": "Google",
            "mode": "Pixel 5",
            "os_ver": "33",
            "os_ver_name": "13",
            "platform": 1,
            "product": "redfin",
            "screen_height": 1080,
            "screen_width": 1920,
        },
        "host_app_info": {
            "build_no": "468",
            "channel": "",
            "md5": "6756e53158d6f6c013650a40d8f1147b",
            "pkg_name": "com.apkpure.aegon",
            "sdk_ver": "3.20.34",
            "version_code": 3203427,
            "version_name": "3.20.34",
        },
    }),
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
}

APTOIDE_API_URL = "https://ws75.aptoide.com/api/7/apps/search/query="


def normalize_version(version: str) -> str:
    """Normalize version string by removing build suffixes and non-digit noise."""
    if not version:
        return ""
    clean = re.sub(r"[\(\[].*?[\)\]]", "", version)
    clean = re.sub(r"\s+build\s+\d+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"-release.*$", "", clean, flags=re.IGNORECASE)
    parts = re.findall(r"\d+", clean)
    return ".".join(parts) if parts else clean.strip().lower()


def versions_match(v1: str, v2: str) -> bool:
    """Compare two version strings with normalization."""
    if not v1 or not v2:
        return False
    if v1.strip().lower() == v2.strip().lower():
        return True
    n1 = normalize_version(v1)
    n2 = normalize_version(v2)
    return bool(n1) and bool(n2) and n1 == n2


def download_file(url: str, dest_path: Path, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> bool:
    """Download file with progress and basic retry."""
    req_headers = {"User-Agent": DESKTOP_UA}
    if headers:
        req_headers.update(headers)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    for attempt in range(1, 4):
        try:
            downloaded = 0
            total_size = 0
            if HAS_CURL_CFFI:
                session = cffi_requests.Session(impersonate="chrome120")
                response = None
                try:
                    response = session.get(url, headers=req_headers, stream=True, timeout=timeout)
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))
                    with open(temp_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                finally:
                    if response is not None:
                        try:
                            response.close()
                        except Exception:
                            pass
                    try:
                        session.close()
                    except Exception:
                        pass
            else:
                req = urllib.request.Request(url, headers=req_headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    total_size = int(response.headers.get("content-length", 0))
                    with open(temp_path, "wb") as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

            if total_size > 0 and downloaded < total_size:
                raise IOError(f"Truncated download ({downloaded}/{total_size} bytes)")

            temp_path.replace(dest_path)
            logging.info(f"Successfully downloaded {dest_path.name} ({downloaded} bytes).")
            return True
        except Exception as e:
            logging.warning(f"Download attempt {attempt} failed for {url}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            # Attempt curl CLI fallback if Python download failed
            try:
                cmd = ["curl", "-sSL", "-L", "-A", req_headers.get("User-Agent", DESKTOP_UA), "-o", str(temp_path), url]
                subprocess.run(cmd, check=True, timeout=timeout)
                if temp_path.is_file() and temp_path.stat().st_size > 10000:
                    temp_path.replace(dest_path)
                    logging.info(f"Successfully downloaded {dest_path.name} via curl CLI fallback ({dest_path.stat().st_size} bytes).")
                    return True
            except Exception as ce:
                logging.debug(f"curl CLI fallback failed for {url}: {ce}")
                if temp_path.exists():
                    temp_path.unlink()
            if attempt < 3:
                time.sleep(2 * attempt)

    return False


def is_split_bundle(file_path: Path) -> bool:
    """Check if the downloaded file is a split APK bundle (XAPK, APKM, APKS, or split zip)."""
    if file_path.suffix.lower() in (".xapk", ".apkm", ".apks"):
        return True
    try:
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, "r") as z:
                names = z.namelist()
                apk_entries = [n for n in names if n.lower().endswith(".apk")]
                if len(apk_entries) > 1:
                    return True
                # Check for manifest with splits
                if "manifest.json" in names or "info.json" in names:
                    return True
    except Exception:
        pass
    return False


def download_apkeditor(tools_dir: Path) -> Optional[Path]:
    """Download APKEditor.jar tool for merging split bundles if not already cached."""
    tools_dir.mkdir(parents=True, exist_ok=True)
    editor_path = tools_dir / "APKEditor.jar"
    if editor_path.is_file() and editor_path.stat().st_size > 100000:
        return editor_path

    urls = [
        "https://github.com/REAndroid/APKEditor/releases/download/V1.4.3/APKEditor-1.4.3.jar",
        "https://github.com/REAndroid/APKEditor/releases/latest/download/APKEditor.jar",
    ]
    for url in urls:
        logging.info(f"Fetching APKEditor from {url}...")
        if download_file(url, editor_path):
            return editor_path

    return None


def merge_bundle_to_apk(bundle_path: Path, output_apk: Path, tools_dir: Path) -> bool:
    """Merge split bundle (.xapk, .apkm, or zip) into standalone installable APK using APKEditor."""
    editor = download_apkeditor(tools_dir)
    if not editor:
        logging.error("Could not obtain APKEditor.jar for merging split bundle.")
        return False

    logging.info(f"Merging split bundle {bundle_path.name} into {output_apk.name} using APKEditor...")
    cmd = [
        "java", "-jar", str(editor),
        "m",
        "-f",
        "-i", str(bundle_path),
        "-o", str(output_apk),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode == 0 and output_apk.is_file() and output_apk.stat().st_size > 100000:
            logging.info(f"Successfully merged split bundle into {output_apk.name} ({output_apk.stat().st_size} bytes).")
            return True
        logging.error(f"APKEditor merge failed with return code {proc.returncode}: {proc.stderr}")
    except Exception as e:
        logging.error(f"Error running APKEditor: {e}")

    return False


def fetch_official_direct(app_cfg: dict, dest_path: Path) -> Tuple[bool, str]:
    """Fetch base APK from configured official direct download URL if available."""
    direct_url = app_cfg.get("direct_download_url")
    if not direct_url:
        return False, ""

    logging.info(f"Attempting direct official download from {direct_url}...")
    if download_file(direct_url, dest_path):
        ver = app_cfg.get("tested_versions", ["latest"])[0]
        return True, ver
    return False, ""


def fetch_from_apkpure_api(
    package_id: str,
    candidate_versions: List[str],
    dest_path: Path,
) -> Tuple[bool, str]:
    """Fetch base APK directly via APKPure's client API (tapi.pureapk.com).
    Bypasses Cloudflare Turnstile entirely with zero web scraping required."""
    logging.info(f"Querying APKPure API for package '{package_id}'...")
    api_url = f"{APKPURE_API_URL}?package_name={package_id}&hl=en"
    req = urllib.request.Request(api_url, headers=APKPURE_API_HEADERS)

    try:
        data = None
        if HAS_CURL_CFFI:
            session = None
            try:
                session = cffi_requests.Session(impersonate="chrome120")
                res = session.get(api_url, headers=APKPURE_API_HEADERS, timeout=25)
                if res.status_code == 200:
                    data = res.json()
            except Exception as e:
                logging.debug(f"curl_cffi APKPure query failed: {e}")
            finally:
                if session is not None:
                    try:
                        session.close()
                    except Exception:
                        pass

        if not data:
            req = urllib.request.Request(api_url, headers=APKPURE_API_HEADERS)
            with urllib.request.urlopen(req, timeout=25) as response:
                if response.status != 200:
                    logging.warning(f"APKPure API responded with status {response.status}")
                    return False, ""
                raw_data = response.read()
                try:
                    import gzip
                    raw_data = gzip.decompress(raw_data)
                except Exception:
                    pass
                data = json.loads(raw_data.decode("utf-8", errors="replace"))

        version_list = data.get("version_list", [])
        if not version_list:
            logging.info(f"APKPure API returned 0 versions for {package_id}")
            return False, ""

        logging.info(f"APKPure API returned {len(version_list)} versions for {package_id}.")

        # 1. Look for matching candidate version
        selected_entry = None
        selected_version = ""

        for candidate in candidate_versions:
            for entry in version_list:
                vname = (entry.get("version_name") or "").strip()
                if versions_match(vname, candidate):
                    urls = (entry.get("asset") or {}).get("urls") or []
                    if urls:
                        selected_entry = entry
                        selected_version = vname
                        logging.info(f"Found compatible version match on APKPure: v{selected_version}")
                        break
            if selected_entry:
                break

        # 2. Fallback: if candidate is 'latest_compatible' or no exact match, pick the latest entry with URLs
        if not selected_entry:
            for entry in version_list:
                urls = (entry.get("asset") or {}).get("urls") or []
                if urls:
                    selected_entry = entry
                    selected_version = (entry.get("version_name") or "latest").strip()
                    logging.info(f"No exact version match; selecting newest available APKPure version: v{selected_version}")
                    break

        if not selected_entry:
            return False, ""

        dl_url = selected_entry["asset"]["urls"][0]
        logging.info(f"Downloading {package_id} v{selected_version} from APKPure CDN...")
        if download_file(dl_url, dest_path):
            return True, selected_version

    except Exception as e:
        logging.warning(f"APKPure API lookup failed for {package_id}: {e}")

    return False, ""


def fetch_from_aptoide(
    package_id: str,
    candidate_versions: List[str],
    dest_path: Path,
) -> Tuple[bool, str]:
    """Fetch base APK from Aptoide API (ws75.aptoide.com)."""
    logging.info(f"Querying Aptoide API for package '{package_id}'...")
    url = f"{APTOIDE_API_URL}{package_id}"
    req = urllib.request.Request(url, headers={"User-Agent": DESKTOP_UA})

    try:
        data = None
        if HAS_CURL_CFFI:
            session = None
            try:
                session = cffi_requests.Session(impersonate="chrome120")
                res = session.get(url, headers={"User-Agent": DESKTOP_UA}, timeout=20)
                if res.status_code == 200:
                    data = res.json()
            except Exception as e:
                logging.debug(f"curl_cffi Aptoide lookup failed: {e}")
            finally:
                if session is not None:
                    try:
                        session.close()
                    except Exception:
                        pass

        if not data:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

        datalist = data.get("datalist", {}).get("list", [])
        if not datalist:
            return False, ""

        # Filter for exact package
        matching_apps = [a for a in datalist if a.get("package") == package_id]
        if not matching_apps:
            matching_apps = datalist

        selected_app = None
        selected_version = ""

        for candidate in candidate_versions:
            for app in matching_apps:
                vname = app.get("file", {}).get("vername", "")
                if versions_match(vname, candidate):
                    selected_app = app
                    selected_version = vname
                    break
            if selected_app:
                break

        if not selected_app and matching_apps:
            selected_app = matching_apps[0]
            selected_version = selected_app.get("file", {}).get("vername", "latest")

        if not selected_app:
            return False, ""

        file_url = selected_app.get("file", {}).get("path")
        if not file_url:
            return False, ""

        logging.info(f"Downloading {package_id} v{selected_version} from Aptoide CDN...")
        if download_file(file_url, dest_path):
            return True, selected_version

    except Exception as e:
        logging.warning(f"Aptoide query failed for {package_id}: {e}")

    return False, ""


def fetch_with_flaresolverr(url: str, flaresolverr_url: str) -> Optional[str]:
    """Solve Cloudflare challenges via FlareSolverr proxy service."""
    try:
        payload = json.dumps({
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
        }).encode("utf-8")
        req = urllib.request.Request(
            flaresolverr_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=70) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "ok":
                return data.get("solution", {}).get("response", "")
    except Exception as e:
        logging.debug(f"FlareSolverr request failed for {url}: {e}")
    return None


def resolve_and_download_apk(
    app_id: str,
    app_cfg: dict,
    requested_version: str = "latest_compatible",
    tools_dir: Path = Path("tools"),
    dest_dir: Path = Path("input_apks"),
) -> Tuple[Optional[Path], str]:
    """High-level resolver: searches across multiple sources, downloads the base APK,
    merges split bundles if necessary, and returns the verified standalone .apk path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    pkg = app_cfg["package_id"]
    display_name = app_cfg.get("display_name", app_id)

    # 1. Candidate versions determination
    compat_versions = app_cfg.get("compatible_versions", [])
    tested_versions = app_cfg.get("tested_versions", [])

    candidate_versions: List[str] = []
    if requested_version and requested_version != "latest_compatible":
        candidate_versions = [requested_version]
    else:
        # Prioritize tested, then compatible
        for v in tested_versions + compat_versions:
            if v and v not in candidate_versions:
                candidate_versions.append(v)

    logging.info(f"[{display_name}] Resolving base APK for candidate versions: {candidate_versions[:4]}")

    # Temporary download target
    raw_dest = dest_dir / f"raw_{app_id}_{pkg}.tmp"

    success = False
    resolved_version = ""

    # Strategy A: Official direct download if specified
    if not success and app_cfg.get("direct_download_url"):
        success, resolved_version = fetch_official_direct(app_cfg, raw_dest)

    # Strategy B: APKPure Mobile Client API (primary automated source)
    if not success:
        success, resolved_version = fetch_from_apkpure_api(pkg, candidate_versions, raw_dest)

    # Strategy C: Aptoide API
    if not success:
        success, resolved_version = fetch_from_aptoide(pkg, candidate_versions, raw_dest)

    if not success or not raw_dest.is_file() or raw_dest.stat().st_size < 10000:
        logging.error(f"[{display_name}] All automated download sources failed to retrieve base APK.")
        if raw_dest.exists():
            raw_dest.unlink()
        return None, ""

    # Handle bundles vs standalone APK
    final_apk = dest_dir / f"{app_id}.apk"

    if is_split_bundle(raw_dest):
        logging.info(f"[{display_name}] Downloaded file is a split bundle (XAPK/APKM/APKS). Merging...")
        merged = merge_bundle_to_apk(raw_dest, final_apk, tools_dir)
        raw_dest.unlink(missing_ok=True)
        if not merged:
            logging.error(f"[{display_name}] Bundle merge failed.")
            return None, ""
    else:
        raw_dest.replace(final_apk)

    logging.info(f"[{display_name}] Base APK ready at {final_apk} (v{resolved_version}, {final_apk.stat().st_size} bytes).")
    return final_apk, resolved_version


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 apk_fetcher.py <package_id> [candidate_version]")
        sys.exit(1)
    p = sys.argv[1]
    c = [sys.argv[2]] if len(sys.argv) > 2 else []
    dest = Path(f"/tmp/{p}.apk")
    ok, ver = fetch_from_apkpure_api(p, c, dest)
    print(f"Result: ok={ok}, ver={ver}")
