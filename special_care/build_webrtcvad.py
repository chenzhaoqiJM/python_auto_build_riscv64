#!/usr/bin/env python3

import sys
import subprocess
import tempfile
from pathlib import Path

from tools import download_source_with_retry, extract_source
from registry import register


def patch_project(source_dir: Path):
    """
    Patch py-webrtcvad to recognize riscv64 in the bundled WebRTC typedefs.
    """
    typedefs_file = source_dir / "cbits" / "webrtc" / "typedefs.h"
    if not typedefs_file.exists():
        raise FileNotFoundError(f"❌ 未找到 {typedefs_file}，确认源码目录是否正确")

    text = typedefs_file.read_text(encoding="utf-8")

    riscv_block = """#elif defined(__riscv) || defined(__riscv__)\n#define WEBRTC_ARCH_64_BITS\n#define WEBRTC_ARCH_LITTLE_ENDIAN"""

    if "defined(__riscv) || defined(__riscv__)" in text:
        print("✅ typedefs.h 已包含 riscv64 支持，跳过 patch")
        return

    anchor = "#elif defined(__aarch64__)\n#define WEBRTC_ARCH_64_BITS\n#define WEBRTC_ARCH_LITTLE_ENDIAN"
    if anchor not in text:
        raise RuntimeError("❌ 未找到 typedefs.h 中预期的架构检测代码，无法自动 patch")

    text = text.replace(anchor, anchor + "\n" + riscv_block, 1)
    typedefs_file.write_text(text, encoding="utf-8")
    print("✅ 已为 webrtcvad 添加 riscv64 架构支持 patch")


def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )


@register("webrtcvad")
def build_webrtcvad_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)

            patch_project(Path(source_dir))
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)
