import os
import shutil
from collections import defaultdict
import pypinyin


def organize_video_files(source_folder, base_target):
    """
    整理视频文件
    - source_folder: 源文件夹 (如 H:\\NudeFileZilla\\J-AV\\A)
    - base_target: 目标根目录 (如 H:\\NudeFileZilla\\J-AV)
    """

    # 支持的视频格式
    video_extensions = ['.mp4', '.avi', '.mkv', '.ts', '.webm', '.wmv']

    # 用于存储中文名字和对应的文件列表
    file_dict = defaultdict(list)

    print(f"源文件夹: {source_folder}")
    print(f"目标根目录: {base_target}")
    print("-" * 60)

    # 遍历源文件夹中的所有文件
    if not os.path.exists(source_folder):
        print(f"错误: 源文件夹不存在: {source_folder}")
        return

    for filename in os.listdir(source_folder):
        source_path = os.path.join(source_folder, filename)

        # 检查是否为文件
        if not os.path.isfile(source_path):
            continue

        # 检查文件扩展名
        if any(filename.lower().endswith(ext) for ext in video_extensions):
            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(filename)[0]

            # 提取中文名字
            chinese_name = extract_chinese_name(base_name)

            if chinese_name:
                # 获取首字母对应的文件夹
                folder_letter = get_pinyin_initial(chinese_name[0])

                # 存储文件信息
                file_dict[chinese_name].append({
                    'source': source_path,
                    'full_name': filename,
                    'folder_letter': folder_letter
                })
            else:
                print(f"警告: 无法提取中文名字: {filename}")

    print(f"共找到 {len(file_dict)} 个不同的中文名字")
    print("-" * 60)

    # 统计信息
    total_files = sum(len(files) for files in file_dict.values())
    print(f"总文件数: {total_files}")
    print("-" * 60)

    # 按文件夹分组显示统计
    folder_stats = defaultdict(int)
    for chinese_name, files in file_dict.items():
        for f in files:
            folder_stats[f['folder_letter']] += 1

    print("各文件夹文件统计:")
    for folder in sorted(folder_stats.keys()):
        print(f"  {folder}: {folder_stats[folder]} 个文件")
    print("-" * 60)

    # 实际移动文件
    multi_count = 0
    single_count = 0

    for chinese_name, files in file_dict.items():
        target_letter = files[0]['folder_letter']
        target_folder = os.path.join(base_target, target_letter)

        # 确保目标文件夹存在
        os.makedirs(target_folder, exist_ok=True)

        if len(files) > 1:
            # 多个文件，创建同名子文件夹
            multi_count += 1
            target_subfolder = os.path.join(target_folder, chinese_name)
            os.makedirs(target_subfolder, exist_ok=True)

            print(f"[多次] {chinese_name} -> {target_letter}/{chinese_name}/ ({len(files)}个文件)")

            for file_info in files:
                target_path = os.path.join(target_subfolder, file_info['full_name'])
                shutil.move(file_info['source'], target_path)
        else:
            # 单个文件，直接移动到目标文件夹
            single_count += 1
            target_path = os.path.join(target_folder, files[0]['full_name'])
            shutil.move(files[0]['source'], target_path)
            print(f"[单次] {files[0]['full_name']} -> {target_letter}/")

    print("-" * 60)
    print(f"完成!")
    print(f"  - 创建了 {multi_count} 个同名文件夹")
    print(f"  - 移动了 {single_count} 个单独文件")


def extract_chinese_name(filename):
    """从文件名中提取中文名字"""
    chinese_chars = ''
    for char in filename:
        # Unicode中中文的范围
        if '\u4e00' <= char <= '\u9fff':
            chinese_chars += char
    return chinese_chars


def get_pinyin_initial(char):
    """获取汉字的拼音首字母"""
    try:
        # 使用pypinyin获取拼音
        pinyin_list = pypinyin.pinyin(char, style=pypinyin.FIRST_LETTER)
        if pinyin_list and pinyin_list[0]:
            return pinyin_list[0][0].upper()
    except:
        pass

    # 如果无法获取拼音，默认返回A
    return 'A'


# 测试用 - 请修改为您的实际路径
if __name__ == '__main__':
    # 源文件夹（目前文件堆积的文件夹）
    source_folder = r"H:\NudeFileZilla\J-AV\A"

    # 目标根目录
    base_target = r"H:\NudeFileZilla\J-AV"

    # 先预览
    print("=== 预览模式 ===")
    # organize_video_files(source_folder, base_target)

    # 确认无误后，取消下面注释真正执行
    organize_video_files(source_folder, base_target)