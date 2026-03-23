#!/usr/bin/env python3
import sys
from pathlib import Path
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
current_dir = os.path.abspath(current_dir)
# 包名
pkg = sys.argv[1]
pkg = pkg.split("==", 1)[0]

# 配置文件路径（和你的bash在同级或者自己改路径）
config_file = os.path.join(current_dir, "no_deps_list.txt")
config_file = Path(config_file)

no_deps = set()
if config_file.exists():
    with config_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 去掉可能的版本号，例如 numpy==2.3.2 -> numpy
            name = line.split("==", 1)[0]
            no_deps.add(name)

# 输出结果，命中则输出 --no-deps，否则输出空
if pkg in no_deps:
    print("--no-deps")
else:
    print("")
