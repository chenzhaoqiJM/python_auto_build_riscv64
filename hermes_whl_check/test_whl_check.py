#!/usr/bin/env python3
"""hermes_whl_check regression checks."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from hermes_whl_check import remote_worker, x86_controller


class WheelCompatibilityTest(unittest.TestCase):
    def test_wheel_matches_exact_cp_version_and_riscv_platform(self) -> None:
        filename = "demo_pkg-1.0.0-cp312-cp312-manylinux_2_39_riscv64.whl"

        self.assertTrue(remote_worker.wheel_matches_python_version(filename, "3.12"))
        self.assertFalse(remote_worker.wheel_matches_python_version(filename, "3.13"))

    def test_wheel_matches_universal_py3_none_any_for_all_checked_versions(self) -> None:
        filename = "demo_pkg-1.0.0-py3-none-any.whl"

        for python_version in ("3.12", "3.13", "3.14"):
            with self.subTest(python_version=python_version):
                self.assertTrue(remote_worker.wheel_matches_python_version(filename, python_version))


class RemoteWorkerRequestTest(unittest.TestCase):
    def test_make_test_request_contains_venv_python_and_install_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            base_dir = Path(tmpdir) / "home"
            venv_dir = base_dir / "venvs" / "demo_pkg-py312"
            log_path = base_dir / "logs" / "demo_pkg" / "3.12" / "install.log"

            request = remote_worker.make_test_request(
                repo_root=repo_root,
                base_dir=base_dir,
                package="demo-pkg",
                python_version="3.12",
                venv_dir=venv_dir,
                install_log=log_path,
                index_url="https://example.invalid/simple",
            )

        self.assertEqual(request["package"], "demo-pkg")
        self.assertEqual(request["python_version"], "3.12")
        self.assertEqual(request["venv_dir"], str(venv_dir))
        self.assertEqual(request["venv_python"], str(venv_dir / "bin" / "python"))
        self.assertEqual(request["install_log"], str(log_path))
        self.assertEqual(request["state"], "pending")


class ControllerPromptTest(unittest.TestCase):
    def test_prompt_tells_hermes_to_use_exact_remote_venv(self) -> None:
        request = {
            "package": "demo-pkg",
            "python_version": "3.13",
            "repo_root": "/home/bianbu/python_auto_build_riscv64",
            "venv_dir": "/home/bianbu/.python_auto_build_hermes_whl_check/venvs/demo_pkg-py313",
            "venv_python": "/home/bianbu/.python_auto_build_hermes_whl_check/venvs/demo_pkg-py313/bin/python",
            "install_log": "/home/bianbu/.python_auto_build_hermes_whl_check/logs/demo_pkg/3.13/install.log",
        }

        prompt = x86_controller.make_prompt(
            request,
            local_install_log=Path("/tmp/demo/install.log"),
            ssh_host="bianbu@10.0.90.13",
        )

        self.assertIn("demo-pkg", prompt)
        self.assertIn("3.13", prompt)
        self.assertIn("ssh bianbu@10.0.90.13", prompt)
        self.assertIn("/home/bianbu/.python_auto_build_hermes_whl_check/venvs/demo_pkg-py313/bin/python", prompt)
        self.assertIn("只输出 JSON", prompt)


class HermesResultParsingTest(unittest.TestCase):
    def test_parse_hermes_result_reads_json_from_markdown_block(self) -> None:
        output = """测试已执行。

```json
{"status": "failed", "summary": "import demo_pkg failed", "details": "No module named demo_pkg"}
```
"""

        result = x86_controller.parse_hermes_result(output)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"], "import demo_pkg failed")

    def test_append_failure_summary_writes_package_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(home_dir=Path(tmpdir))
            request = {"package": "demo-pkg", "python_version": "3.14"}
            result = {"status": "failed", "summary": "basic API check failed"}

            x86_controller.append_failure_summary(args, request, result, Path("/tmp/demo-test.log"))

            log_path = Path(tmpdir) / "logs" / "failed_whl_checks.log"
            data = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(data["package"], "demo-pkg")
        self.assertEqual(data["python_version"], "3.14")
        self.assertEqual(data["summary"], "basic API check failed")


if __name__ == "__main__":
    unittest.main()
