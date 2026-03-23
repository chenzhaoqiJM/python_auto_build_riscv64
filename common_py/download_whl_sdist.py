import json
import subprocess
import sys
import urllib.request
import os

def fetch_latest_version(package, index_url='https://pypi.org/pypi'):
    """
    获取指定包的最新版本号
    """
    json_url = f"{index_url}/{package}/json"
    with urllib.request.urlopen(json_url) as resp:
        data = json.load(resp)
    return data["info"]["version"]

def download_sdist(package, version=None, dest_dir='.', filename=None, index_url='https://pypi.org/pypi'):
    """
    下载指定PyPI包的源码包（sdist）
    
    参数：
    - package: 包名
    - version: 版本号，如 None 则自动获取最新版本
    - dest_dir: 下载目录
    - filename: 保存为本地的文件名
    - index_url: JSON API基础地址
    """
    if not version:
        version = fetch_latest_version(package, index_url)
        print(f"未指定版本号，自动获取最新版本: {version}")

    json_url = f"{index_url}/{package}/{version}/json"
    print(f"查询 {package}=={version} 的源码包链接: {json_url}")
    with urllib.request.urlopen(json_url) as resp:
        data = json.load(resp)

    sdist_info = None
    for file_info in data.get("urls", []):
        if file_info.get("packagetype") == "sdist":
            sdist_info = file_info
            break

    if not sdist_info:
        raise RuntimeError(f"未找到 {package}=={version} 的源码包")

    download_url = sdist_info["url"]
    server_filename = sdist_info["filename"]
    save_name = filename or server_filename
    save_path = os.path.join(dest_dir, save_name)
    print(f"源码包链接: {download_url}")
    print(f"保存为: {save_path}")

    # 调用 wget 下载
    cmd = ["wget", download_url, "-O", save_path]
    print("开始下载...")
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        raise RuntimeError("wget 下载失败")

    print("下载完成")
    return save_path, version

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="下载PyPI包的源码包(sdist)")
    parser.add_argument("package", help="包名，如 lintrunner")
    parser.add_argument("version", nargs="?", default=None, help="版本号（可选），默认最新")
    parser.add_argument("--dest", default=".", help="下载目录，默认当前目录")
    parser.add_argument("--filename", default=None, help="保存文件名，默认用服务器原始文件名")
    parser.add_argument("--index-url", default="https://pypi.org/pypi", help="PyPI JSON接口基础地址")

    args = parser.parse_args()
    try:
        download_sdist(args.package, args.version, args.dest, args.filename, args.index_url)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
