# 手动构建脚本

本目录存放需要特殊处理或手动触发的 RISC-V Python wheel 构建脚本。

## PySide6

`build_pyside6.sh` 会自动创建 Python 虚拟环境和隔离的源码副本，依次构建、修复并检查
`pyside6`、`shiboken6` 和 `shiboken6_generator` wheel，不会修改传入的源码目录。

```bash
./build_pyside6.sh <pyside源码目录> <Qt安装目录>
```

示例：

```bash
./build_pyside6.sh "$HOME/pyside-pyside-setup" /opt/Qt6.11.2
```

默认使用 Python 3.12，产物保存到：

```text
$HOME/whls/pyside6-wheelhouse
```

常用选项：

- `--check-only`：只创建环境并检查依赖。
- `--keep-work`：构建成功后保留临时工作目录。
- `--upload`：构建成功后上传 wheel，使用前请确认上传配置。

如需选择其他 Python 版本，可设置 `BUILD_FOR_VERSION`：

```bash
BUILD_FOR_VERSION=3.13 ./build_pyside6.sh <pyside源码目录> <Qt安装目录>
```

更详细的构建背景和排错记录见 [`qt/README_pyside6.md`](qt/README_pyside6.md)。
