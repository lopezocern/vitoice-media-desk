# coding:utf-8
# @time: 2023/11/18 1:20
# @Author: guoxiao
# @File: v_m
import os
import subprocess
import time
from prettytable import PrettyTable


def check_hardware_acceleration():
    """检查可用的硬件加速选项"""
    try:
        # 检查NVIDIA GPU是否可用
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'hevc_nvenc' in result.stdout:
            print("✅ 检测到NVIDIA GPU硬件加速 (hevc_nvenc)")
            return 'hevc_nvenc'
        elif 'h264_nvenc' in result.stdout:
            print("✅ 检测到NVIDIA GPU硬件加速 (h264_nvenc)")
            return 'h264_nvenc'
        else:
            print("⚠️ 未检测到NVIDIA GPU硬件加速，将使用软件编码")
            return 'libx265'
    except Exception as e:
        print(f"❌ 检查硬件加速时出错: {e}")
        return 'libx265'


def compress_video(input_file, output_file, speed_mode='balanced'):
    """压缩视频文件，支持不同速度模式和硬件加速
    
    Args:
        input_file: 输入视频文件路径
        output_file: 输出视频文件路径
        speed_mode: 速度模式，可选 'balanced', 'fast', 'ultrafast'
    
    Returns:
        float: 压缩执行时间（秒）
    """
    # 记录开始时间
    start_time = time.time()
    
    # 检查硬件加速
    encoder = check_hardware_acceleration()
    
    # 根据速度模式设置参数
    if speed_mode == 'fast':
        preset = 'fast'
        crf = 26  # 稍微提高质量以补偿快速编码
        video_bitrate = '2.5M'
        threads = '0'  # 自动线程数
        print("  使用快速模式: 编码速度优先")
    elif speed_mode == 'ultrafast':
        preset = 'ultrafast'
        crf = 28  # 更高质量以补偿超快编码
        video_bitrate = '3M'  # 更高比特率以保持质量
        threads = '0'  # 自动线程数
        print("  使用超快模式: 最大编码速度")
    else:  # balanced (默认)
        preset = 'medium'
        crf = 24  # 平衡的质量设置
        video_bitrate = '2M'
        threads = '0'  # 自动线程数
        print("  使用平衡模式: 速度与质量平衡")
    
    # 根据编码器类型调整命令
    if encoder in ['hevc_nvenc', 'h264_nvenc']:
        # NVIDIA硬件加速编码器
        if encoder == 'hevc_nvenc':
            codec = 'hevc_nvenc'
            print(f"  使用NVIDIA HEVC硬件加速编码器")
        else:
            codec = 'h264_nvenc'
            print(f"  使用NVIDIA H.264硬件加速编码器")
        
        # NVENC编码器使用不同的参数
        command = [
            'ffmpeg', '-i', input_file, '-c:v', codec,
            '-preset', 'p1',  # NVENC的preset，p1是最快的
            '-tune', 'ull',   # 超低延迟
            '-rc', 'vbr',     # 可变比特率
            '-b:v', video_bitrate,
            '-maxrate', video_bitrate,
            '-bufsize', str(int(video_bitrate[:-1]) * 2) + 'M',
            '-c:a', 'copy',   # 直接复制音频流
            '-movflags', '+faststart',
            '-y', output_file
        ]
    else:
        # 软件编码
        print(f"  使用软件编码器: {encoder}")
        command = [
            'ffmpeg', '-i', input_file, '-c:v', encoder,
            '-preset', preset,
            '-crf', str(crf),
            '-b:v', video_bitrate,
            '-threads', threads,
            '-c:a', 'copy',   # 直接复制音频流
            '-movflags', '+faststart',
            '-y', output_file
        ]
    
    # 显示文件大小信息
    if os.path.exists(input_file):
        file_size = os.path.getsize(input_file) / (1024 * 1024 * 1024)  # GB
        print(f"  输入文件大小: {file_size:.2f} GB")
    
    # 执行压缩命令
    print(f"  开始压缩...")
    subprocess.run(command, check=True)
    
    # 显示输出文件大小
    if os.path.exists(output_file):
        output_size = os.path.getsize(output_file) / (1024 * 1024 * 1024)  # GB
        print(f"  输出文件大小: {output_size:.2f} GB")
        
        # 计算压缩率
        if file_size > 0:
            compression_ratio = (1 - output_size / file_size) * 100
            print(f"  压缩率: {compression_ratio:.1f}%")
    
    # 记录结束时间
    end_time = time.time()
    # 计算执行时间
    execution_time = end_time - start_time
    print(f"  压缩完成，耗时: {execution_time:.2f} 秒")
    
    return execution_time


def compress_all_mp4(folder_path, speed_mode='balanced'):
    # 记录开始时间
    start_time = time.time()
    # 初始化一个列表来存储每个视频的运行时间
    video_times = []
    # 开始执行视频压缩
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.ts', '.m4v', '.avi', '.wmv', '.mkv', '.webm'))]
    print(f"找到 {len(image_files)} 个视频文件")
    print(f"速度模式: {speed_mode}")
    
    # 检查文件大小，对大文件使用更快的模式
    large_files = []
    for filename in image_files:
        if 'reb' in str(filename):
            continue
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024 * 1024)  # GB
            if file_size > 3:  # 大于3GB的文件
                large_files.append(filename)
    
    if large_files:
        print(f"检测到 {len(large_files)} 个大文件(>3GB): {', '.join(large_files[:5])}{'...' if len(large_files) > 5 else ''}")
        if speed_mode == 'balanced':
            print("建议对大文件使用 'fast' 模式以获得更好的性能")
    
    for i in range(len(image_files)):
        filename = image_files[i]
        print(f"处理文件 {i+1}/{len(image_files)}: {filename}")
        if 'reb' in str(filename):
            video_time = 0
            video_times.append(video_time)
            pass
        else:
            input_file = fr'{folder_path}\{filename}'  # 输入视频文件路径
            out_filename = fr'{image_files[i]}_reb'
            output_file = fr'{folder_path}\{out_filename}'  # 输入视频文件路径
            
            # 对大文件使用更快的模式
            current_speed_mode = speed_mode
            file_path = os.path.join(folder_path, filename)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024 * 1024)  # GB
                if file_size > 3 and speed_mode == 'balanced':
                    current_speed_mode = 'fast'
                    print(f"  大文件({file_size:.2f}GB)，自动使用快速模式")
            
            # 记录开始时间
            start_time_video = time.time()
            # 调用压缩函数
            video_time = compress_video(input_file, output_file, current_speed_mode)
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
    
    # 计算提速效果
    if execution_time > 0:
        total_size = sum(os.path.getsize(os.path.join(folder_path, f)) / (1024 * 1024 * 1024) 
                         for f in image_files if 'reb' not in f and os.path.exists(os.path.join(folder_path, f)))
        if total_size > 0:
            avg_time_per_gb = execution_time / total_size
            print(f"平均每GB处理时间: {avg_time_per_gb:.2f} 秒")
            
            # 与原始slow模式比较
            original_time = execution_time * 2.5  # 估算原始slow模式的时间
            print(f"估算原始slow模式时间: {time.strftime('%H:%M:%S', time.gmtime(original_time))}")
            print(f"提速约: {((original_time - execution_time) / original_time * 100):.1f}%")


def print_usage_examples():
    """打印使用示例"""
    print("\n" + "="*60)
    print("使用示例:")
    print("="*60)
    print("\n1. 平衡模式 (默认，速度和质量平衡):")
    print("   compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'balanced')")
    print("\n2. 快速模式 (速度优先，质量略有降低):")
    print("   compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'fast')")
    print("\n3. 超快模式 (最大速度，质量进一步降低):")
    print("   compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'ultrafast')")
    print("\n4. 单个文件压缩:")
    print("   compress_video(r'H:/NudeFileZilla/ff/tvshow/video.mp4', r'H:/NudeFileZilla/ff/tvshow/video_reb', 'fast')")
    print("\n" + "="*60)


# 在主程序开始前添加硬件加速检查
if __name__ == "__main__":
    print("="*60)
    print("视频压缩工具 - 优化版")
    print("="*60)
    
    # 检查硬件加速
    encoder = check_hardware_acceleration()
    
    # 打印使用示例
    print_usage_examples()
    
    # 原始代码
    folder_path = fr'H:\NudeFileZilla\PPro\J-AV\未命名文件夹'
    # folder_path = fr'H:/NudeFileZilla/ff/tvshow'
    compress_all_mp4(folder_path, 'balanced')  # 默认使用平衡模式