#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta


def parse_time_ranges(time_ranges_str):
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})')
    intervals = pattern.findall(time_ranges_str)
    if not intervals:
        raise ValueError(f"无效时间区间: {time_ranges_str}")
    return [[s, e] for s, e in intervals]


def make_ranges(video_file: str,
                start: str,
                end_time: str,
                step_seconds: int = 10,
                fmt: str = "%H:%M:%S") -> dict:
    start = datetime.strptime(start, fmt)
    end   = datetime.strptime(end_time, fmt)
    ranges = []
    while start < end:
        seg_end = min(start + timedelta(seconds=step_seconds), end)
        ranges.append([start.strftime(fmt), seg_end.strftime(fmt)])
        start = seg_end
    return {video_file: ranges}


def cut_video(video_file: Path, time_ranges, _video_dir, out_dir, use_gpu=False):
    name = video_file.stem
    print(f"开始处理: {name}")

    for idx, (start, end) in enumerate(time_ranges, 1):
        out_file = Path(out_dir) / f"{name}_{idx}.mp4"
        duration = (datetime.strptime(end, "%H:%M:%S") - datetime.strptime(start, "%H:%M:%S")).seconds

        if use_gpu:
            # 使用 GPU 加速（Nvidia NVENC）
            cmd = [
                'ffmpeg',
                '-ss', start,
                '-i', str(video_file),
                '-t', str(duration),
                '-c:v', 'h264_nvenc',
                '-preset', 'medium', #'fast',     # h264_nvenc 支持的预设
                '-cq', '26',           # NVENC 控制质量（类似 crf）
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y', str(out_file)
            ]
        else:
            # 使用 CPU 软件编码
            cmd = [
                'ffmpeg',
                '-ss', start,
                '-i', str(video_file),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'superfast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y', str(out_file)
            ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            print(f"完成: {out_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"失败: {out_file.name} | {e.stderr}")

    print(f"{name} 全部段完成")


def cut_videos(video_directory, time_ranges_dict, video_output_directory, use_gpu=False):
    src = Path(video_directory)
    if not src.exists():
        raise FileNotFoundError(f"目录不存在: {video_directory}")

    Path(video_output_directory).mkdir(parents=True, exist_ok=True)

    args = [
        (src / vid_name, ranges, video_directory, video_output_directory, use_gpu)
        for vid_name, ranges in time_ranges_dict.items()
    ]

    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(cut_video, *arg) for arg in args]
        for f in futures:
            f.result()

    print("所有切割任务完成")


if __name__ == "__main__":
    start_time = "00:00:00"
    end_time = "01:31:08"
    time_ranges_dict = make_ranges("SGKI-048.mp4", start_time, end_time, 11)
    #
    video_directory       = r"H:\NudeFileZilla\J-AV\# 单体\电视台"
    video_output_directory = r"H:\NudeFileZilla\J-AV\# 单体\电视台"

    # 设置 use_gpu=True 使用 Nvidia GPU 加速，否则用 CPU 编码
    cut_videos(video_directory, time_ranges_dict, video_output_directory, use_gpu=True)
