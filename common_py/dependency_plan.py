#!/usr/bin/env python3
"""Resolve build order and probe official PyPI for compatible wheels."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


OFFICIAL_PYPI_INDEX = "https://pypi.org/simple"


def _requirement_name(package_spec: str) -> str:
    try:
        return canonicalize_name(Requirement(package_spec).name)
    except Exception:
        return canonicalize_name(package_spec.split("==", 1)[0].strip())


def dependency_order(report: dict, requested_spec: str) -> list[str]:
    """Return the resolved packages in dependency-first order."""
    packages = {}
    for item in report.get("install", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name")
        version = metadata.get("version")
        if not name or not version:
            continue
        packages[canonicalize_name(name)] = {
            "name": name,
            "version": version,
            "requires_dist": metadata.get("requires_dist") or [],
            "requested": bool(item.get("requested")),
        }

    dependencies = {}
    for key, package in packages.items():
        package_dependencies = set()
        for requirement_text in package["requires_dist"]:
            try:
                dependency = canonicalize_name(Requirement(requirement_text).name)
            except Exception:
                continue
            # The pip report already contains only selected distributions. An
            # edge is relevant only when its target is part of this resolution.
            if dependency in packages and dependency != key:
                package_dependencies.add(dependency)
        dependencies[key] = sorted(package_dependencies)

    requested_name = _requirement_name(requested_spec)
    roots = []
    if requested_name in packages:
        roots.append(requested_name)
    roots.extend(
        key
        for key, package in packages.items()
        if package["requested"] and key not in roots
    )
    roots.extend(key for key in packages if key not in roots)

    ordered = []
    state = {}

    def visit(key: str) -> None:
        if state.get(key) == "done":
            return
        if state.get(key) == "visiting":
            # Dependency metadata can contain benign cycles. Pip has already
            # resolved them, so keep the first traversal order.
            return
        state[key] = "visiting"
        for dependency in dependencies.get(key, []):
            visit(dependency)
        state[key] = "done"
        ordered.append(
            f"{canonicalize_name(packages[key]['name'])}=={packages[key]['version']}"
        )

    for root in roots:
        visit(root)
    return ordered


def resolve(package_spec: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="hp-dependency-report-") as tmpdir:
        report_path = Path(tmpdir) / "report.json"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--report",
            str(report_path),
            "--disable-pip-version-check",
            "--no-input",
            package_spec,
        ]
        result = subprocess.run(command, text=True, stdout=sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"pip failed to resolve {package_spec}")
        with report_path.open(encoding="utf-8") as report_file:
            report = json.load(report_file)
    return dependency_order(report, package_spec)


def official_wheel_available(package_spec: str, attempts: int = 3) -> bool:
    """Ask the target interpreter whether official PyPI has a usable wheel."""
    env = os.environ.copy()
    env.pop("PIP_INDEX_URL", None)
    env.pop("PIP_EXTRA_INDEX_URL", None)
    env.pop("PIP_NO_INDEX", None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INPUT"] = "1"

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--isolated",
        "--index-url",
        OFFICIAL_PYPI_INDEX,
        "--only-binary=:all:",
        "--no-deps",
        "--dry-run",
        "--ignore-installed",
        "--disable-pip-version-check",
        "--no-input",
        package_spec,
    ]
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                command,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            last_error = "pip compatibility check timed out"
            if attempt < attempts:
                time.sleep(attempt)
            continue

        if result.returncode == 0:
            print(
                f"Official PyPI has a compatible wheel for {package_spec}",
                file=sys.stderr,
            )
            return True

        last_error = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        no_distribution = (
            "No matching distribution found" in result.stdout
            or "Could not find a version that satisfies" in result.stdout
        )
        if no_distribution:
            break
        if attempt < attempts:
            time.sleep(attempt)

    print(
        f"Official PyPI has no compatible wheel for {package_spec}"
        + (f": {last_error}" if last_error else ""),
        file=sys.stderr,
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("package")

    wheel_parser = subparsers.add_parser("official-wheel")
    wheel_parser.add_argument("package")

    args = parser.parse_args()
    if args.command == "resolve":
        try:
            for package in resolve(args.package):
                print(package)
        except Exception as error:
            print(f"Failed to resolve {args.package}: {error}", file=sys.stderr)
            return 1
        return 0

    return 0 if official_wheel_available(args.package) else 1


if __name__ == "__main__":
    sys.exit(main())
