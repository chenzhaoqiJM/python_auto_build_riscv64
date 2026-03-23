import requests
import json
from datetime import datetime, timedelta, timezone
import dateutil.parser  # 需要安装 python-dateutil 库

import configparser
import os

config = configparser.ConfigParser()

# 读取 pypirc.txt（你可以指定绝对路径）
current_dir = os.path.dirname(os.path.abspath(__file__))
pypirc_path = os.path.abspath(os.path.join(current_dir, "..", "pypirc.txt"))
config.read(pypirc_path)

# 获取 gitlab 的认证信息
gitlab_repo = config.get('gitlab', 'repository')
gitlab_pass = config.get('gitlab', 'password')

# 配置部分
GITLAB_API = gitlab_repo.rsplit('/', 1)[0]
PRIVATE_TOKEN = gitlab_pass  # ⚠️ 替换成你的 GitLab 访问令牌

HEADERS = {
    "PRIVATE-TOKEN": PRIVATE_TOKEN
}

days_range = [7, 30] # 7天内上传的包不要删除,超过30天不要删除

def get_package_detail(pkg_id):
    url = f"{GITLAB_API}/{pkg_id}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"❌ 获取包详情失败: ID={pkg_id}，状态码={resp.status_code}")
        return None

def get_packages():
    print("📦 正在获取包列表（支持自动分页）...")

    all_packages = []
    page = 1
    per_page = 100  # GitLab 最大支持 100

    while True:
        url = f"{GITLAB_API}?per_page={per_page}&page={page}"
        print(f"➡️ GET {url}")
        resp = requests.get(url, headers=HEADERS)
        print(f"⬅️ 状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"❌ 第 {page} 页请求失败: {resp.status_code}")
            print(f"🧾 错误内容: {resp.text}")
            break

        page_packages = resp.json()
        if not page_packages:
            print(f"✅ 所有包已获取完，共获取 {len(all_packages)} 个包")
            break

        print(f"📄 第 {page} 页，获取 {len(page_packages)} 个包")
        all_packages.extend(page_packages)

        # 打印本页内容
        for pkg in page_packages:
            # pkg_detail = get_package_detail(pkg["id"])
            # created_at = pkg_detail.get("created_at") if pkg_detail else "未知"
            # print(f" - ID: {pkg['id']}, name: {pkg['name']}, version: {pkg.get('version')}, 上传时间: {created_at}")
            print(f" - ID: {pkg['id']}, name: {pkg['name']}, version: {pkg.get('version')}")

        # 如果 GitLab 返回了 X-Next-Page，可以参考它；否则自己继续加页码
        next_page = resp.headers.get("X-Next-Page")
        if next_page:
            page = int(next_page)
        else:
            page += 1

    print(f"✅ 总共获取到 {len(all_packages)} 个包")
    return all_packages


def delete_package(pkg):
    url = f"{GITLAB_API}/{pkg['id']}"
    print(f"🗑️ 准备删除包: {pkg['name']} (版本: {pkg.get('version')}) -> ID: {pkg['id']}")
    print(f"➡️ DELETE {url}")
    
    resp = requests.delete(url, headers=HEADERS)
    print(f"⬅️ 状态码: {resp.status_code}")

    if resp.status_code == 204:
        print(f"✅ 删除成功: {pkg['name']} (ID: {pkg['id']})")
    else:
        print(f"❌ 删除失败: {pkg['name']} (ID: {pkg['id']})")
        print(f"🧾 返回内容: {resp.text}")


def get_package_files(pkg_id):
    url = f"{GITLAB_API}/{pkg_id}/package_files"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"⚠️ 获取包文件失败: ID={pkg_id} 状态码={resp.status_code}")
        return []

def should_skip_none_any(pkg):
    files = get_package_files(pkg["id"])
    for f in files:
        filename = f.get("file_name", "")
        if "none-any.whl" in filename:
            print(f"🚫 跳过 none-any.whl 包: {pkg['name']} ({filename})")
            return True
    return False

def main():
    # 读取要删除的包名列表
    try:
        with open("packages_to_delete.txt", "r") as f:
            to_delete = set(line.strip() for line in f if line.strip())
        print(f"📃 读取到 {len(to_delete)} 个待删除包名: {to_delete}")
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")
        return

    # 获取项目中已有的包
    packages = get_packages()

    # 当前时间
    now = datetime.now(timezone.utc)

    # 对比后进行删除
    matched = 0
    for pkg in packages:
        if pkg["name"] in to_delete:
            print(f"准备尝试删除：{pkg["name"]} ..........")
            
            # 跳过 none-any.whl 包
            if should_skip_none_any(pkg):
                continue
                
            # 获取包详情，含 created_at
            pkg_detail = get_package_detail(pkg["id"])
            if not pkg_detail:
                continue

            created_at_str = pkg_detail.get("created_at")
            if not created_at_str:
                print(f"⚠️ 包 {pkg['name']} 没有 created_at 字段，跳过")
                continue

            created_at = dateutil.parser.isoparse(created_at_str)
            age_days = (now - created_at).days

            print(f"📅 包 {pkg['name']} 上传于 {created_at}, 距今 {age_days} 天")

            if age_days <= days_range[0] or age_days >= days_range[1]:
                print(f"⏳ 跳过删除: {pkg['name']} (ID: {pkg['id']})，上传了 {age_days} 天")
                continue

            matched += 1
            delete_package(pkg)
    
    if matched == 0:
        print(f"⚠️ 没有找到任何匹配的包名（且上传时间早于{days_range}天前）")

if __name__ == "__main__":
    main()
