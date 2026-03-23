#!/usr/bin/env python3
import tomllib
import tomli_w
from pathlib import Path

file_path = Path("pyproject.toml")

data = tomllib.loads(file_path.read_text(encoding="utf-8"))

# 确保存在 build-system.requires
requires = data.setdefault("build-system", {}).setdefault("requires", [])

if "numpy" not in [r.lower() for r in requires]:
    requires.append("numpy")
    print("✅ Added numpy to requires.")
else:
    print("ℹ️ numpy already exists in requires.")

file_path.write_text(tomli_w.dumps(data), encoding="utf-8")
