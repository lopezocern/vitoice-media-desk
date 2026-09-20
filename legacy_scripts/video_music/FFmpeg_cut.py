import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


def parse_time_ranges(time_ranges_str):
    """
    解析时间区间字符串，返回时间区间列表。

    :param time_ranges_str: 时间区间字符串，格式为 "a-b c-d e-f ..."，其中 a、b、c、d、e、f 是时间点（格式为 HH:MM:SS）
    :return: 时间区间列表，每个元素是一个包含两个时间点的列表
    """
    time_range_pattern = re.compile(r'(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})')
    time_intervals = time_range_pattern.findall(time_ranges_str)

    if not time_intervals:
        raise ValueError(f"无效的时间区间格式: {time_ranges_str}")

    return [[start, end] for start, end in time_intervals]
def cut_video_webm(video_file, time_ranges, video_directory, video_output_directory):
    """
    切割单个视频的多个时间段。

    :param video_file: 视频文件
    :param time_ranges: 时间区间列表
    :param video_directory: 视频所在的目录
    :param video_output_directory: 输出视频所在目录
    :return: 无
    """
    video_name = video_file.stem
    print(f"开始处理视频: {video_name}")

    for i, (start_time, end_time) in enumerate(time_ranges, 1):
        output_video = Path(video_output_directory) / f"{video_name}_{i}.webm"  # 确保输出路径是 Path 对象
        print(f"开始切割 {video_name} 的时间段: {start_time} 到 {end_time}")

        try:
            result = subprocess.run([
                'ffmpeg',
                '-i', str(video_file),  # 输入文件
                '-ss', start_time,       # 开始时间
                '-to', end_time,         # 结束时间
                '-r', '30',              # 帧率
                '-c:v', 'libvpx',        # 使用 VP8 编码器
                '-c:a', 'libvorbis',     # 使用 Vorbis 音频编码器
                '-b:v', '2M',  # 设置视频比特率为 2 Mbps，增加清晰度
                '-crf', '18',            # 质量控制参数，数值越低质量越高
                '-b:a', '128k',          # 音频比特率
                '-cpu-used', '1',        # 编码速度与压缩比的平衡
                str(output_video)        # 输出文件
            ], check=True, capture_output=True, text=True, encoding='utf-8')  # 使用 utf-8 编码读取输出

            # 输出ffmpeg的stdout信息
            print(f"输出：{result.stdout}")
            print(f"已生成 {video_file.name} 的切割文件: {output_video}")
        except subprocess.CalledProcessError as e:
            print(f"切割 {video_file.name} 的时间段 {start_time}-{end_time} 失败: {e.stderr}")
        except Exception as e:
            print(f"发生错误: {str(e)}")

    print(f"{video_file.name} 所有时间段切割完成")

def cut_video(video_file, time_ranges, video_directory, video_output_directory):
    """
    切割单个视频的多个时间段。

    :param video_file: 视频文件
    :param time_ranges: 时间区间列表
    :param video_directory: 视频所在的目录
    :param video_output_directory: 输出视频所在目录
    :return: 无
    """
    video_name = video_file.stem
    print(f"开始处理视频: {video_name}")

    for i, (start_time, end_time) in enumerate(time_ranges, 1):
        output_video = Path(video_output_directory) / f"{video_name}_{i}.webm"  # 确保输出路径是 Path 对象
        print(f"开始切割 {video_name} 的时间段: {start_time} 到 {end_time}")

        try:
            result = subprocess.run([
                'ffmpeg',
                '-i', str(video_file),  # 输入文件
                '-ss', start_time,       # 开始时间
                '-to', end_time,         # 结束时间
                # 视频编码器：H.265/HEVC
                '-c:v', 'hevc_nvenc',
                # 音频编码器：AAC（不变）
                '-c:a', 'aac',
                # H.265 的 CRF 默认是 28，对应 H.264 的 23
                # 设 20-23 可获得很好画质，18 接近无损
                '-crf', '20',
                # 限制峰值码率（可选）
                '-maxrate', '2M',
                '-bufsize', '4M',
                # 音频码率
                '-b:a', '128k',
                # 像素格式
                '-pix_fmt', 'yuv420p',
                # 关键：Apple 设备兼容性（QuickTime/Safari/iOS 必须加）
                '-tag:v', 'hvc1',
                # 网络优化
                '-movflags', '+faststart',
                # 编码速度预设（slow 压缩率更高，medium 平衡）
                '-preset', 'medium',
                str(output_video)        # 输出文件
            ], check=True, capture_output=True, text=True, encoding='utf-8')  # 使用 utf-8 编码读取输出

            # 输出ffmpeg的stdout信息
            print(f"输出：{result.stdout}")
            print(f"已生成 {video_file.name} 的切割文件: {output_video}")
        except subprocess.CalledProcessError as e:
            print(f"切割 {video_file.name} 的时间段 {start_time}-{end_time} 失败: {e.stderr}")
        except Exception as e:
            print(f"发生错误: {str(e)}")

    print(f"{video_file.name} 所有时间段切割完成")


def cut_videos(video_directory, time_ranges_dict, video_output_directory):
    """
    根据给定的时间区间字典切割多个视频。

    :param video_directory: 视频文件目录
    :param time_ranges_dict: 一个字典，键为视频文件名，值为该视频的时间区间列表
    :param video_output_directory: 输出视频文件的目录
    :return: 无
    """
    base_path = Path(video_directory)
    if not base_path.exists():
        raise FileNotFoundError(f"目录不存在: {video_directory}")

    # 获取视频文件列表
    video_files = [base_path / video for video in time_ranges_dict.keys()]
    print(f"需要处理的视频文件: {video_files}")

    # 使用线程池加速切割任务
    with ThreadPoolExecutor() as executor:
        futures = []
        for video_file in video_files:
            video_name = video_file.name
            if video_name in time_ranges_dict:
                time_ranges = time_ranges_dict[video_name]
                futures.append(executor.submit(cut_video, video_file, time_ranges, base_path, video_output_directory))

        # 等待所有线程完成
        for future in futures:
            future.result()  # 阻塞直到任务完成

    print("所有切割任务完成")
from datetime import datetime, timedelta

def make_ranges(video_file: str, end_time: str, step_seconds: int = 10, fmt: str = "%H:%M:%S") -> dict:
    """
    生成 cut_videos 需要的 time_ranges_dict
    :param video_file: 视频文件名，如 "HJBB-181.mp4"
    :param end_time:   终点时间，如 "04:00:57"
    :param step_seconds: 每段多少秒
    :param fmt:        时间格式，默认 "%H:%M:%S"
    :return:           可直接丢给 cut_videos 的 dict
    """
    start = datetime.strptime("00:00:00", fmt)
    end   = datetime.strptime(end_time, fmt)

    ranges = []
    while start < end:
        seg_end = min(start + timedelta(seconds=step_seconds), end)
        ranges.append([start.strftime(fmt), seg_end.strftime(fmt)])
        start = seg_end

    return {video_file: ranges}

# 开始 扰 按 手 棒 后 换1 换2 换3 合格
# 示例用法
if __name__ == "__main__":

    # 批量10s 切割
    # end_time = "04:00:57"
    # time_ranges_dict = make_ranges("HJBB-181.mp4", end_time, 10)

    # 时间区间字典：键为视频文件名，值为该视频的时间区间列表
    time_ranges_dict = {
        "SAN-089.ts": [
            ["00:00:00", "00:52:27"],
            ["02:12:51", "02:58:36"],
            ],
    }
    # 视频文件目录
    video_directory = r"H:\NudeFileZilla\J-AV"
    video_output_directory = r"G:\A648-PC\A648-PC\assets\standalone_content\images\videos\new_tv\cut"

    # 执行切割
    cut_videos(video_directory, time_ranges_dict, video_directory)
