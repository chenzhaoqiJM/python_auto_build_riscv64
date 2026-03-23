import subprocess
import pathlib
from typing import Union

import os
import subprocess
import shutil
from pathlib import Path
import hashlib
import base64
import tempfile
from zipfile import ZipInfo
import stat
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(current_dir)
sys.path.insert(0, parent_dir)

from fix_rpath_common import fix_so_rpaths_in_lib_dir, patch_rpath_all

from fix_z_qt5 import postprocess_whl_rpath_qt5
from fix_z_qt6 import postprocess_whl_rpath_qt6
special_fix_func_map = {
    'pyqt5':postprocess_whl_rpath_qt5, 'pyqt6':postprocess_whl_rpath_qt6
}

def process_whl_rpath(whl_path, skip_tag=["none", "cmake"]):

    print("转到可选后处理..........................................")

    whl_path = Path(whl_path).resolve()
    if not whl_path.exists() or whl_path.suffix != ".whl":
        print(f"[✗] Not a valid .whl file: {whl_path}")
        return whl_path

    # 处理特殊后处理包
    pkg_name = (whl_path.name).split('-')[0]
    pkg_name = pkg_name.replace("_", "-")
    if pkg_name in special_fix_func_map:
        print(f"$$$-转到处理特殊流程——for {str(whl_path)}")
        final_path = special_fix_func_map[pkg_name](whl_path, skip_tag=skip_tag)
        return final_path

    # if "none" in whl_path or "cmake" in whl_path:
    if any(keyword in str(whl_path) for keyword in skip_tag):
        print(f"⚠️  Skipping set RPATH for wheel with skip-tag: {whl_path}")
        return whl_path
    
    if shutil.which("patchelf") is None:
        print("[✗] patchelf not found. Please install it first.")
        return whl_path
    
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        print(f"[+] Unpacking {whl_path.name} ...")

        # 解压
        subprocess.run(["wheel", "unpack", str(whl_path), "-d", str(tmpdir)], check=True)

        unpacked_dir = next(tmpdir.glob("*"))  # wheel unpack 会在 tmpdir 下生成一个目录

        # 查找 .libs 目录
        lib_dirs = list(unpacked_dir.glob("*/.libs")) + list(unpacked_dir.glob("*.libs"))
        if not lib_dirs:
            print("[✗] No .libs directory found at top level or one level down. Exiting.")
            return whl_path

        for lib_dir in lib_dirs:
            print(f"[+] Checking .so dependencies in: {lib_dir}")
            fix_so_rpaths_in_lib_dir(lib_dir)

        # 使用 wheel.pack 重新打包
        
        subprocess.run(["wheel", "pack", str(unpacked_dir), "-d", str(whl_path.parent)], check=True)

        print(f"[✅] Original wheel overwritten: {whl_path}")

        return whl_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix rpath inside .whl package for embedded .libs/")
    parser.add_argument("whl", help="Path to .whl file")
    args = parser.parse_args()

    process_whl_rpath(args.whl)
