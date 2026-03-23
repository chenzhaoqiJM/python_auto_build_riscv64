#!/bin/bash

echo "========================================"
echo "OpenCV 构建环境配置"
echo "========================================"

read -r -p "是否启用 ENABLE_CONTRIB? (1=是, 0=否, 默认0): " ENABLE_CONTRIB_INPUT
ENABLE_CONTRIB_INPUT=${ENABLE_CONTRIB_INPUT:-0}

while [[ "$ENABLE_CONTRIB_INPUT" != "0" && "$ENABLE_CONTRIB_INPUT" != "1" ]]; do
	read -r -p "输入无效，请输入 1 或 0: " ENABLE_CONTRIB_INPUT
done

read -r -p "是否启用 ENABLE_HEADLESS? (1=是, 0=否, 默认0): " ENABLE_HEADLESS_INPUT
ENABLE_HEADLESS_INPUT=${ENABLE_HEADLESS_INPUT:-0}

while [[ "$ENABLE_HEADLESS_INPUT" != "0" && "$ENABLE_HEADLESS_INPUT" != "1" ]]; do
	read -r -p "输入无效，请输入 1 或 0: " ENABLE_HEADLESS_INPUT
done

echo ""
echo "请选择要构建的包："
echo "  1) opencv-python"
echo "  2) opencv-contrib-python"
echo "  3) opencv-contrib-python-headless"
echo "  4) opencv-python-headless"

read -r -p "请输入选项编号 (1-4): " OPENCV_PKG_CHOICE

while [[ ! "$OPENCV_PKG_CHOICE" =~ ^[1-4]$ ]]; do
	read -r -p "输入无效，请输入 1-4: " OPENCV_PKG_CHOICE
done

case "$OPENCV_PKG_CHOICE" in
	1)
		PACKAGE_NAME="opencv-python"
		ENABLE_CONTRIB_INPUT=0
		ENABLE_HEADLESS_INPUT=0
		;;
	2)
		PACKAGE_NAME="opencv-contrib-python"
		ENABLE_CONTRIB_INPUT=1
		ENABLE_HEADLESS_INPUT=0
		;;
	3)
		PACKAGE_NAME="opencv-contrib-python-headless"
		ENABLE_CONTRIB_INPUT=1
		ENABLE_HEADLESS_INPUT=1
		;;
	4)
		PACKAGE_NAME="opencv-python-headless"
		ENABLE_CONTRIB_INPUT=0
		ENABLE_HEADLESS_INPUT=1
		;;
esac

read -r -p "请输入版本号: " PACKAGE_VERSION
while [[ -z "$PACKAGE_VERSION" ]]; do
	read -r -p "版本号不能为空，请重新输入: " PACKAGE_VERSION
done

export ENABLE_CONTRIB="$ENABLE_CONTRIB_INPUT"
export ENABLE_HEADLESS="$ENABLE_HEADLESS_INPUT"
export PACKAGE_NAME_REAL="${PACKAGE_NAME}==${PACKAGE_VERSION}"

echo ""
echo "已设置环境变量："
echo "  ENABLE_CONTRIB=$ENABLE_CONTRIB"
echo "  ENABLE_HEADLESS=$ENABLE_HEADLESS"
echo "  PACKAGE_NAME_REAL=$PACKAGE_NAME_REAL"
