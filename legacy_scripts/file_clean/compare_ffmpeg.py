import subprocess
import pandas as pd
import os


def get_video_info(video_path):
    """获取视频的详细信息"""
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,bit_rate,width,height,codec_long_name,profile,PIXEL_ASPECT_RATIO,r_frame_rate,duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        video_output = result.stdout.decode('utf-8').split('\n')

        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_name,bit_rate,sample_rate,channels',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        audio_output = result.stdout.decode('utf-8').split('\n')

        def safe_int(value):
            """尝试将值转换为整数，如果失败返回原始值"""
            try:
                return int(value)
            except ValueError:
                return value.strip() if value else 'N/A'

        video_info = {
            'video_codec_name': video_output[0].strip(),
            'video_bit_rate': safe_int(video_output[1].strip()),  # 使用 safe_int 函数处理 bit_rate
            'width': video_output[2].strip(),
            'height': video_output[3].strip(),
            'video_codec_long_name': video_output[4].strip(),
            'video_profile': video_output[5].strip(),
            'pixel_aspect_ratio': video_output[6].strip(),
            'frame_rate': video_output[7].strip(),
            'duration': float(video_output[8].strip()) if video_output[8].strip() else 0.0,
            'audio_codec_name': audio_output[0].strip() if audio_output[0] else 'N/A',
            'audio_bit_rate': safe_int(audio_output[1].strip()) if len(audio_output) > 1 else 'N/A',
            'audio_sample_rate': safe_int(audio_output[2].strip()) if len(audio_output) > 2 else 'N/A',
            'audio_channels': audio_output[3].strip() if len(audio_output) > 3 else 'N/A',
        }
        return video_info
    except subprocess.CalledProcessError as e:
        print(f"获取视频信息失败: {e.stderr.decode()}")
        return None
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None


def format_duration(duration):
    """将时长转换为 HH:MM:SS 格式"""
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def compare_videos(video1_path, video2_path):
    """比较两个视频并输出对比表格"""
    video1_info = get_video_info(video1_path)
    video2_info = get_video_info(video2_path)

    if not video1_info or not video2_info:
        print("无法获取一个或两个视频的信息")
        return

    # 格式化时长为 HH:MM:SS
    video1_info['duration'] = format_duration(video1_info['duration'])
    video2_info['duration'] = format_duration(video2_info['duration'])

    # 创建对比数据
    data = {
        '属性': [
            '视频编码格式 (codec_name)',
            '视频比特率 (bit_rate)',
            '宽度 (width)',
            '高度 (height)',
            '视频完整编码名称 (codec_long_name)',
            '视频编码配置文件 (profile)',
            '像素宽高比 (PIXEL_ASPECT_RATIO)',
            '帧率 (frame_rate)',
            '时长 (duration)',
            '音频编码格式 (codec_name)',
            '音频比特率 (bit_rate)',
            '音频采样率 (sample_rate)',
            '音频通道数 (channels)'
        ],
        '视频1': [
            video1_info['video_codec_name'],
            f"{video1_info['video_bit_rate'] if isinstance(video1_info['video_bit_rate'], str) else '{:,}'.format(video1_info['video_bit_rate'])}",
            video1_info['width'],
            video1_info['height'],
            video1_info['video_codec_long_name'],
            video1_info['video_profile'],
            video1_info['pixel_aspect_ratio'],
            video1_info['frame_rate'],
            video1_info['duration'],
            video1_info['audio_codec_name'],
            f"{video1_info['audio_bit_rate'] if isinstance(video1_info['audio_bit_rate'], str) else '{:,}'.format(video1_info['audio_bit_rate'])}",
            video1_info['audio_sample_rate'],
            video1_info['audio_channels']
        ],
        '视频2': [
            video2_info['video_codec_name'],
            f"{video2_info['video_bit_rate'] if isinstance(video2_info['video_bit_rate'], str) else '{:,}'.format(video2_info['video_bit_rate'])}",
            video2_info['width'],
            video2_info['height'],
            video2_info['video_codec_long_name'],
            video2_info['video_profile'],
            video2_info['pixel_aspect_ratio'],
            video2_info['frame_rate'],
            video2_info['duration'],
            video2_info['audio_codec_name'],
            f"{video2_info['audio_bit_rate'] if isinstance(video2_info['audio_bit_rate'], str) else '{:,}'.format(video2_info['audio_bit_rate'])}",
            video2_info['audio_sample_rate'],
            video2_info['audio_channels']
        ]
    }

    # 创建 DataFrame 并设置列格式
    df = pd.DataFrame(data)

    # 设置 Pandas 表格的显示选项
    pd.set_option('display.colheader_justify', 'center')  # 表头居中
    pd.set_option('display.width', 1000)  # 控制表格的宽度，避免自动换行
    pd.set_option('display.max_columns', None)  # 显示所有列
    pd.set_option('display.max_rows', None)  # 显示所有行
    pd.set_option('display.max_colwidth', 50)  # 限制列宽，避免长字段影响显示

    print(df)

# 示例用法
if __name__ == "__main__":
    video1 = r"H:\NudeFileZilla\SONE-187-C.mp4"
    video2 = r"H:\NudeFileZilla\J-AV\S\BF-687-森日向子.mp4"

    compare_videos(video1, video2)
