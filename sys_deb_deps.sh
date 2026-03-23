#!/bin/bash
set -e  # 如果任何命令失败则退出
set -u  # 使用未定义变量时报错

# 获取 glibc 版本号（只取主次版本号，如 2.39、2.41）
GLIBC_VERSION=$(ldd --version 2>&1 \
    | grep -oE '[0-9]+\.[0-9]+' \
    | head -n1)

case "$GLIBC_VERSION" in
    "2.39")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential
            libgeos-dev libproj-dev proj-data proj-bin python3-requests patchelf libavcodec-dev libavformat-dev libavutil-dev libswscale-dev
            ffmpeg libpng-dev libtiff-dev libopenexr-dev libavif-dev libgif-dev bison libblas-dev bzip2 ccache
            coreutils diffutils dos2unix environment-modules file findutils flex fontconfig libfontconfig-dev gawk gdb gettext libgmp-dev
            gnupg gperf gzip libhwloc-dev libisl-dev libkrb5-dev liblapack-dev libxext-dev libxfixes3 libxfixes-dev libcurl4 libcurl4-openssl-dev
            libgomp1 libjpeg62 uuid-dev libgbm-dev meson libmpfr-dev libncurses-dev openssl p7zip-full
            patch libpcre3-dev perl lsb-release rsync sqlite3 libsqlite3-dev tar unzip util-linux xz-utils
            libclang-dev libclang-18-dev clang-18 portaudio19-dev libcjson-dev libasound2-dev
            libgirepository-2.0-dev libqpdf-dev libpq-dev librados-dev libibverbs-dev python3-sphinx
            python3-routes librdmacm-dev libudev-dev libkeyutils-dev libfuse-dev libcryptsetup-dev libnbd-dev
            libaio-dev libsnappy-dev liblz4-dev libbabeltrace-dev libthrift-dev thrift-compiler libcap-dev liblua5.3-dev
            libnl-3-dev libnl-genl-3-dev libcap-ng-dev librdkafka-dev librabbitmq-dev liblmdb-dev
            libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev pax-utils fonts-dejavu-core
            librsync-dev default-libmysqlclient-dev libcups2-dev libssh-dev nanobind-dev
            llvm-dev libacl1-dev unixodbc-dev freetds-dev graphviz graphviz-dev libxml2-dev libxmlsec1-dev
            gdal-bin libgdal-dev libdebuginfod-dev libunwind-dev libldap2-dev libsasl2-dev libsleef3 libsleef-dev libleveldb-dev
            protobuf-compiler libgflags-dev libgoogle-glog-dev libogre-1.9-dev libtesseract-dev libleptonica-dev screen
            libusb-1.0-0-dev libsrtp2-dev libopenmpi-dev libgfortran-14-dev
            llvm-14-dev clang-14 llvm-15-dev clang-15 llvm-19-dev clang-19 libxml2 libxmlsec1t64-openssl
        )
        ;;
    "2.41")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential
            libgeos-dev libproj-dev proj-data proj-bin python3-requests patchelf libavcodec-dev libavformat-dev libavutil-dev libswscale-dev
            ffmpeg libpng-dev libtiff-dev libopenexr-dev libavif-dev libgif-dev bison libblas-dev bzip2 ccache
            coreutils diffutils dos2unix environment-modules file findutils flex fontconfig libfontconfig-dev gawk gdb gettext libgmp-dev
            gnupg gperf gzip libhwloc-dev libisl-dev libkrb5-dev liblapack-dev libxext-dev libxfixes3 libxfixes-dev libcurl4 libcurl4-openssl-dev
            libgomp1 libjpeg62 uuid-dev libgbm-dev meson libmpfr-dev libncurses-dev openssl p7zip-full
            patch libpcre3-dev perl lsb-release rsync sqlite3 libsqlite3-dev tar unzip util-linux xz-utils
            libclang-dev libclang-18-dev clang-18 portaudio19-dev libcjson-dev libasound2-dev
            libgirepository-2.0-dev libqpdf-dev libpq-dev librados-dev libibverbs-dev python3-sphinx
            python3-routes librdmacm-dev libudev-dev libkeyutils-dev libfuse-dev libcryptsetup-dev libnbd-dev
            libaio-dev libsnappy-dev liblz4-dev libbabeltrace-dev libthrift-dev thrift-compiler libcap-dev liblua5.3-dev
            libnl-3-dev libnl-genl-3-dev libcap-ng-dev librdkafka-dev librabbitmq-dev liblmdb-dev
            libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev pax-utils fonts-dejavu-core
            librsync-dev default-libmysqlclient-dev libcups2-dev libssh-dev nanobind-dev
            llvm-dev libacl1-dev unixodbc-dev freetds-dev graphviz graphviz-dev libxml2-dev libxmlsec1-dev
            gdal-bin libgdal-dev libdebuginfod-dev libunwind-dev libldap2-dev libsasl2-dev libsleef3 libsleef-dev libleveldb-dev
            protobuf-compiler libgflags-dev libgoogle-glog-dev libogre-1.9-dev libtesseract-dev libleptonica-dev screen
            libusb-1.0-0-dev libsrtp2-dev libopenmpi-dev libgfortran-14-dev
            llvm-14-dev clang-14 llvm-15-dev clang-15 llvm-19-dev clang-19 llvm-20-dev clang-20 libxml2 libxmlsec1t64-openssl
        )
        ;;
    "2.42")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential
            libgeos-dev libproj-dev proj-data proj-bin python3-requests patchelf libavcodec-dev libavformat-dev libavutil-dev libswscale-dev
            ffmpeg libpng-dev libtiff-dev libopenexr-dev libavif-dev libgif-dev bison libblas-dev bzip2 ccache
            coreutils diffutils dos2unix environment-modules file findutils flex fontconfig libfontconfig-dev gawk gdb gettext libgmp-dev
            gnupg gperf gzip libhwloc-dev libisl-dev libkrb5-dev liblapack-dev libxext-dev libxfixes3 libxfixes-dev libcurl4 libcurl4-openssl-dev
            libgomp1 libjpeg62 uuid-dev libgbm-dev meson libmpfr-dev libncurses-dev openssl p7zip-full
            patch libpcre3-dev perl lsb-release rsync sqlite3 libsqlite3-dev tar unzip util-linux xz-utils
            libclang-dev libclang-18-dev clang-18 portaudio19-dev libcjson-dev libasound2-dev
            libgirepository-2.0-dev libqpdf-dev libpq-dev librados-dev libibverbs-dev python3-sphinx
            python3-routes librdmacm-dev libudev-dev libkeyutils-dev libfuse-dev libcryptsetup-dev libnbd-dev
            libaio-dev libsnappy-dev liblz4-dev libbabeltrace-dev libthrift-dev thrift-compiler libcap-dev liblua5.3-dev
            libnl-3-dev libnl-genl-3-dev libcap-ng-dev librdkafka-dev librabbitmq-dev liblmdb-dev
            libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev pax-utils fonts-dejavu-core
            librsync-dev default-libmysqlclient-dev libcups2-dev libssh-dev nanobind-dev
            llvm-dev libacl1-dev unixodbc-dev freetds-dev graphviz graphviz-dev libxmlsec1-dev
            gdal-bin libgdal-dev libdebuginfod-dev libunwind-dev libldap2-dev libsasl2-dev libsleef3 libsleef-dev libleveldb-dev
            protobuf-compiler libgflags-dev libgoogle-glog-dev libogre-1.9-dev libtesseract-dev libleptonica-dev screen
            libusb-1.0-0-dev libsrtp2-dev libopenmpi-dev libgfortran-14-dev
            llvm-14-dev clang-14 llvm-19-dev clang-19 llvm-20-dev clang-20 llvm-21-dev clang-21
            libxmlsec1-openssl1
        )
        ;;
    "2.43")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential
            libgeos-dev libproj-dev proj-data proj-bin python3-requests patchelf libavcodec-dev libavformat-dev libavutil-dev libswscale-dev
            ffmpeg libpng-dev libtiff-dev libopenexr-dev libavif-dev libgif-dev bison libblas-dev bzip2 ccache
            coreutils diffutils dos2unix environment-modules file findutils flex fontconfig libfontconfig-dev gawk gdb gettext libgmp-dev
            gnupg gperf gzip libhwloc-dev libisl-dev libkrb5-dev liblapack-dev libxext-dev libxfixes3 libxfixes-dev libcurl4 libcurl4-openssl-dev
            libgomp1 libjpeg62 uuid-dev libgbm-dev meson libmpfr-dev libncurses-dev openssl p7zip-full
            patch libpcre3-dev perl lsb-release rsync sqlite3 libsqlite3-dev tar unzip util-linux xz-utils
            libclang-dev libclang-18-dev clang-18 portaudio19-dev libcjson-dev libasound2-dev
            libgirepository-2.0-dev libqpdf-dev libpq-dev librados-dev libibverbs-dev python3-sphinx
            python3-routes librdmacm-dev libudev-dev libkeyutils-dev libfuse-dev libcryptsetup-dev libnbd-dev
            libaio-dev libsnappy-dev liblz4-dev libbabeltrace-dev libthrift-dev thrift-compiler libcap-dev liblua5.3-dev
            libnl-3-dev libnl-genl-3-dev libcap-ng-dev librdkafka-dev librabbitmq-dev liblmdb-dev
            libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev pax-utils fonts-dejavu-core
            librsync-dev default-libmysqlclient-dev libcups2-dev libssh-dev nanobind-dev
            llvm-dev libacl1-dev unixodbc-dev freetds-dev graphviz graphviz-dev libxmlsec1-dev
            gdal-bin libgdal-dev libdebuginfod-dev libunwind-dev libldap2-dev libsasl2-dev libsleef3 libsleef-dev libleveldb-dev
            protobuf-compiler libgflags-dev libgoogle-glog-dev libogre-1.9-dev libtesseract-dev libleptonica-dev screen
            libusb-1.0-0-dev libsrtp2-dev libopenmpi-dev libgfortran-14-dev
            llvm-14-dev clang-14 llvm-19-dev clang-19 llvm-20-dev clang-20 llvm-21-dev clang-21
            libxmlsec1-openssl1
        )
        ;;
    *)
        echo "❌ 不支持的 glibc 版本: $GLIBC_VERSION"
        exit 1
        ;;
esac

echo "🔄 更新 apt 源并安装构建依赖..."
sudo apt update
if sudo apt install -y --allow-downgrades "${BUILD_DEPS[@]}"; then
    echo "✅ 所有构建依赖安装成功"
else
    echo "❌ 构建依赖安装失败"
    exit 1
fi