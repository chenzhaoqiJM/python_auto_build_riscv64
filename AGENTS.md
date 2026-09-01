---
description: "Use when editing python_auto_build scripts, Python build helpers, shell automation, dynamic_env modules, special_care builders, wheel repair or upload logic. Covers concise project coding conventions for RISC-V Python wheel automation."
name: "python_auto_build Project Coding Guidelines"
applyTo: ["**/*.py", "**/*.sh", "**/*.md"]
---

# python_auto_build Project Coding Guidelines

This project automates building, repairing, testing, and uploading Python wheel packages in a Bianbu Linux / riscv64 environment. When making changes, prioritize keeping scripts simple, directly executable in the target environment, and easy to troubleshoot.

## General Principles

- Prefer minimal changes and avoid introducing unnecessary frameworks, abstraction layers, or new dependencies.
- Preserve existing directory responsibilities: place common logic in `common_py/`, package-specific builds in `special_care/`, dynamic environments in `dynamic_env/`, and automated build scripts for packages requiring special handling under `build_*`.
- When modifying the build process, always account for `BUILD_FOR_VERSION` and support the existing version convention from `3.9` through `3.14t`.
- Do not hard-code personal local paths. When caches or temporary directories are necessary, follow existing patterns such as `$HOME/.cache*`, `$HOME/.mytmp*`, and `$HOME/pyenvs*`.
- For high-risk operations such as uploading, deleting, or overwriting packages, retain clear logs and avoid silent failures.

## Shell Script Conventions

- For new Bash scripts, prefer `#!/bin/bash` and `set -e`; use `#!/usr/bin/env sh` only when POSIX sh is required.
- Calculate paths relative to the script directory: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`. Avoid relying on the current working directory.
- Reuse `common_func.sh`, `env_common.sh`, and `dynamic_env/env_loader.sh`; do not duplicate existing functions.
- Double-quote variable expansions by default. Treat package names, paths, and version numbers as potentially containing special characters.
- Always use dynamic environments with matching `load_env` / `unload_env` calls to avoid contaminating subsequent package builds.

## Python Code Conventions

- Prefer the Python standard library. Add a third-party dependency only when the project already depends on it or it is genuinely necessary.
- Implement common capabilities as small functions. Put package-specific logic in `special_care/build_<pkg>.py` and register it with a decorator from `registry.py`.
- Unreliable operations such as network downloads, GitLab queries, and uploads should include retries or explicit error output.
- When parsing package names, support both `name` and `name==version` forms to avoid breaking version build scripts.
- Keep logs readable. Follow the project's style of explanatory messages and emoji status indicators; error messages must include the package name or a relevant path.

## Wheel and Build Compatibility

- When modifying wheel repair logic, preserve compatibility with manylinux tags, rpath handling, `.libs` processing, abi3, and free-threading.
- For environments involving glibc, RISC-V, RVV, Qt, OpenCV, Arrow, FFmpeg, MuJoCo, CycloneDDS, Faiss, and similar components, prefer incremental configuration through `dynamic_env/`.
- Before adding a special package build, check whether a wheel already exists, whether a source patch is required, and whether additional system libraries are needed.

## Verification Guidelines

- After modifying a Python file, run at least a syntax check or a lightweight entry-point check for the target script.
- After modifying a shell script, run at least `bash -n` to check its syntax. Perform an actual build verification only when the target environment is available.
- Do not claim that a build succeeded unless it has been confirmed in the target riscv64/Bianbu environment.

## Ongoing Maintenance

- Add new guidelines to the relevant section and keep each item concise.
- If a rule applies to only one package, document it in a comment near the corresponding `special_care/build_<pkg>.py` file or in a README instead of adding it to this file.
