import csv

input_file = "top-pypi-packages.csv"
output_file = "top_pypi_package_names.txt"

with open(input_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    package_names = [row["project"] for row in reader]

with open(output_file, "w", encoding="utf-8") as f:
    for name in package_names:
        f.write(name + "\n")

print(f"✅ 已写入 {len(package_names)} 个包名到 {output_file}")
