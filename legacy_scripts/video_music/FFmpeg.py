# coding:utf-8
# @time: 2023/11/18 1:20
# @Author: guoxiao
# @File: v_m
import os
import subprocess, time
from prettytable import PrettyTable

def compress_video(input_file, output_file):
    # 记录开始时间
    start_time = time.time()
    print(f'开始压缩 {input_file}')

    # 使用FFmpeg进行压缩
    ffmpeg_cmd = [
        'ffmpeg',  # FFmpeg 命令本身
        # '-hwaccel', 'cuvid',  # 使用 cuvid 加速器
        '-i', input_file,  # 输入文件路径
        '-c:v', 'hevc_nvenc', # 使用 NVIDIA GPU 加速的 H.264 编码器 hevc_nvenc h264_nvenc
        # '-c:v', 'libx264',  # 视频编码器，使用 H.264
        '-crf', '18',  # 压缩率因子，影响视频质量（数值越小，质量越好，范围一般为0-51）
        '-preset', 'p6',
            # 编码速度和压缩效率的预设，可选值包括 ultrafast、superfast、veryfast、faster、fast、medium、slow、slower、veryslow。预设越慢，压缩效率越高，但速度越慢。
            # hevc_nvenc 使用的是 GPU硬件编码，支持的预设值如：p1 (最快) 到 p7 (最慢)，或 fast、medium、slow 等
        '-profile:v', 'main',  # 视频编码的配置文件，高级别的配置可以提供更好的质量，这里设置为高级别。
        # '-vf', 'scale=1920:1080',  # 强制输出为1920x1080分辨率
        '-b:v', '1M',  # 视频比特率，可根据需要调整 2M
        '-c:a', 'aac',  # 音频编码器，使用 AAC
        '-b:a', '128k',  # 音频比特率，128 kbps（音频码率）
        '-strict', '-2',  # 使用标准的 AAC 编码器，解决 AAC 编码时出现的错误提示
        '-movflags', '+faststart',  # 在媒体文件的 moov atom 放在文件的前面，可使视频文件流式传输时开始播放更快。
        output_file+'.mp4'  # 输出文件路径
    ]
    x = [
        'ffmpeg',
        '-i', input_file,  # 输入文件路径
        '-c:v', 'hevc_nvenc',  # 视频编码器：NVIDIA','HEVC硬件编码
        '-preset', 'p6',  # 编码预设：最慢/最高质量 NVENC预设，p1最快/p7最慢质量最好
        '-tune', 'hq',  # 调优模式：高质量 调优模式：hq=高质量（可选ll=低延迟/lossless=无损）
        '-profile:v', 'main',  # 编码档次：10bit','Main main10
        '-pix_fmt', 'p010le',      # 像素格式：10bit', 'YUV', '4:2:0
        '-rc', 'vbr',      # 码率控制：可变码率
        '-cq', '24',      # 恒定质量值：24（平衡质量与大小）
        '-qmin', '20',
        '-qmax', '28',  # 质量范围限制
        '-g', '250',  # GOP大小：250帧（约4秒）
        '-bf', '4',     # B帧数量：4帧
        '-b_ref_mode', 'middle',  # B帧参考模式：中间参考
        '-c:a', 'copy',     #音频：直接复制，不重新编码
        '-movflags', '+faststart',      # 容器优化：网络播放优化
        output_file+'.mp4'  # 输出文件路径
    ]
    # 调用FFmpeg命令
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print("压缩完成")
    except subprocess.CalledProcessError as e:
        print("压缩失败:", e)

    # 记录结束时间
    end_time = time.time()

    # 计算执行时间
    execution_time = end_time - start_time
    print("执行时间：", execution_time, "秒")

def compress_all_mp4(folder_path):
    # 记录开始时间
    start_time = time.time()
    # 初始化一个列表来存储每个视频的运行时间
    video_times = []
    # 开始执行视频压缩
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.ts', '.m4v', '.avi', '.wmv', '.mkv', '.webm'))]
    print(image_files)
    for i in range(len(image_files)):
        filename = image_files[i]
        print(str(filename))
        if 'reb' in str(filename):
            video_time = 0
            video_times.append(video_time)
            pass
        else:
            input_file = fr'{folder_path}\{filename}'  # 输入视频文件路径
            out_filename = fr'{image_files[i]}_reb'
            output_file = fr'{folder_path}\{out_filename}'  # 输入视频文件路径
            # 记录开始时间
            start_time_video = time.time()
            # 调用压缩函数
            compress_video(input_file, output_file)
            # 记录结束时间
            end_time_video = time.time()
            # 计算运行时间
            video_time = end_time_video - start_time_video
            video_times.append(video_time)
    # 记录结束时间
    end_time = time.time()
    # 计算执行时间
    execution_time = end_time - start_time
    # 使用prettytable创建一个表格来展示每个视频的运行时间
    pt = PrettyTable()
    pt.field_names = ['Video', 'Compression Time (HH:MM:SS)']
    for i in range(len(image_files)):
        filename = image_files[i]
        video_time_str = time.strftime("%H:%M:%S", time.gmtime(video_times[i]))
        pt.add_row([f"Video {i + 1}: {filename}", video_time_str])
    execution_time_str = time.strftime("%H:%M:%S", time.gmtime(execution_time))
    pt.add_row([f"Total Compression Time: {execution_time:.2f} seconds", execution_time_str])
    print(pt)

folder_path = r'H:\NFZ\DeepFace\temp'
# folder_path = fr'H:/NudeFileZilla/ff/tvshow'
compress_all_mp4(folder_path)
