#!/bin/bash

if [[ -n "${BASH_VERSION:-}" ]]; then
    QT_SRC_ENV_FILE="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    QT_SRC_ENV_FILE="${(%):-%N}"
else
    echo "❌ 仅支持在 Bash 或 zsh 中加载此脚本"
    return 1 2>/dev/null || exit 1
fi

if { [[ -n "${BASH_VERSION:-}" && "$QT_SRC_ENV_FILE" == "$0" ]] \
    || [[ -n "${ZSH_VERSION:-}" && "${ZSH_EVAL_CONTEXT:-}" != *:file* ]]; }; then
    echo "❌ 此脚本需要通过 source 加载，否则环境变量不会保留："
    echo "    source $QT_SRC_ENV_FILE"
    exit 1
fi

qt_read_prompt() {
    printf "%s" "$1"
    IFS= read -r "$2"
}

echo "========================================"
echo "Qt Python 绑定构建环境配置"
echo "========================================"
echo ""
echo "请选择要构建的包："
echo "  1) pyqt5"
echo "  2) pyqt6"
echo "  3) pyside2"
echo "  4) pyside6"

qt_read_prompt "请输入选项编号 (1-4): " QT_PKG_CHOICE
while [[ ! "$QT_PKG_CHOICE" =~ ^[1-4]$ ]]; do
    qt_read_prompt "输入无效，请输入 1-4: " QT_PKG_CHOICE
done

case "$QT_PKG_CHOICE" in
    1)
        QT_PACKAGE_NAME="pyqt5"
        QT_EXPECTED_MAJOR=5
        ;;
    2)
        QT_PACKAGE_NAME="pyqt6"
        QT_EXPECTED_MAJOR=6
        ;;
    3)
        QT_PACKAGE_NAME="pyside2"
        QT_EXPECTED_MAJOR=5
        ;;
    4)
        QT_PACKAGE_NAME="pyside6"
        QT_EXPECTED_MAJOR=6
        ;;
esac

qt_read_prompt "请输入 ${QT_PACKAGE_NAME} 版本号: " QT_PACKAGE_VERSION
while [[ -z "$QT_PACKAGE_VERSION" ]]; do
    qt_read_prompt "版本号不能为空，请重新输入: " QT_PACKAGE_VERSION
done

QT_PREFIX_DEFAULT="${QT_INSTALL_PREFIX:-/opt/Qt${QT_EXPECTED_MAJOR}}"
while true; do
    qt_read_prompt "请输入 Qt${QT_EXPECTED_MAJOR} 安装目录 (默认 ${QT_PREFIX_DEFAULT}): " QT_PREFIX_INPUT
    QT_PREFIX_INPUT="${QT_PREFIX_INPUT:-$QT_PREFIX_DEFAULT}"

    if [[ ! -d "$QT_PREFIX_INPUT" ]]; then
        echo "❌ Qt 安装目录不存在: $QT_PREFIX_INPUT"
        continue
    fi

    if [[ ! -d "$QT_PREFIX_INPUT/lib" ]]; then
        echo "❌ Qt lib 目录不存在: $QT_PREFIX_INPUT/lib"
        continue
    fi

    QT_PREFIX_RESOLVED="$(cd "$QT_PREFIX_INPUT" && pwd -P)"
    break
done

export QT_INSTALL_PREFIX="$QT_PREFIX_RESOLVED"
export PACKAGE_NAME_REAL="${QT_PACKAGE_NAME}==${QT_PACKAGE_VERSION}"
export QTDIR="$QT_INSTALL_PREFIX"

case ":${PATH:-}:" in
    *":$QT_INSTALL_PREFIX/bin:"*) ;;
    *) export PATH="$QT_INSTALL_PREFIX/bin${PATH:+:$PATH}" ;;
esac

case ":${LD_LIBRARY_PATH:-}:" in
    *":$QT_INSTALL_PREFIX/lib:"*) ;;
    *) export LD_LIBRARY_PATH="$QT_INSTALL_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
esac

echo ""
echo "已设置环境变量："
echo "  QT_INSTALL_PREFIX=$QT_INSTALL_PREFIX"
echo "  PACKAGE_NAME_REAL=$PACKAGE_NAME_REAL"
echo "  QTDIR=$QTDIR"
echo "  PATH=$PATH"
echo "  LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "  qmake=$(command -v qmake 2>/dev/null || true)"
echo ""
echo "接下来可执行："
echo "  pip wheel . --no-build-isolation -w /path/to/wheel-dir"
echo "  ./build_most_common/build_from_src.sh /path/to/source"
unset QT_PKG_CHOICE QT_PACKAGE_NAME QT_EXPECTED_MAJOR QT_PACKAGE_VERSION
unset QT_PREFIX_DEFAULT QT_PREFIX_INPUT QT_PREFIX_RESOLVED
unset QT_SRC_ENV_FILE
unset -f qt_read_prompt
