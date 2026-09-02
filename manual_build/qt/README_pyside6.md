# pyside6 手动构建

## 步骤

```bash
git clone https://github.com/qtproject/pyside-pyside-setup.git
```

```bash
cd pyside-pyside-setup
git checkout 6.11.2
```

### 创建构建虚拟环境

```bash
uv venv build_qt --python=3.12
source build_qt/bin/activate
uv pip install pip -U
deactivate
```

```bash
source build_qt/bin/activate
pip install -r ~/pyside-pyside-setup/requirements.txt
```

### 构建

```bash
sudo apt install libclang-18-dev clang-18
```

```bash
export LLVM_INSTALL_DIR=/usr/lib/llvm-18
source ~/python_auto_build_riscv64/build_most_common/src_env/qt.sh # 按需填写
```

```bash
cd pyside-pyside-setup
python setup.py bdist_wheel
```

### 后处理

解包原始 whl

```bash
wheel unpack ./pyside6-6.11.2-6.11.2-cp312-cp312-linux_riscv64.whl -d tmp
```

修复动态库

```bash
cd ~/python_auto_build_riscv64

python3 -c 'from common_py.fix_whl.fix_rpath_common import patch_rpath_all; patch_rpath_all(
    root="/home/pipro/whls/pyside-pyside-setup/dist/tmp/pyside6-6.11.2/PySide6",
    pattern="*.so",
    new_rpath="$ORIGIN/:$ORIGIN/Qt/lib:$ORIGIN/../shiboken6/"
)'

python3 -c 'from common_py.fix_whl.fix_rpath_common import patch_rpath_all; patch_rpath_all(
    root="/home/pipro/whls/pyside-pyside-setup/dist/tmp/pyside6-6.11.2/PySide6",
    pattern="*.so.*",
    new_rpath="$ORIGIN/:$ORIGIN/Qt/lib:$ORIGIN/../shiboken6/"
)'
```

复制动态库

```bash
#进入 /home/pipro/whls/pyside-pyside-setup/dist/tmp/pyside6-6.11.2/PySide6

cp -r /opt/Qt6.11.2/lib ./Qt/
cp -r /opt/Qt6.11.2/plugins ./Qt/
cp -r /opt/Qt6.11.2/qml ./Qt/
cp -r /opt/Qt6.11.2/translations ./Qt/
```

```bash
cd ./Qt/lib
rm -rf *.prl
```

环境变量与abi

```bash
vim __init__.py

os.environ["QT_QPA_PLATFORM"] = "wayland"
```

```bash
cd pyside6-6.11.2.dist-info
```

```bash
vim WHEEL

# Tag: cp312-abi3-linux_riscv64
```

重新打包

```bash
wheel pack pyside6-6.11.2 -d .
```

动态库修复

