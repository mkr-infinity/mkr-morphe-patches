<!-- Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches) -->
<div align="center">

# ⚡ MKR Morphe Patches ⚡

**Personal Morphe-compatible Android patches with automatic patch updates and on-demand APK builds.**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL_v3.0-d97706.svg?style=flat-square)](LICENSE)
[![Morphe Compatible](https://img.shields.io/badge/Morphe-Compatible-f59e0b.svg?style=flat-square&logo=android)](https://github.com/MorpheApp)
[![Maintainer](https://img.shields.io/badge/Maintainer-mkr--infinity-b45309.svg?style=flat-square&logo=github)](https://github.com/mkr-infinity)
[![APK Builds](https://img.shields.io/badge/APK_Builds-Scheduled_%26_On--Demand-f59e0b.svg?style=flat-square)](.github/workflows/build-patched-apk.yml)
[![Upstream Sync](https://img.shields.io/badge/Upstream_Sync-Automated-d97706.svg?style=flat-square)](.github/workflows/update-upstream.yml)

<br>

<p align="center">
  <a href="https://morphe.software/add-source?github=mkr-infinity/mkr-morphe-patches">
    <img src="https://img.shields.io/badge/📲_Add_Source_to_Morphe-mkr--infinity%2Fmkr--morphe--patches-f59e0b.svg?style=for-the-badge&logo=android&logoColor=white" alt="Add Source to Morphe" />
  </a>
</p>

</div>

---

> [!WARNING]
> **Independent Project Notice:** This repository is an independent personal project maintained by [@mkr-infinity](https://github.com/mkr-infinity). It is **not** affiliated with, authorized, maintained, or endorsed by the official Morphe open-source organization, Google LLC, YouTube, Meta, Telegram FZ-LLC, X Corp, ByteDance, or any of their affiliates. All product and company names are trademarks™ or registered® trademarks of their respective holders.

---

## 🧭 Overview & Core Architecture

`mkr-morphe-patches` is an automated, configuration-driven Android patching laboratory and Morphe source repository:

1. **Automatic Daily & On-Demand APK Builds (`build-patched-apk.yml`)**:
   - Runs automatically on a daily schedule (`06:00 UTC`) or manually via `workflow_dispatch`.
   - **Incremental Build Planner (`scripts/plan_builds.py`)**: Fetches `manifest.json` from the latest release and diffs current target versions and patch bundle revisions. If nothing has changed, the build finishes in seconds with `SKIPPED_NO_CHANGE` without rebuilding APKs.
   - **Isolated Matrix Builds**: If one or more apps update, GitHub Actions launches targeted matrix build jobs only for affected apps.
   - **Consolidated Release Publisher (`scripts/publish_release.py`)**: Automatically updates `manifest.json`, rolls forward untouched APKs, publishes newly built APKs to GitHub Releases (`patched-apks`), and generates structured markdown release notes.
   - Manual builds support `Select all apps`, individual app checkboxes, and `force_full_rebuild`.
2. **Automatic Upstream Monitoring (`update-upstream.yml`)**:
   - Monitored weekly via scheduled GitHub Actions.
   - Compares releases from official upstream Morphe repositories (`MorpheApp/morphe-patches`, `MorpheApp/morphe-desktop`).
   - Opens a clean, reviewable pull request when new upstream releases or version targets are detected.
3. **CI Validation & Remote Patch Compilation (`validate.yml`)**:
   - Validates central catalog parity, security boundaries, and YAML integrity.
   - Verifies patch compilation remotely using GitHub Actions (`./gradlew :patches:buildAndroid`).

---

## 📱 Application Catalog & Compatibility Matrix

Every target application is centrally defined in [`config/apps.json`](config/apps.json):

| Application | Package Identifier | Source & Revision | Target Versions | Remote APK Build | Side-by-Side Coexist | Status |
|---|---|---|---|:---:|:---:|:---:|
| **YouTube** | `com.google.android.youtube` | `MorpheApp/morphe-patches` (v1.47.0) | `21.20.405`, `20.51.39`, `20.21.37` | ✅ | ✅ *(via GmsCore)* | `supported` |
| **YouTube Music** | `com.google.android.apps.youtube.music` | `MorpheApp/morphe-patches` (v1.47.0) | `9.20.53`, `9.15.51` | ✅ | ✅ *(via GmsCore)* | `supported` |
| **Reddit** | `com.reddit.frontpage` | `MorpheApp/morphe-patches` (v1.47.0) | `2026.24.0`, `2026.10.0` | ✅ | ✅ *(Clone app)* | `supported` |
| **Telegram** | `org.telegram.messenger` | Custom / Community | `11.8.2`, `11.7.1` | ✅ *(Auto-Download)* | ✅ *(Clone app)* | `supported` |
| **Smart Launcher** | `ginlemon.flowerfree` | Custom (`app.mkr.patches`) | `6.4 build 049`, `6.4` | ✅ | ⚠️ *(Launcher constraints)* | `experimental` |
| **MovieBox Pro Mobile** | `com.movieboxpro.android` | Custom (`app.mkr.patches`) | `15.6`, `15.5` | ✅ | ✅ *(Clone app)* | `experimental` |
| **Instagram** | `com.instagram.android` | Custom (`app.mkr.patches`) | `355.0.0.44.106` | ✅ | ❌ *(Facebook provider issues)* | `experimental` |
| **Facebook** | `com.facebook.katana` | Custom (`app.mkr.patches`) | `485.0.0.52.79` | ✅ | ❌ *(Internal signature locks)* | `experimental` |
| **Twitter / X** | `com.twitter.android` | Custom (`app.mkr.patches`) | `10.65.0-release.0` | ✅ | ⚠️ *(Post opening quirks)* | `experimental` |
| **TikTok** | `com.zhiliaoapp.musically` | Custom (`app.mkr.patches`) | `37.4.3`, `37.2.3` | ✅ | ✅ *(Clone app)* | `experimental` |

| **Twitch** | `tv.twitch.android.app` | Custom (`app.mkr.patches`) | `20.8.0`, `20.7.0` | ✅ | ❌ *(Native launch check)* | `experimental` |
| **Duolingo** | `com.duolingo` | Custom (`app.mkr.patches`) | `6.28.2`, `6.25.4` | ✅ | ❌ *(Signature locks)* | `experimental` |
| **Messenger** | `com.facebook.orca` | Custom (`app.mkr.patches`) | `480.0.0.45.109` | ✅ | ❌ *(Facebook provider issues)* | `experimental` |
| **Discord** | `com.discord` | Custom (`app.mkr.patches`) | `250.0`, `248.0` | ✅ | ✅ *(Clone app)* | `experimental` |


> [!NOTE]
> Targets marked `experimental` require the `experimental_mode` checkbox if the target APK version differs from strictly tested builds, or have known platform constraints documented in [`config/apps.json`](config/apps.json).

---

## 📲 How to Add This Repository to Morphe

You can add this repository as an official patch source directly inside **Morphe Manager** or **Morphe Desktop**:

### One-Click Web Registration
Click the link below on your Android device (with Morphe Manager installed):
**[https://morphe.software/add-source?github=mkr-infinity/mkr-morphe-patches](https://morphe.software/add-source?github=mkr-infinity/mkr-morphe-patches)**

### Manual Source Registration
1. Open **Morphe Manager** or **Morphe Desktop**.
2. Navigate to **Settings → Sources → Add Source**.
3. Enter:
   - **Source Type:** `GitHub`
   - **Repository:** `mkr-infinity/mkr-morphe-patches`
4. Tap **Save** / **Confirm**. Morphe will fetch your released `.mpp` patch bundles and display all compatible patches.

---

## 🛠️ Remote APK Builds & Automated Delivery

Patched APKs are compiled **exclusively on GitHub-hosted runners** with output verification, signature generation, and consolidated release publishing.

### ⏱️ 1. Automatic Scheduled Builds
- **Frequency**: Every day at `06:00 UTC` (`0 6 * * *`).
- **Incremental Detection**: The workflow queries the latest GitHub Release (`patched-apks`) for `manifest.json`. It compares the recorded app versions and patch bundle revision against current versions.
- **Efficient & Safe**: If nothing has changed, the run finishes in seconds (`SKIPPED_NO_CHANGE`) without compiling APKs or publishing empty releases. When an app or patch bundle updates, only affected applications are built in parallel matrix jobs.

### 🚀 2. On-Demand Manual Builds
To trigger a build manually with custom parameters:
1. Navigate to your repository on GitHub: `https://github.com/mkr-infinity/mkr-morphe-patches`
2. Click the **Actions** tab at the top.
3. Select **Build Patched APKs** from the left-hand workflow list.
4. Click the **Run workflow** dropdown button on the right.
5. Select options:
   - **`force_full_rebuild`**: Force rebuild all selected apps regardless of manifest state (bypasses incremental skip).
   - **`⚡ Select all eligible applications`**: Check this box to build every supported application in one run.
   - **Individual Checkboxes**: Target specific apps (e.g. `youtube`, `telegram`, `reddit`, etc.).
   - **`Enable side-by-side clone`**: (Default: `true`) Modifies the application package name so the patched app can coexist alongside untouched apps.
   - **`Optional custom package name`**: Enter a custom package name suffix (defaults to `.morphe`).
   - **`Experimental mode`**: Force apply patches to unverified or bleeding-edge APK versions (`--force`).
   - **`App version`**: Set to `latest_compatible` or enter an explicit version string.
   - **`Optional direct download URL`**: Supply an HTTPS URL to a base APK file.

### 📦 3. Base APK Input Sourcing Strategy
Because proprietary apps cannot be permanently redistributed or stored in Git, base APKs are resolved through:
- **Direct Automatic Downloads**:
  - **Telegram (`telegram.org/android`)**: Downloaded automatically during workflow execution with zero manual steps.
- **Workflow Artifact Upload**:
  - Upload an untouched base APK as a GitHub Actions workflow artifact named `apk-<app_id>` (e.g. `apk-youtube`, `apk-reddit`, `apk-tiktok`) in your repository. The workflow detects and uses it automatically.
- **Direct HTTPS URL Input**:
  - When starting a manual run, specify an HTTPS URL in the `Optional direct download URL` input.

### 📥 4. Downloading Patched Releases & Diagnostics
Once the build completes:
1. **GitHub Releases (`patched-apks`)**:
   - Go to **Releases → Latest Patched APKs**: `https://github.com/mkr-infinity/mkr-morphe-patches/releases/tag/patched-apks`
   - Download signed, installable APKs (e.g., `Telegram-v11.8.2-morphe-patched.apk`, `YouTube-v21.20.405-morphe-patched.apk`).
   - Review the release notes table detailing build status, SHA-256 hashes, and patch revisions.
   - `manifest.json` is attached to the release to track state across future scheduled runs.
2. **GitHub Actions Run Artifacts**:
   - Scroll to the bottom of the completed workflow run to download `mkr-morphe-patched-apks` (raw APK bundle) or `mkr-morphe-build-diagnostics` (per-app build manifests, patch options, and patching logs).

---

## 👥 Cloned App / Side-by-Side Coexistence

The repository supports installing modified apps side-by-side with original applications:

### How It Works
- Android enforces that two apps cannot share the same `applicationId` / package name unless one overwrites the other.
- The `Clone app` patch transforms the `AndroidManifest.xml` package name (e.g. `com.reddit.frontpage` ➔ `com.reddit.frontpage.morphe`), updates custom permissions, and rewrites provider authorities.
- For YouTube and YouTube Music, **GmsCore support** is automatically applied, enabling independent non-root login via MicroG without conflicting with Google Play Services.

### Limitations & Caveats
- **Launchers (`Smart Launcher`)**: Modifying launcher package names disrupts `android.intent.category.HOME` registration and widget host authorities. Installing Smart Launcher as a clone is disabled by default.
- **Social Apps (`Facebook`, `Instagram`)**: Internal Facebook SDK native code contains hard-coded provider names and signature cross-checks. Side-by-side clones may experience video story audio-only issues or launch crashes.
- **Updates**: A cloned app **does not** automatically receive updates from the Play Store or when patch source repositories are updated. To update a clone, trigger a new manual build and install the new APK over the existing clone.

---

## ➕ How to Add Future Applications

To add a new application target without rewriting workflows:

1. **Register in `config/apps.json`**:
   Add your app definition with `id`, `display_name`, `package_id`, `compatible_versions`, and `apk_input_policy`.
2. **Add Workflow Checkbox in `.github/workflows/build-patched-apk.yml`**:
   Add the static boolean input under `workflow_dispatch.inputs` and map it in the selector step.
3. **Add Custom Patches in `patches/src/main/kotlin/app/mkr/patches/`**:
   If upstream Morphe does not yet support the app, add a Kotlin patch definition using `resourcePatch` or `bytecodePatch`.
4. **Validate**:
   Run the validator script before committing:
   ```bash
   python3 scripts/validate_catalog.py
   python3 tests/test_pipeline_logic.py
   ```

---

## 🔒 GitHub Actions Secrets & Permissions Setup

Ensure the following settings are enabled in your repository:

1. Go to **Settings → Actions → General**.
2. Under **Workflow permissions**:
   - Select **Read and write permissions**.
   - Check **Allow GitHub Actions to create and approve pull requests**.
3. Under **Actions permissions**:
   - Select **Allow all actions and reusable workflows**.

---

## 🩹 Patches List

<!-- PATCHES_START EXPANDED -->

#### MKR Morphe Patches Catalog

| 💊&nbsp;Patch | 📜&nbsp;Description | ⚙️&nbsp;Options |
|---|---|---|
| [Smart Launcher Customizations](#smart-launcher-customizations) | Provides launcher layout tweaks and UI theme overrides for Smart Launcher. | • Theme Overrides |
| [MovieBox Streaming Optimization](#moviebox-streaming-optimization) | Optimizes player buffer settings and removes non-critical in-app banner promos. | • Buffer Size |
| [Telegram Sponsored Filter](#telegram-sponsored-filter) | Suppresses official sponsored channel posts and promotional banners in chat channels. | • Filter Channels |
| [Clone App](#clone-app) | Changes the app package name to allow installing the same app multiple times alongside the original. | • Package name<br>• Update permissions<br>• Update providers |
| [GmsCore Support](#gmscore-support) | Allows YouTube and YouTube Music to work without root by using GmsCore. | • Redirect Auth |

<!-- PATCHES_END -->

---

## ⚖️ License & Attribution

- **Patch Source Code**: Licensed under the [GNU General Public License v3.0](LICENSE).
- **Attribution (GPLv3 §7b)**: Upstream Morphe patcher and template code copyright (c) MorpheApp contributors.
- **Branding (GPLv3 §7c)**: This repository uses its own distinct identity (`mkr-morphe-patches`). The "Morphe" name is used solely for compatibility identification.
- **Maintainer**: Copyright (c) 2026 [@mkr-infinity](https://github.com/mkr-infinity).
