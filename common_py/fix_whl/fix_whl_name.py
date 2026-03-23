import subprocess
import tempfile
from pathlib import Path
import os
import sys

# 获取common_py_dir
current_dir = os.path.dirname(os.path.abspath(__file__))
common_py_dir = os.path.join(current_dir, '../')
sys.path.insert(0, common_py_dir)
from abi3_adapter import CHANGE_TO_ABI3_MAP

def patch_whl_to_abi3(whl_path, new_abi_tag="abi3"):
    """
    将 wheel 内部的 ABI tag 改成 abi3，并重新打包。
    文件名会自动更新为带 abi3 的版本。
    """
    whl_path = Path(whl_path).resolve()
    if not whl_path.exists() or whl_path.suffix != ".whl":
        print(f"[✗] Not a valid .whl file: {whl_path}")
        return whl_path

    pkg_name = (whl_path.name).split('-')[0]
    pkg_name = pkg_name.replace("_", "-")

    if not CHANGE_TO_ABI3_MAP.get(pkg_name, False):
        print(f"不处理 {pkg_name} 包为 abi3")
        return whl_path
    else:
        print("添加 abi3 Tag ...................")

    # 生成当前解释器对应的 py_tag，比如 cp312
    version = sys.version_info
    py_tag = f"cp{version.major}{version.minor}"
    old_abi_tag = py_tag

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        print(f"[+] Unpacking {whl_path.name} ...")
        subprocess.run(["wheel", "unpack", str(whl_path), "-d", str(tmpdir)], check=True)

        unpacked_dir = next(tmpdir.glob("*"))  # wheel unpack 会在 tmpdir 下生成一个目录

        # 修改 WHEEL 文件里的 Tag
        dist_info_dirs = list(unpacked_dir.glob("*.dist-info"))
        if not dist_info_dirs:
            print("[✗] No .dist-info directory found")
            return whl_path
        wheel_file = dist_info_dirs[0] / "WHEEL"

        print(f"[+] Patching WHEEL metadata: {wheel_file}")
        text = wheel_file.read_text()
        new_text = text.replace(f"Tag: {py_tag}-{old_abi_tag}", f"Tag: {py_tag}-{new_abi_tag}")
        wheel_file.write_text(new_text)

        # 重新打包
        subprocess.run(["wheel", "pack", str(unpacked_dir), "-d", str(whl_path.parent)], check=True)

        # wheel pack 会生成新的文件名
        packed_whl = max(whl_path.parent.glob("*.whl"), key=lambda p: p.stat().st_mtime)
        print(f"[✅] New wheel generated: {packed_whl.name}")

        return packed_whl