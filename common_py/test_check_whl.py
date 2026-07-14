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
    def test_import_does_not_require_gitlab_config(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            module = import_check_whl_with_home(tmp_home)

        self.assertEqual(module.get_current_python_tag(), f"cp{sys.version_info.major}{sys.version_info.minor}")

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

            with patch.object(module.requests, "get", side_effect=[package_response, files_response]) as request_get:
                found, filenames = module.has_whl_in_gitlab("demo", version="1.0")

        self.assertTrue(found)
        self.assertEqual(len(filenames), 1)
        first_url = request_get.call_args_list[0].args[0]
        first_headers = request_get.call_args_list[0].kwargs["headers"]
        self.assertEqual(first_url, "https://git.example/api/v4/projects/33/packages?per_page=100&page=1")
        self.assertEqual(first_headers, {"PRIVATE-TOKEN": "test-token"})


if __name__ == "__main__":
    unittest.main()
