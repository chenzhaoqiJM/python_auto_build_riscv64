#!/bin/bash

# 获取当前脚本所在目录
SCRIPT_DIR_ENV_PYPIC="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR_ENV_PYPIC"/../

wget https://archive.spacemit.com/ros2/prebuilt_libs/pypirc/pypirc.txt

wget https://archive.spacemit.com/ros2/prebuilt_libs/pypirc/pypirc_k3.txt