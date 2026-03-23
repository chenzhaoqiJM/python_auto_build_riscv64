
import re
import subprocess
from pathlib import Path

def get_glibc_version() -> tuple[int, int]:
    """返回 glibc 主版本和次版本，例如 2.39 -> (2, 39)"""
    try:
        out = subprocess.check_output(["ldd", "--version"], text=True)
        # 通常第一行形如 "ldd (Ubuntu GLIBC 2.39-0ubuntu3) 2.39"
        m = re.search(r" (\d+)\.(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 0, 0  # 默认未知版本

print(get_glibc_version())