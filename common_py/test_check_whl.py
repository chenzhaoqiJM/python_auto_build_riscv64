import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


COMMON_PY_DIR = Path(__file__).resolve().parent


def import_check_whl_with_home(home_dir):
    sys.path.insert(0, str(COMMON_PY_DIR))
    sys.modules.pop("check_whl", None)
    with patch.dict(os.environ, {"HOME": str(home_dir)}):
        return importlib.import_module("check_whl")


class CheckWhlConfigTests(unittest.TestCase):
    def _mock_gitlab_files(self, module, filenames, build_for_version):
        package_response = Mock(status_code=200)
        package_response.json.return_value = [
            {"id": 7, "name": "bcrypt", "version": "5.0.0"}
        ]
        package_response.headers = {}
        files_response = Mock(status_code=200)
        files_response.json.return_value = [
            {"file_name": filename} for filename in filenames
        ]
        empty_page_response = Mock(status_code=200)
        empty_page_response.json.return_value = []
        empty_page_response.headers = {}

        with (
            patch.object(module, "load_gitlab_config", return_value=("https://git.example/api/v4/projects/33/packages/pypi", "token")),
            patch.object(
                module.requests,
                "get",
                side_effect=[package_response, files_response, empty_page_response],
            ),
        ):
            return module.has_whl_in_gitlab(
                "bcrypt", version="5.0.0", build_for_version=build_for_version
            )

    def test_wheel_matches_requested_platform(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        self.assertTrue(module.wheel_matches_platform(
            "demo-1.0-cp312-cp312-manylinux_2_39_riscv64.whl",
            "manylinux_2_39_riscv64",
        ))
        self.assertFalse(module.wheel_matches_platform(
            "demo-1.0-cp312-cp312-manylinux_2_36_riscv64.whl",
            "manylinux_2_39_riscv64",
        ))
        self.assertTrue(module.wheel_matches_platform(
            "demo-1.0-py3-none-any.whl", "manylinux_2_39_riscv64"
        ))

    def test_import_does_not_require_gitlab_config(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        self.assertEqual(module.get_current_python_tag(), f"cp{sys.version_info.major}{sys.version_info.minor}")

    def test_distinguishes_python_314_regular_and_free_threaded_wheels(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        regular = "bcrypt-5.0.0-cp314-cp314-manylinux_2_41_riscv64.whl"
        free_threaded = (
            "bcrypt-5.0.0-cp314-cp314t-"
            "manylinux_2_34_riscv64.manylinux_2_41_riscv64.whl"
        )
        pure_python = "demo-1.0-py3-none-any.whl"

        self.assertTrue(module.wheel_matches_python(regular, "3.14"))
        self.assertFalse(module.wheel_matches_python(free_threaded, "3.14"))
        self.assertFalse(module.wheel_matches_python(regular, "3.14t"))
        self.assertTrue(module.wheel_matches_python(free_threaded, "3.14t"))
        self.assertTrue(module.wheel_matches_python(pure_python, "3.14"))
        self.assertTrue(module.wheel_matches_python(pure_python, "3.14t"))

    def test_free_threaded_target_does_not_accept_abi3_wheel(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        abi3 = "demo-1.0-cp39-abi3-manylinux_2_41_riscv64.whl"
        self.assertTrue(module.wheel_matches_python(abi3, "3.14"))
        self.assertFalse(module.wheel_matches_python(abi3, "3.14t"))

    def test_gitlab_lookup_uses_requested_314_abi(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        free_threaded = (
            "bcrypt-5.0.0-cp314-cp314t-"
            "manylinux_2_34_riscv64.manylinux_2_41_riscv64.whl"
        )
        self.assertEqual(
            self._mock_gitlab_files(module, [free_threaded], "3.14"),
            (False, []),
        )
        self.assertEqual(
            self._mock_gitlab_files(module, [free_threaded], "3.14t"),
            (True, [free_threaded]),
        )

    def test_has_whl_in_gitlab_reads_home_pypirc(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            home_dir = Path(tmp_home)
            (home_dir / ".pypirc").write_text(
                "[gitlab]\n"
                "repository = https://git.example/api/v4/projects/33/packages/pypi\n"
                "password = test-token\n"
            )
            module = import_check_whl_with_home(home_dir)

            package_response = Mock(status_code=200)
            package_response.json.return_value = [{"id": 7, "name": "demo", "version": "1.0"}]
            package_response.headers = {}
            files_response = Mock(status_code=200)
            files_response.json.return_value = [
                {"file_name": f"demo-1.0-{module.get_current_python_tag()}-none-linux_riscv64.whl"}
            ]
            files_response.headers = {}

            with (
                patch.object(module, "pypirc_path", str(home_dir / "missing-project-pypirc")),
                patch.object(module.requests, "get", side_effect=[package_response, files_response]) as request_get,
            ):
                found, filenames = module.has_whl_in_gitlab("demo", version="1.0")

        self.assertTrue(found)
        self.assertEqual(len(filenames), 1)
        first_url = request_get.call_args_list[0].args[0]
        first_headers = request_get.call_args_list[0].kwargs["headers"]
        self.assertEqual(first_url, "https://git.example/api/v4/projects/33/packages?per_page=100&page=1")
        self.assertEqual(first_headers, {"PRIVATE-TOKEN": "test-token"})


if __name__ == "__main__":
    unittest.main()
