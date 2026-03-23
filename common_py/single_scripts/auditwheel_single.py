#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
from pathlib import Path

def try_auditwheel_repair(whl_path: Path, output_dir: Path) -> Path:
    whl_name = whl_path.name
    print(f"🛠️  Trying auditwheel repair: {whl_name}")

    # 可配置跳过关键字
    SKIP_KEYWORDS = ["none-any"]  

    # 输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 检查 wheel 名称是否包含跳过关键字
    if any(keyword in whl_name for keyword in SKIP_KEYWORDS):
        print(f"⚠️  Skipping auditwheel repair for wheel with skip-tag: {whl_name}")
        fallback_path = output_dir / whl_name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

    try:
        exclude_libs = [
            'libglib*.so.*', 'libgobject*.so.*', 'libgio*.so.*', 'libX11*.so.*', 'libGLX*.so.*',
            'libGL*.so.*', 'libGLdispatch*.so.*', 'libxcb*.so.*', 'libXau*.so.*', 'libqwayland*.so.*',
            'libXdmcp*.so.*', 'libX*.so*', 'libgdk*.so*', 'libgio*.so*', 'libgmodule*.so*',
            'libgtk*.so*', 'libwayland*.so.*'
        ]

        cmd = [
            "auditwheel", "repair", str(whl_path), "-w", str(output_dir)
        ]

        # 检查 Python 版本并决定是否添加 --no-update-tags
        if sys.version_info.major == 3 and sys.version_info.minor <= 12:
            print(f"🔧 Detected Python {sys.version_info.major}.{sys.version_info.minor} <= 3.12, adding --no-update-tags")
            cmd.append("--no-update-tags")
        else:
            print(f"ℹ️  Detected Python {sys.version_info.major}.{sys.version_info.minor} > 3.12, not adding --no-update-tags")

        for lib in exclude_libs:
            cmd += ["--exclude", lib]

        before_files = set(output_dir.glob("*.whl"))

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("❌ auditwheel repair failed!")
            print(f"   Command: {e.cmd}")
            print(f"   Return code: {e.returncode}")
            if e.stdout:
                print(f"   --- STDOUT ---\n{e.stdout}")
            if e.stderr:
                print(f"   --- STDERR ---\n{e.stderr}")
            # fallback
            fallback_path = output_dir / whl_path.name
            shutil.copy2(whl_path, fallback_path)
            print(f"📋 Copied original wheel to: {fallback_path}")
            return fallback_path

        after_files = set(output_dir.glob("*.whl"))
        new_files = list(after_files - before_files)

        print(f"生成的修复文件：{new_files}")

        if new_files:
            repaired_whl = new_files[0]
            print(f"✅ auditwheel repair succeeded: {repaired_whl.name}")
            return repaired_whl
        else:
            raise FileNotFoundError("No repaired .whl generated")

    except Exception as e:
        print(f"❌ auditwheel repair failed: {e}")
        fallback_path = output_dir / whl_path.name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <wheel路径> <修复后输出目录>")
        sys.exit(1)

    whl_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()

    if not whl_path.exists():
        print(f"❌ 找不到文件: {whl_path}")
        sys.exit(1)

    repaired = try_auditwheel_repair(whl_path, output_dir)
    print(f"最终产物: {repaired}")
