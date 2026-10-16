<!-- Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches) -->
# Contributing to MKR Morphe Patches

Thank you for contributing to **mkr-morphe-patches**! This repository provides Morphe-compatible patch bundles, automated upstream synchronization, and on-demand remote APK builds.

---

## 🛠️ Repository Architecture & Guidelines

1. **Separation of Concerns**:
   - Upstream patch tracking is isolated in `config/upstream.json`.
   - The central application catalog is maintained in `config/apps.json`.
   - Custom patch source code lives in `patches/src/main/kotlin/app/mkr/patches/`.
   - Automated builds occur remote-only on GitHub Actions; no APK compilation or binary patching is executed locally.

2. **Branching Model & Releases**:
   - `main`: Primary repository branch. All commits, pull requests, and automated upstream PRs target `main`.
   - Patched APK releases are built and published on-demand using the [`build-patched-apk.yml`](.github/workflows/build-patched-apk.yml) workflow with concise changelogs and direct APK downloads.
   - Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification (`feat:`, `fix:`, `perf:`, `chore:`, `bump:`).

3. **Three-Document Policy**:
   - Project-owned Markdown documentation is strictly limited to three files: `README.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`.
   - Do not create additional `.md` files; integrate configuration details, tables, or guides directly into `README.md` or as inline documentation.

---

## 📱 How to Add a New Application

Adding a new application target requires updating configuration and workflow inputs:

### Step 1: Add App to Central Registry (`config/apps.json`)
Add a new JSON entry to the `apps` array with:
```json
{
  "id": "app_id",
  "display_name": "App Display Name",
  "package_id": "com.example.app",
  "upstream_source": "custom",
  "source_type": "custom",
  "source_revision": "main",
  "compatible_versions": ["1.0.0"],
  "tested_versions": ["1.0.0"],
  "apk_input_policy": "manual_artifact_or_url",
  "has_custom_patches": true,
  "apk_build_supported": true,
  "side_by_side_supported": true,
  "clone_mechanism": "morphe_clone_app",
  "signing_requirement": "v2_v3_ephemeral_or_custom_keystore",
  "requires_microg": false,
  "enabled": true,
  "status": "supported",
  "description": "App description and patch details."
}
```

### Step 2: Add Boolean Input to Build Workflow (`.github/workflows/build-patched-apk.yml`)
Add the static boolean input under `on.workflow_dispatch.inputs`:
```yaml
      app_id:
        description: "Build App Display Name"
        type: boolean
        default: false
```
And add the mapping in the `Resolve Selected Applications` script step:
```python
      'app_id': '${{ inputs.app_id }}' == 'true',
```

### Step 3: Implement Custom Patches (If Applicable)
If the application requires custom bytecode or resource patches not present in upstream Morphe:
- Add a new compatibility definition in `patches/src/main/kotlin/app/mkr/patches/shared/Constants.kt`.
- Define the patch using `bytecodePatch` or `resourcePatch` in `patches/src/main/kotlin/app/mkr/patches/custom/`.

### Step 4: Validate
Run local validation to ensure complete schema compliance and parity:
```bash
python3 scripts/validate_catalog.py
python3 tests/test_pipeline_logic.py
```

---

## 🔒 Security & Quality Standards

- **No Secrets or Signing Keys**: Never commit `.keystore`, `.jks`, `.p12`, passwords, or personal access tokens.
- **No APK Binaries in Git**: Never commit `.apk`, `.apkm`, `.xapk`, or `.mpp` files.
- **Truthful Compatibility**: Never mark an application or version as `supported` without verified test evidence. Use `experimental` or document limitations when testing is ongoing.
- **Side-by-Side Coexistence**: Verify provider authorities, permissions, and launcher intent compatibility before enabling side-by-side cloning.

---
*Maintained by [@mkr-infinity](https://github.com/mkr-infinity)*
