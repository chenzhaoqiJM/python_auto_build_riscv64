#!/usr/bin/env python3
import sys
from pathlib import Path

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <__init__.py 文件路径> [QT_QPA_PLATFORM值]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        sys.exit(1)

    qpa_platform = sys.argv[2] if len(sys.argv) > 2 else "wayland"
    insert_code_into_file(file_path, qpa_platform)
