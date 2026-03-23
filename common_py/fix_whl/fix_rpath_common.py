import os
import subprocess
import shutil
from pathlib import Path
import hashlib
import base64
import tempfile
from zipfile import ZipInfo
import stat
import pathlib
from typing import Union

def run_ldd(path):
    try:
        return subprocess.check_output(["ldd", str(path)], text=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] ldd failed on {path}: {e}")
        return ""

def parse_ldd_output(output):
    missing = []
    for line in output.splitlines():
        if "=>" not in line:
            continue
        parts = line.split("=>")
        lib = parts[0].strip()
        if "not found" in parts[1]:
            missing.append(lib)
    return missing

def lib_exists_in_dir(lib_name, lib_dir):
    return any(Path(f).name == lib_name for f in os.listdir(lib_dir))

def is_elf(file_path):
    try:
        with open(file_path, 'rb') as f:
            return f.read(4) == b'\x7fELF'
    except:
        return False

def rpath_already_set(so_file, target_rpath='$ORIGIN'):
    """
    检查目标 rpath 是否已经存在于 so_file 的 RPATH 条目中。
    RPATH 可包含多个路径（以 ':' 分隔），只要 target_rpath 是其中之一即视为已设置。
    """
    try:
        out = subprocess.check_output(['patchelf', '--print-rpath', str(so_file)], text=True).strip()
        if not out:
            return False
        existing_rpaths = [p.strip() for p in out.split(':')]
        return target_rpath in existing_rpaths
    except:
        return False

def set_rpath(so_file, rpath='$ORIGIN'):

    if rpath_already_set(so_file, rpath):
        print(f"[↪] rpath already set on: {so_file.name}")
        return

    try:
        subprocess.check_call(['patchelf', '--set-rpath', rpath, str(so_file)])
        print(f"[✓] rpath set: {so_file.name}")
    except subprocess.CalledProcessError as e:
        print(f"[✗] Failed to set rpath on {so_file.name}: {e}")

def get_ldd_lib_names(output):
    libs = []
    for line in output.splitlines():
        if "=>" not in line:
            continue
        parts = line.split("=>")
        lib_name = parts[0].strip()
        # 排除linux-vdso和ld-linux等特殊项
        if lib_name and lib_name != "linux-vdso.so.1" and not lib_name.startswith("/"):
            libs.append(lib_name)
        # libs.append(lib_name)
    return libs

def fix_so_rpaths_in_lib_dir(lib_dir):
    lib_dir = Path(lib_dir)

    so_files = list(lib_dir.glob("*.so*"))

    resolved_targets = set()

    for so_file in so_files:
        try:
            real_target = so_file.resolve()
        except FileNotFoundError:
            print(f"[⚠️] Broken symlink skipped: {so_file}")
            continue  # 链接坏掉，跳过

        if not is_elf(real_target):
            print(f"[↩] Skipping non-ELF file: {real_target.name}")
            continue

        if real_target in resolved_targets:
            print(f"[↩] Already processed target: {real_target.name} (via {so_file.name})")
            continue
        resolved_targets.add(real_target)

        before_ldd = run_ldd(real_target)
        before_libs = get_ldd_lib_names(before_ldd)
        missing_deps = parse_ldd_output(before_ldd)

        for dep in missing_deps:
            if lib_exists_in_dir(dep, lib_dir):
                print(f"❗ [!] {real_target.name} missing {dep} — attempting fix...")

                backup_path = real_target.with_suffix(real_target.suffix + ".bak")
                shutil.copy2(real_target, backup_path)
                print(f"📦  Backup created: {backup_path.name}")

                set_rpath(real_target)

                after_ldd = run_ldd(real_target)
                after_libs = get_ldd_lib_names(after_ldd)

                if not set(before_libs).issubset(set(after_libs)):
                    print(f"🔁  [✗] Dependency mismatch after patch, reverting 🚫 {real_target.name}")
                    shutil.move(backup_path, real_target)
                else:
                    print(f"✅  [✓] rpath fixed and dependencies verified: {real_target.name}")
                    backup_path.unlink(missing_ok=True)

                break


def patch_rpath_all(
    root: Union[str, pathlib.Path] = ".",
    pattern: str = "*.so",
    new_rpath: str = r"$ORIGIN/Qt5/lib",
    dry_run: bool = False
):
    """
    批量修改指定目录下的 .so 文件 rpath 为 new_rpath

    :param root: 搜索根目录
    :param pattern: 文件匹配模式 (如 '*.so', '*.pyd', '*.so.*')
    :param new_rpath: 新的 RPATH (例如 r"$ORIGIN/Qt5/lib")
    :param dry_run: 如果为 True，只打印不修改
    """
    root = pathlib.Path(root)
    so_files = list(root.rglob(pattern))

    if not so_files:
        print("⚠️ 未找到匹配文件")
        return

    for so in so_files:
        try:
            # 获取原来的 RPATH
            old_rpath = subprocess.run(
                ["patchelf", "--print-rpath", str(so)],
                capture_output=True, text=True
            ).stdout.strip()

            print(f"\n📦 {so}")
            print(f"   原 RPATH: {old_rpath if old_rpath else '(空)'}")
            print(f"   新 RPATH: {new_rpath}")

            if not dry_run:
                subprocess.run(
                    ["patchelf", "--set-rpath", new_rpath, str(so)],
                    check=True
                )
        except subprocess.CalledProcessError as e:
            print(f"❌ 修改失败: {so} ({e})")


if __name__ == "__main__":
    fix_so_rpaths_in_lib_dir('/home/zq/whl_build/qt5-env/lib/python3.12/site-packages/pyqt5.libs')
