import requests
import sys
from datetime import datetime, timedelta

# 获取传入的包名参数
if len(sys.argv) < 2:
    print("Usage: python 00get_pkg_version.py <package_name>")
    sys.exit(1)

package_name = sys.argv[1]

# 计算2年前的日期
two_years_ago = datetime.now() - timedelta(days=365)

# 访问 PyPI API 获取包的版本数据
url = f"https://pypi.org/pypi/{package_name}/json"
response = requests.get(url)

# 检查请求是否成功
if response.status_code != 200:
    print(f"Error: Failed to fetch data for package {package_name}")
    sys.exit(1)

data = response.json()

# 获取版本和发布日期
releases = data['releases']
recent_versions = set()  # 使用 set 去除重复版本

for version, release_info in releases.items():
    for release in release_info:
        # 获取发布日期并转换为 datetime 对象
        release_date = release['upload_time']
        release_datetime = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S')
        
        # 如果发布日期在2年内，则加入 set
        if release_datetime > two_years_ago:
            recent_versions.add(version)

# 将版本按降序排序并输出到文件
sorted_versions = sorted(recent_versions, reverse=True)
file_name = f"{package_name}.log"
with open(file_name, 'w') as f:
    for version in sorted_versions:
        f.write(f"{version}\n")

print(f"Versions for {package_name} have been written to {file_name}")
