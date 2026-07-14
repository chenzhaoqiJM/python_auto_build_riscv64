#!/usr/bin/env python3
"""x86_controller prompt generation regression checks."""

from __future__ import annotations

import unittest
from pathlib import Path

from hermes_build import x86_controller


class MakePromptTest(unittest.TestCase):
    def test_prompt_tells_hermes_exact_ssh_target_and_requested_python_version(self) -> None:
        request = {
            "package": "awswrangler==3.17.0",
            "python_version": "3.14",
            "arch": "riscv64",
            "repo_root": "/home/zqmuse3/python_auto_build_riscv64",
            "build_script": "build_most_common/build_one.sh",
            "src_build_script": "build_most_common/build_from_src.sh",
            "log_path": "/home/zqmuse3/.python_auto_build_hermes/logs/awswrangler/attempt-1-build.log",
        }

        prompt = x86_controller.make_prompt(
            request,
            Path("/tmp/awswrangler/build.log"),
            Path("/tmp/experience"),
            ssh_host="zqmuse3@10.0.90.182",
        )

        self.assertIn("- remote_ssh_host: zqmuse3@10.0.90.182", prompt)
        self.assertIn("ssh zqmuse3@10.0.90.182", prompt)
        self.assertIn("不要只使用裸 IP", prompt)
        self.assertIn("export BUILD_FOR_VERSION=3.14", prompt)
        self.assertNotIn("BUILD_FOR_VERSION`为 3.12", prompt)
        self.assertNotIn("export BUILD_FOR_VERSION=3.12", prompt)


if __name__ == "__main__":
    unittest.main()
