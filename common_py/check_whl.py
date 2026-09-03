import requests
import sys
import os
import configparser

current_dir = os.path.dirname(os.path.abspath(__file__))
pypirc_path = os.path.abspath(os.path.join(current_dir, "..", "pypirc.txt"))
home_pypirc_path = os.path.expanduser("~/.pypirc")


def load_gitlab_config():
    """
    从项目 pypirc.txt 或 ~/.pypirc 中读取 GitLab 包仓库配置。
    """
    for path in (pypirc_path, home_pypirc_path):
        if not os.path.isfile(path):
            continue

        config = configparser.ConfigParser()
        config.read(path)
        if not config.has_section("gitlab"):
            continue

        repo = config.get("gitlab", "repository", fallback="").strip()
        if not repo:
            continue

        token = config.get("gitlab", "password", fallback="").strip()
        return repo, token

    raise RuntimeError(
        "GitLab 配置缺失：请在项目根目录 pypirc.txt 或 ~/.pypirc 中配置 "
        "[gitlab] repository/password"
    )

def get_latest_version_from_pypi(package_name, index_url='https://pypi.org/pypi'):
    """
    从 PyPI 官方（或镜像）获取某个包的最新版本号。
    """
    url = f"{index_url.rstrip('/')}/{package_name}/json"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"❌ 获取 PyPI 包失败: {package_name}, 状态码: {resp.status_code}")
            return None
        data = resp.json()
        return data["info"]["version"]
    except Exception as e:
        print(f"❌ 获取 PyPI 版本号异常: {e}")
        return None


def get_current_python_tag():
    """
    返回当前 Python 的 tag，例如 Python 3.12 → 'cp312'
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"cp{major}{minor}"

def wheel_matches_platform(filename, platform_tag):
    """检查 wheel 的 platform 字段是否匹配目标平台；any 适用于所有平台。"""
    if not filename.endswith(".whl"):
        return False
    platforms = filename[:-4].rsplit("-", 1)[-1].split(".")
    return "any" in platforms or not platform_tag or platform_tag in platforms


def has_whl_in_gitlab(package_name, version=None, project_id=33, token=None,
                      platform_tag=None):
    """
    查询 GitLab 包仓库中是否存在当前 Python 版本可用的 .whl 文件。
    如果 version 为 None，则从 PyPI 获取最新版本号。
    """
    print("&&& 检查是否存在 whl ................")
    python_tag = get_current_python_tag()
    gitlab_repo, config_token = load_gitlab_config()
    if token is None:
        token = config_token

    if version is None:
        version = get_latest_version_from_pypi(package_name)
        if not version:
            print(f"⚠️ 无法获取 {package_name} 的最新版本号，终止")
            return False, []

    base_url = gitlab_repo.rsplit('/', 1)[0]
    headers = {"PRIVATE-TOKEN": token} if token else {}

    page = 1
    per_page = 100

    while True:
        url = f"{base_url}?per_page={per_page}&page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"❌ 获取包失败: 状态码 {resp.status_code}")
            return False, []

        pkgs = resp.json()
        if not pkgs:
            break

        for pkg in pkgs:
            if pkg["name"] != package_name or pkg.get("version") != version:
                continue

            # 检查是否有当前 python 版本的 .whl 文件
            file_url = f"{base_url}/{pkg['id']}/package_files"
            files_resp = requests.get(file_url, headers=headers)
            if files_resp.status_code != 200:
                continue
            files = files_resp.json()

            matching_whls = []
            for f in files:
                fname = f.get("file_name", "")
                if not wheel_matches_platform(fname, platform_tag):
                    continue
                if sys.version_info.minor <= 12:
                    if python_tag in fname or 'none' in fname or 'abi3' in fname:
                        matching_whls.append(fname)
                else:
                    no_free_thread = sys._is_gil_enabled()
                    python_tag_t = f"{python_tag}t"
                    if no_free_thread:
                        if (python_tag in fname and python_tag_t not in fname) or 'none' in fname or 'abi3' in fname:
                            matching_whls.append(fname)
                    else:
                        major = sys.version_info.major
                        minor = sys.version_info.minor
                        python_tag_free_t = f"cp{major}{minor}t"
                        if python_tag_free_t in fname or 'none' in fname or 'abi3' in fname:
                            matching_whls.append(fname)



            if matching_whls:
                return True, matching_whls  # ✅ 找到匹配当前 Python 的 .whl

        # 下一页
        next_page = resp.headers.get("X-Next-Page")
        if next_page:
            page = int(next_page)
        else:
            page += 1

    return False, []


if __name__ == "__main__":
    found, filenames = has_whl_in_gitlab(
        package_name="lintrunner",
        version=None,
    )

    if found:
        print("✅ GitLab 上已有 .whl 包:", filenames)
    else:
        print("❌ 没有找到对应的 .whl 文件")
