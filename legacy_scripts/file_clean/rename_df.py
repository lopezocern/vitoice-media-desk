import os
import re

# 设置您要处理的目录
# rootdir = r"H:/NudeFileZilla/Deep Face/A temp"
rootdir = r"H:\NudeFileZilla\浏览器采集\AI Picture"

def remove_leading_numbers(filename):
    # 正则表达式匹配以一位或两位数字开头，后面跟着'_99'或'-99'的模式
    # pattern = re.compile(r'^(\d{1,2}[-_]\d{1,2})')
    pattern = re.compile(r'Group(\d{1,3}\d{1,3}\d{1,3})_')
    # 使用正则表达式替换匹配到的字符串为空
    new_filename = re.sub(pattern, '', filename)
    return new_filename

for parent, dirnames, filenames in os.walk(rootdir):
    for filename in filenames:
        # 获取新的文件名
        new_filename = remove_leading_numbers(filename)
        # 构建完整的文件路径
        old_file = os.path.join(parent, filename)
        new_file = os.path.join(parent, new_filename)
        # 重命名文件
        try:
            os.rename(old_file, new_file)
            print(f"Renamed '{old_file}' to '{new_file}'")
        except OSError as e:
            print(f"Error: {e.strerror}. Cannot rename '{old_file}' to '{new_file}'")
