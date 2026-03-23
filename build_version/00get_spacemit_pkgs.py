import requests
from bs4 import BeautifulSoup

# 设置 PyPI 源 URL
pypi_url = "https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple"

# 发起请求获取包列表页面
response = requests.get(pypi_url)
if response.status_code == 200:
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 获取所有包名称并去重
    packages = set(a.text for a in soup.find_all('a'))

    # 保存包名称到文本文件
    with open("packages.log", 'w') as file:
        for package in sorted(packages):  # 按字母排序（可选）
            file.write(f"{package}\n")
else:
    print(f"请求失败，状态码：{response.status_code}")
