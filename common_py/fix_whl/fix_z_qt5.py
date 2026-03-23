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

def make_insert_code(qpa_platform: str) -> str:
    return f"""# ==== Custom insert start ====
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
current_dir = os.path.abspath(current_dir)

_lib_dir = os.path.join(current_dir, "Qt5/lib/")

os.environ["LD_LIBRARY_PATH"] = f"{{_lib_dir}}:" + os.environ.get("LD_LIBRARY_PATH", "")
#print(os.environ.get("LD_LIBRARY_PATH", ""))

if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"

os.environ["QT_QPA_PLATFORM"] = "{qpa_platform}"
# ==== Custom insert end ====
"""

def insert_code_into_file(file_path: Path, qpa_platform: str):
    text = file_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # 找到版权声明后的插入位置（第一个非注释行之前）
    insert_idx = 0
    for i, line in enumerate(text):
        if not line.strip().startswith("#") and line.strip():
            insert_idx = i
            break
    else:
        insert_idx = len(text)

    # 如果已经插入过，就跳过
    if any("==== Custom insert start ====" in line for line in text):
        print(f"{file_path} 已经包含插入代码，跳过。")
        return

    insert_code = make_insert_code(qpa_platform)
    new_text = text[:insert_idx] + [insert_code + "\n"] + text[insert_idx:]
    file_path.write_text("".join(new_text), encoding="utf-8")
    print(f"已修改 {file_path}, 设置 QT_QPA_PLATFORM={qpa_platform}")


def postprocess_whl_rpath_qt5(whl_path, skip_tag=["none", "cmake"]):

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
        qt5_dir=unpacked_dir/'PyQt5'
        # set qt5 rpath to 
        print(f"$$$$-set dir {str(qt5_dir)} all *.so rpath to $ORIGIN/Qt5/lib")
        patch_rpath_all(root=qt5_dir)


        qt5_lib_dir=qt5_dir/'Qt5'
        # copy qt5
        print(f"$$$$-copy /opt/Qt5.15.16 to dir {str(qt5_lib_dir)}")
        subprocess.run(["cp", "-ra", '/opt/Qt5.15.16', str(qt5_lib_dir)], check=True)
        subprocess.run(["rm", "-rf", str(qt5_lib_dir/'bin')], check=True)
        subprocess.run(["rm", "-rf", str(qt5_lib_dir/'doc')], check=True)
        subprocess.run(["rm", "-rf", str(qt5_lib_dir/'include')], check=True)
        
        # fix_so_rpaths_in_lib_dir()
        # 修改 init file
        init_file = qt5_dir / '__init__.py'
        libqxcb_path = qt5_lib_dir / 'plugins/platforms/libqxcb.so'
        if os.path.exists(libqxcb_path):
            insert_code_into_file(init_file, 'xcb')
        else:
            insert_code_into_file(init_file, 'wayland')

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
    a = process_whl_rpath_qt5('/home/zq/whl_build/tmp/pyqt5-5.15.11-cp39-abi3-manylinux_2_17_x86_64.whl')
    print(str(a))
