#!/usr/bin/env python3
import sys
import os
from tools import has_whl_in_gitlab_with_retry

def main():
    if len(sys.argv) < 2:
        print("Usage: check_whl_exist.py <package>", file=sys.stderr)
        sys.exit(100)

    package = sys.argv[1]  # pkg 或 pkg==version
    AUDITWHEEL_PLAT_DEF = os.environ.get("AUDITWHEEL_PLAT_DEF")

    FROM_SOURCE_FLAG = os.environ.get("FROM_SOURCE_FLAG")

    try:
        found, filenames = has_whl_in_gitlab_with_retry(package)

        if not found:
            sys.exit(1)  # 没找到

        # 如果设置了平台要求，就进一步检查
        if FROM_SOURCE_FLAG == "1":
            for file in filenames:
                if AUDITWHEEL_PLAT_DEF in str(file) or 'none' in str(file):
                    print(f"✅ Found {file}")
                    sys.exit(0)
            # 找到了 whl 但是不满足平台
            sys.exit(2)
        else:
            # 只要找到就算成功
            print(f"✅ Found {filenames}")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error checking {package}: {e}", file=sys.stderr)
        sys.exit(99)

if __name__ == "__main__":
    main()
