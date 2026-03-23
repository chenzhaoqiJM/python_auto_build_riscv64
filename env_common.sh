#!/bin/bash

# 获取当前脚本所在目录
SCRIPT_DIR_ENV_COMMON="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export PATH="$SCRIPT_DIR_ENV_COMMON/bin":$PATH

# export FROM_SOURCE_FLAG="1"
export FROM_SOURCE_FLAG="0"

# auditwheel的平台标签
# export AUDITWHEEL_PLAT_DEF="manylinux_2_39_riscv64"
ARCH=$(uname -m)

GLIBC_VER=$(getconf GNU_LIBC_VERSION | awk '{print $2}')
GLIBC_MAJ=$(echo $GLIBC_VER | cut -d. -f1)
GLIBC_MIN=$(echo $GLIBC_VER | cut -d. -f2)

export AUDITWHEEL_PLAT_DEF="manylinux_${GLIBC_MAJ}_${GLIBC_MIN}_${ARCH}"

export HNSWLIB_NO_NATIVE=1
export CMAKE_POLICY_VERSION_MINIMUM=3.5
# export C_INCLUDE_PATH=$HOME/.pyenv/versions/3.12.3/include/python3.12/cpython:$C_INCLUDE_PATH
# export CPLUS_INCLUDE_PATH=$HOME/.pyenv/versions/3.12.3/include/python3.12/cpython:$CPLUS_INCLUDE_PATH

# for opencv
# export CMAKE_ARGS="-DCMAKE_CXX_FLAGS=-march=rv64gcv -DCMAKE_C_FLAGS=-march=rv64gcv -Wno-error \
# -DWITH_GTK=OFF -DWITH_QT=ON -DWITH_GTK_2_X=OFF"

export CI_BUILD=1 

export MAKEFLAGS="-j$(nproc)"
export NINJAFLAGS="-j$(nproc)"


# 设置 Go 的环境变量，让其使用国内代理
export GOPROXY=https://goproxy.cn,direct

# 设置一个空路径，保证后续算法正常运行
export LD_LIBRARY_PATH=/opt/lib:$LD_LIBRARY_PATH

export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
export UV_EXTRA_INDEX_URL=https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple
# for C++ QT -----------------------------------------------------------------------------
# 添加 Qt lib 路径到 LD_LIBRARY_PATH（防重复）
# if [[ ":$LD_LIBRARY_PATH:" != *":/opt/Qt5.15.16/lib:"* ]]; then
#     export LD_LIBRARY_PATH=/opt/Qt5.15.16/lib:$LD_LIBRARY_PATH
# fi

# # 添加 Qt bin 路径到 PATH（防重复）
# if [[ ":$PATH:" != *":/opt/Qt5.15.16/bin:"* ]]; then
#     export PATH=/opt/Qt5.15.16/bin:$PATH
# fi

# 设置 QTDIR 变量
# export QTDIR=/opt/Qt5.15.16

