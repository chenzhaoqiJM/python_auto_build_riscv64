import sys

py_version = sys.version_info

_OPENCV_ABI3_PYTHON_VERSIONS = {(3, 9), (3, 12), (3, 13), (3, 14)}
_USE_OPENCV_ABI3 = (
    py_version.major,
    py_version.minor,
) in _OPENCV_ABI3_PYTHON_VERSIONS
# 过滤 abi3
# 包名：允许以abi3形式通过的版本是否满足
CHANGE_TO_ABI3_MAP = {
    "opencv-python": _USE_OPENCV_ABI3,
    "opencv-contrib-python": _USE_OPENCV_ABI3,
    "opencv-python-headless": _USE_OPENCV_ABI3,
    "opencv-contrib-python-headless": _USE_OPENCV_ABI3,
}
