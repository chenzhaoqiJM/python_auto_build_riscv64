#!/usr/bin/env python3
import sys
import subprocess
import tempfile
import os
import tarfile
import zipfile
from pathlib import Path
import importlib
import glob

from tools import has_whl_in_gitlab_with_retry, download_source_with_retry, extract_source

from build_all import build_all_func

# 自动导入所有 build_*.py 模块，触发装饰器注册
current_dir = Path(__file__).parent
for py_file in current_dir.glob("build_*.py"):
    module_name = py_file.stem
    if module_name != "build_all":  # build_all 不需要注册
        importlib.import_module(module_name)

# 从 registry 获取注册的函数
from registry import SPECIAL_PACKAGES, CHECK_VERSION_MAP

# 获取common_py_dir
common_py_dir = os.path.join(current_dir, '../common_py')
sys.path.insert(0, common_py_dir)
from abi3_adapter import CHANGE_TO_ABI3_MAP

def main():
    if len(sys.argv) < 2:
        print("Usage: special_builder.py <package> [<wheel_dir>]", file=sys.stderr)
        sys.exit(100)

    package = sys.argv[1] # prob is: pkg or pkg==version
    wheel_dir = sys.argv[2] if len(sys.argv) >= 3 else os.getcwd()

    name = package.split("==")[0].strip()

    FROM_SOURCE_FLAG = os.environ.get("FROM_SOURCE_FLAG") # 强制从源码构建

    if name not in SPECIAL_PACKAGES:

        if FROM_SOURCE_FLAG == "1":
            pass
        else:
            sys.exit(100)  # 告诉 Bash 脚本：不处理这个包

    try:
        if FROM_SOURCE_FLAG == "1":
            AUDITWHEEL_PLAT_DEF = os.environ.get("AUDITWHEEL_PLAT_DEF")

            # 先检查版本
            # if name in CHECK_VERSION_MAP:
            #     if_build_here = CHECK_VERSION_MAP[name](package, wheel_dir)
            #     if not if_build_here:
            #         print("$$$$-回退到正常构建流程...............")
            #         sys.exit(100)

            # 检查有无whl
            found, filenames = has_whl_in_gitlab_with_retry(package)

            print("have: ", filenames)

            for file in filenames:
                if AUDITWHEEL_PLAT_DEF in str(file) or 'none' in str(file):
                    print(f"✅ Aready exist {file}")
                    sys.exit(0)

            if name in SPECIAL_PACKAGES:
                SPECIAL_PACKAGES[name](package, wheel_dir)
            else:
                build_all_func(package, wheel_dir)

        else:

            # 先检查版本
            if name in CHECK_VERSION_MAP:
                if_build_here = CHECK_VERSION_MAP[name](package, wheel_dir)
                if not if_build_here:
                    print("$$$$-回退到正常构建流程...............")
                    sys.exit(100)


            # 检查有无whl
            found, filenames = has_whl_in_gitlab_with_retry(package)

            # 检查 abi3 过滤准则
            # 要求 opencv py39 只要有 abi3 就通过
            only_need_abi3 = False # 是否有abi3就通过
            change_to_abi_flag=False
            if name in CHANGE_TO_ABI3_MAP:
                change_to_abi_flag=True
                only_need_abi3 = CHANGE_TO_ABI3_MAP[name]

            # 检查是否存在 abi3 whl
            abi3_whl_exist = False
            for whl_file in filenames:
                if 'abi3' in whl_file:
                    abi3_whl_exist = True

            if found:
                if abi3_whl_exist:
                    if only_need_abi3:
                        print(f"✅ Aready exist abi3 whl for {filenames}")
                        sys.exit(0)
                    else:
                        if len(filenames) >= 2:
                            print(f"✅ Aready exist {filenames}")
                            sys.exit(0)
                        else:
                            if change_to_abi_flag:
                                print(f"仅仅检测到 {filenames}， 不跳过构建")
                            else:
                                print(f"✅ Aready exist {filenames}")
                                sys.exit(0)

                else:
                    if only_need_abi3:
                        print("执行 abi3 构建.......................")
                        pass
                    else:
                        print(f"✅ Aready exist {filenames}")
                        sys.exit(0)
            else:
                print("没有找到可用的 whl 包，执行构建.................")

            if name in SPECIAL_PACKAGES:
                SPECIAL_PACKAGES[name](package, wheel_dir)


    except Exception as e:
        print(f"❌ Error building {package}: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)  # 构建成功

if __name__ == "__main__":
    main()
