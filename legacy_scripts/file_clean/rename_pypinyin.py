# coding:utf-8
# @time: 2024/1/1 21:57
# @Author: guoxiao
# @File: rename
import os
from pypinyin import pinyin, Style

def rename_folders(parent_folder):
    # 获取父文件夹中的所有子文件夹
    subfolders = [f for f in os.listdir(parent_folder) if os.path.isdir(os.path.join(parent_folder, f))]

    # 遍历每个子文件夹
    for folder in subfolders:
        # 如果文件夹的第一个字符是英文，则跳过
        if not is_chinese(folder[0]):
            print(f"Skipped: {folder} (Already starts with an English letter)")
            continue

        # 获取子文件夹的中文拼音首字母
        pinyin_first_letter = get_pinyin_first_letter(folder)

        # 重命名子文件夹
        new_name = f"{pinyin_first_letter} {folder}"
        old_path = os.path.join(parent_folder, folder)
        new_path = os.path.join(parent_folder, new_name)
        os.rename(old_path, new_path)
        print(f"Renamed: {folder} -> {new_name}")

def get_pinyin_first_letter(text):
    # 使用 pypinyin 获取中文拼音首字母
    pinyin_result = pinyin(text, style=Style.FIRST_LETTER)
    return pinyin_result[0][0].upper() if pinyin_result else '#'

def is_chinese(char):
    # 判断字符是否是中文
    return '\u4e00' <= char <= '\u9fff'

# 指定父文件夹路径
# parent_folder_path = r"D:\NudeFileZilla\Deep Face"# 指明被遍历的文件夹
parent_folder_path = r"D:\NudeFileZilla\PPro\J"# 指明被遍历的文件夹
# parent_folder_path = r"D:\NudeFileZilla\浏览器采集\AI Picture"
# 调用函数进行重命名
rename_folders(parent_folder_path)
