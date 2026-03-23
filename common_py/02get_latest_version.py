#!/usr/bin/env python3

import sys
import json
import urllib.request
import urllib.error


def fetch_latest_version(package, index_url="https://pypi.org/pypi"):
    """
    获取指定包的最新版本号
    """
    json_url = f"{index_url}/{package}/json"
    with urllib.request.urlopen(json_url, timeout=5) as resp:
        data = json.load(resp)
    return data["info"]["version"]


def main():
    package = sys.argv[1]

    if "==" in package:
        print(package)
        sys.exit(0)

    try:
        version = fetch_latest_version(package)
        print(f"{package}=={version}")
    except Exception:
        # 任意失败（网络 / 不存在 / JSON 异常）
        print(package)


if __name__ == "__main__":
    main()
