#!/usr/bin/env python3
"""
装饰器注册表 - 自动收集构建函数和版本检查函数
"""

SPECIAL_PACKAGES = {}
CHECK_VERSION_MAP = {}

def register(*names):
    """注册构建函数到 SPECIAL_PACKAGES"""
    def decorator(func):
        for name in names:
            SPECIAL_PACKAGES[name] = func
        return func
    return decorator

def version_check(*names):
    """注册版本检查函数到 CHECK_VERSION_MAP"""
    def decorator(func):
        for name in names:
            CHECK_VERSION_MAP[name] = func
        return func
    return decorator
