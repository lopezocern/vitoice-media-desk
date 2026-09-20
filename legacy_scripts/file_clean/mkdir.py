# coding:utf-8
# @time: 2023/12/26 0:04
# @Author: guoxiao
# @File: mkdir

import os
import re


def extract_prefix(file_name):
    # 使用正则表达式提取空格前的文字
    match = re.match(r'([^ ]+)[ ].*', file_name)
    if match:
        return match.group(1)
    else:
        return None


def main():
    directory = r'D:\NudeFileZilla\Deep Face'

    # 获取目录下全部文件的文件名
    file_names = os.listdir(directory)

    # 提取空格前的文字并去重
    prefixes = set()
    for file_name in file_names:
        prefix = extract_prefix(file_name)
        if prefix:
            prefixes.add(prefix)

    # 按照去重后的内容创建文件夹
    for prefix in prefixes:
        folder_path = os.path.join(directory, prefix)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f'文件夹 "{prefix}" 创建成功！')


if __name__ == "__main__":
    main()
