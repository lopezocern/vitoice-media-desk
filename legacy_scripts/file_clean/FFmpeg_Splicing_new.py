# coding:utf-8
import re
import subprocess
from collections import defaultdict
import time
from pathlib import Path
from natsort import natsorted


def auto_concatenate_videos(folder_path, output_name=None):
    base_path = Path(folder_path)
    if not base_path.exists():
        raise FileNotFoundError(f"目录不存在: {folder_path}")

    # 获取所有视频文件并打印数量
    video_files = list(base_path.glob("*.mp4"))
    print(f"扫描到 {len(video_files)} 个MP4文件")  # 新增调试输出

    file_groups = detect_file_sequences(video_files)
    print(f"发现 {len(file_groups)} 个有效文件序列")  # 新增调试输出

    if not file_groups:
        print("提示: 没有检测到可拼接的文件序列")
        return

    # 对每个分组进行拼接
    for group_key, group_info in file_groups.items():
        group_prefix = group_info['prefix']
        group_files = group_info['files']
        if len(group_files) < 2:
            print(f"跳过分组 {group_prefix}: 文件数量不足")
            continue

        # 创建ffconcat文件
        concat_file_path = base_path / f"{group_prefix}_concat.ffconcat"
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for file in natsorted(group_files):
                f.write(f"file '{file.relative_to(base_path)}'\n")

        # 使用ffmpeg进行拼接
        output_file_name = f"{group_prefix}_concat.mp4" if not output_name else output_name
        output_file_path = base_path / output_file_name

        try:
            start_time = time.perf_counter()
            print(f"开始拼接分组 {group_prefix}...")
            subprocess.run(
                [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file_path,
                    '-c', 'copy',
                    '-map', '0',
                    output_file_path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            end_time = time.perf_counter()
            print(f"分组 {group_prefix} 拼接完成，耗时: {end_time - start_time:.2f}秒")
            print(f"输出文件: {output_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"拼接分组 {group_prefix} 失败: {e.stderr.decode('utf-8')}")
        finally:
            concat_file_path.unlink()  # 删除临时ffconcat文件

        print()  # 分隔不同分组的输出


def detect_file_sequences(files):
    pattern = re.compile(r"""
        ^(.*?)                  # 基础前缀
        ([_-]?\s*(?:Part|CPart)?\s*)  # 增强分隔符匹配
        (\d{3,})                # 连续数字编号
        $""", re.VERBOSE | re.IGNORECASE)

    sequences = defaultdict(lambda: {'prefix': None, 'numbers': [], 'files': []})

    for file in files:
        stem = file.stem
        match = pattern.match(stem)
        if match:
            base_prefix = match.group(1).rstrip("_- ")
            separator = match.group(2).strip()
            number = int(match.group(3))
            normalized_prefix = f"{base_prefix}{separator}"
            key = (normalized_prefix, file.suffix)

            sequences[key]['prefix'] = normalized_prefix
            sequences[key]['numbers'].append(number)
            sequences[key]['files'].append(file)
            print(f"匹配成功: {file.name} → 前缀: {normalized_prefix} 编号: {number}")  # 新增匹配日志
        else:
            print(f"未匹配: {file.name}")  # 新增未匹配日志

    # 其余代码保持不变...

    return sequences


# 在main部分添加执行提示
if __name__ == "__main__":
    video_folder = r"H:\NudeFileZilla\PPro\J-AV\未命名文件夹"
    print(f"开始处理目录: {video_folder}")  # 新增开始提示

    try:
        start_time = time.perf_counter()
        auto_concatenate_videos(video_folder)
        print(f"总耗时：{time.perf_counter() - start_time:.2f}秒")
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        print("处理完成")  # 新增结束提示