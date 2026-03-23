import sys

py_version = sys.version_info

_IS_PY39 = (py_version.major, py_version.minor) == (3, 9)
# 过滤 abi3
# 包名：允许以abi3形式通过的版本是否满足
CHANGE_TO_ABI3_MAP = {
    "opencv-python":_IS_PY39, "opencv-contrib-python":_IS_PY39,
    "opencv-python-headless":_IS_PY39, "opencv-contrib-python-headless":_IS_PY39,
}