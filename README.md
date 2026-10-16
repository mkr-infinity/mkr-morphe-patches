<!-- Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches) -->
<div align="center">

# ⚡ MKR Morphe Patches ⚡

**Personal Morphe-compatible Android patches with automatic patch updates and on-demand APK builds.**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL_v3.0-d97706.svg?style=flat-square)](LICENSE)
[![Morphe Compatible](https://img.shields.io/badge/Morphe-Compatible-f59e0b.svg?style=flat-square&logo=android)](https://github.com/MorpheApp)
[![Maintainer](https://img.shields.io/badge/Maintainer-mkr--infinity-b45309.svg?style=flat-square&logo=github)](https://github.com/mkr-infinity)
[![APK Builds](https://img.shields.io/badge/APK_Builds-Manual_Only-1e1e1e.svg?style=flat-square)](.github/workflows/build-patched-apk.yml)
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

`mkr-morphe-patches` maintains a clean separation between **upstream patch intelligence**, **custom patch implementations**, and **remotely triggered APK artifact compilation**:

1. **Automatic Upstream Monitoring (`update-upstream.yml`)**:
   - Monitored daily via scheduled GitHub Actions.
   - Compares releases from official upstream Morphe repositories (`MorpheApp/morphe-patches`, `MorpheApp/morphe-desktop`).
   - Opens a clean, reviewable pull request when new upstream releases or version targets are detected.
   - **Never builds or publishes APKs automatically.**
2. **On-Demand Manual APK Building (`build-patched-apk.yml`)**:
   - Strictly triggered manually via `workflow_dispatch`.
   - Interactive checkbox selection for every app target, plus a `Select all apps` master switch.
   - Downloads/validates input APKs, applies official & custom patches, handles side-by-side app cloning, and uploads standalone signed APK artifacts.
3. **Official Morphe Patch Bundle Releasing (`release.yml`)**:
   - Preserves official semantic-release infrastructure (`.releaserc`).
   - Automatically builds `.mpp` patch bundles and generates patch catalogs on conventional commits to `main` and `dev`.

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

## 🛠️ Triggering On-Demand Remote APK Builds

Patched APKs are built **exclusively on GitHub-hosted runners** via manual trigger:

### Step 1: Open the Workflow
1. Navigate to your repository on GitHub: `https://github.com/mkr-infinity/mkr-morphe-patches`
2. Click the **Actions** tab at the top.
3. Select **Build Patched APKs** from the left-hand workflow list.
4. Click the **Run workflow** dropdown button on the right.

### Step 2: Configure Inputs
- **`⚡ Select all eligible applications`**: Check this box to build every supported application in one run.
- **Individual Checkboxes**: Alternatively, check specific apps (e.g. `youtube`, `telegram`, `reddit`).
- **`Enable side-by-side clone`**: (Default: `true`) Modifies the application package name so the patched app can be installed alongside your existing untouched application.
- **`Optional custom package name`**: Enter a custom package name if you prefer a specific suffix (leave blank for standard `.morphe`).
- **`Experimental mode`**: Check if you wish to apply patches to an unverified or bleeding-edge APK version (`--force`).
- **`App version`**: Set to `latest_compatible` or enter an explicit version string.
- **`Optional direct download URL`**: Supply an HTTPS URL to a trusted APK file if you are not using workflow artifact upload.

### Step 3: Provide Input APKs
Because YouTube, YouTube Music, and other proprietary targets do not distribute static public APK binaries, provide the base APK using either:
1. **GitHub Artifact Upload**: Upload an artifact named `apk-<app_id>` (e.g. `apk-youtube`) to your repository.
2. **Direct URL**: Specify a verifiable HTTPS direct link in the workflow input.
3. **Official Direct Targets**: Apps like **Telegram** automatically download directly from their official site (`telegram.org/android`).

### Step 4: Download Patched Artifacts
Once the workflow run completes:
1. Click into the completed workflow run.
2. Scroll to the **Artifacts** section at the bottom.
3. Download:
   - **`mkr-morphe-patched-apks`**: Contains your signed, installable patched `.apk` files.
   - **`mkr-morphe-build-diagnostics`**: Contains `build-manifest.json` with input/output checksums, applied patch lists, and detailed execution logs.

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
