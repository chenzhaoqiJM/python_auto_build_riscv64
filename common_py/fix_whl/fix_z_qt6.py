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


def postprocess_whl_rpath_qt6(whl_path, skip_tag=["none", "cmake"]):

    if shutil.which("patchelf") is None:
        print("[✗] patchelf not found. Please install it first.")
        return whl_path

    whl_path = Path(whl_path).resolve()
    if not whl_path.exists() or whl_path.suffix != ".whl":
        print(f"[✗] Not a valid .whl file: {whl_path}")
        return whl_path

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        print(f"[+] Unpacking {whl_path.name} ...")

        # 解压
        subprocess.run(["wheel", "unpack", str(whl_path), "-d", str(tmpdir)], check=True)

        unpacked_dir = next(tmpdir.glob("*"))  # wheel unpack 会在 tmpdir 下生成一个目录

        # qt root
        qt6_dir=unpacked_dir/'PyQt6'
        # set qt6 rpath to 
        print(f"$$$$-set dir {str(qt6_dir)} all *.so rpath to $ORIGIN/Qt6/lib")
        patch_rpath_all(root=qt6_dir, new_rpath=r"$ORIGIN/Qt6/lib")


        qt6_lib_dir=qt6_dir/'Qt6'
        # copy qt6
        print(f"$$$$-copy /opt/Qt6.9.2 to dir {str(qt6_lib_dir)}")
        subprocess.run(["cp", "-ra", '/opt/Qt6.9.2', str(qt6_lib_dir)], check=True)
        subprocess.run(["rm", "-rf", str(qt6_lib_dir/'bin')], check=True)
        subprocess.run(["rm", "-rf", str(qt6_lib_dir/'include')], check=True)
        

        # 使用 wheel.pack 重新打包 ----------------------------------
        subprocess.run(["wheel", "pack", str(unpacked_dir), "-d", str(whl_path.parent)], check=True)

        print(f"[✅] Original wheel overwritten: {whl_path}")
        # remove tmp
        subprocess.run(["rm", "-rf", str(tmpdir)], check=True)

        # auditwheel -----------------------------------------------
        WHEELS_REPAIR_DIR = whl_path.parent / 'repair'
        print(f"fix whl to ... {str(WHEELS_REPAIR_DIR)}")

        cmd = [
            "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), 
        ]

        exclude_libs = ['libglib*.so.*', 'libgobject*.so.*', 'libgio*.so.*', 'libX11*.so.*', 'libGLX*.so.*',
                        'libGL*.so.*', 'libGLdispatch*.so.*', 'libxcb*.so.*', 'libXau*.so.*', 'libqwayland*.so.*',
                        'libXdmcp*.so.*', 'libX*.so*', 'libgdk*.so*', 'libgio*.so*', 'libgmodule*.so*', 'libgtk*.so*', 'libwayland*.so.*']
        for lib in exclude_libs:
            cmd += ["--exclude", lib]

        # 获取 repair 目录之前的文件列表
        before_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))

        subprocess.run(cmd, check=True)

        # 获取 repair 目录之后的文件列表
        after_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))
        new_files = list(after_files - before_files)

        repaired_whl = new_files[0]
        print(f"✅ auditwheel repair succeeded: {repaired_whl.name}")

        print("start to fix .libs rpath.............................")
        if new_files:
            
            with tempfile.TemporaryDirectory() as tmpdir_str:
                tmpdir = Path(tmpdir_str)

                print(f"[+] Unpacking {repaired_whl.name} ...")

                # 解压
                subprocess.run(["wheel", "unpack", str(repaired_whl), "-d", str(tmpdir)], check=True)

                unpacked_dir = next(tmpdir.glob("*"))  # wheel unpack 会在 tmpdir 下生成一个目录

                # 查找 .libs 目录
                lib_dirs = list(unpacked_dir.glob("*/.libs")) + list(unpacked_dir.glob("*.libs"))
                if not lib_dirs:
                    print("[✗] No .libs directory found at top level or one level down. Exiting.")
                    return repaired_whl

                for lib_dir in lib_dirs:
                    print(f"[+] Checking .so dependencies in: {lib_dir}")
                    fix_so_rpaths_in_lib_dir(lib_dir)

                # 使用 wheel.pack 重新打包
                subprocess.run(["wheel", "pack", str(unpacked_dir), "-d", str(repaired_whl.parent)], check=True)

                print(f"[✅] Full repair Original wheel overwritten: {repaired_whl}")
                
            return repaired_whl
        else:
            print("No repaired .whl file found")
            return repaired_whl


if __name__ == "__main__":
    # 示例：修改当前目录下所有 .so 文件
    a = process_whl_rpath_qt6('/home/zq/whl_build/tmp/pyqt6-6.16.11-cp39-abi3-manylinux_2_17_x86_64.whl')
    print(str(a))
