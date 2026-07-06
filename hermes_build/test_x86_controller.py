#!/usr/bin/env python3
"""x86_controller 的轻量回归检查。"""

from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hermes_build import x86_controller


class RunRepairCommandTest(unittest.TestCase):
    def test_always_uses_hermes_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "prompt.md"
            repair_log = tmp_path / "repair.log"
            prompt_path.write_text("fix it", encoding="utf-8")
            args = argparse.Namespace(
                host="remote",
                remote_home_data_dir="/data",
                repair_timeout=30,
                repair_command="sh -c 'exit 7'",
                session_cleanup_command="sh -c 'exit 8'",
            )

            def fake_api(_args: argparse.Namespace, _prompt: Path, log_path: Path) -> int:
                log_path.write_text(log_path.read_text(encoding="utf-8") + "api output\n", encoding="utf-8")
                return 0

            with mock.patch.dict(
                os.environ,
                {
                    "HERMES_REPAIR_COMMAND": "sh -c 'exit 7'",
                    "HERMES_SESSION_CLEANUP_COMMAND": "sh -c 'exit 8'",
                },
            ), mock.patch.object(x86_controller, "run_hermes_api_command", side_effect=fake_api) as api:
                exit_code = x86_controller.run_repair_command(args, prompt_path, repair_log)

            api.assert_called_once_with(args, prompt_path, repair_log)
            log_text = repair_log.read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertIn("# command: hermes-api", log_text)
            self.assertIn("api output", log_text)
            self.assertNotIn("cleanup_command", log_text)


class WriteExperienceTest(unittest.TestCase):
    def test_writes_real_experience_from_hermes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            local_log = tmp_path / "build.log"
            repair_log = tmp_path / "repair.log"
            experience_path = tmp_path / "experience" / "pkg.md"
            prompt_path = tmp_path / "experience_prompt.md"
            draft_path = tmp_path / "experience_draft.md"
            local_log.write_text("build failed", encoding="utf-8")
            repair_log.write_text("repair fixed it", encoding="utf-8")
            args = argparse.Namespace(repair_timeout=30)
            request = {
                "package": "pkg",
                "python_version": "3.12",
                "arch": "riscv64",
                "repo_root": "/repo",
                "log_path": "/remote/build.log",
            }

            def fake_api(_args: argparse.Namespace, prompt: Path, _log: Path, *, output_path: Path | None = None) -> int:
                self.assertIn("experience/pkg.md", prompt.read_text(encoding="utf-8"))
                self.assertIsNotNone(output_path)
                output_path.write_text("# pkg RISC-V wheel 修复记录\n\n真实修复经验\n", encoding="utf-8")
                return 0

            with mock.patch.object(x86_controller, "run_hermes_api_command", side_effect=fake_api) as api:
                ok = x86_controller.write_experience_from_hermes(
                    args,
                    request,
                    "fixed",
                    local_log,
                    repair_log,
                    experience_path,
                    prompt_path,
                    draft_path,
                )

            self.assertTrue(ok)
            api.assert_called_once_with(args, prompt_path, repair_log, output_path=draft_path)
            experience_text = experience_path.read_text(encoding="utf-8")
            self.assertIn("真实修复经验", experience_text)
            self.assertNotIn("请根据", experience_text)


if __name__ == "__main__":
    unittest.main()
