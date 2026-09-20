#!/usr/bin/env python3
"""
QSP4 专用 WebM 转码器 - 深度优化版
"""
import subprocess, multiprocessing, shutil, sys, time, datetime
from pathlib import Path
from tqdm import tqdm

# ===== 用户配置 =====
INPUT_DIR = Path(r'G:\A648-PC\A648-PC\assets\standalone_content\images\videos\new_tv\nightshow')
OUTPUT_DIR = Path(r'G:\A648-PC\A648-PC\assets\standalone_content\images\videos\new_tv\cut')
# ====================

GREEN, RED, RESET = '\033[92m', '\033[91m', '\033[0m'


def get_qsp4_compatible_webm_cmd(src: Path, dst: Path):
    """QSP4 专用 WebM 编码参数 - 深度兼容"""
    return [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', str(src),

        # 视频处理 - 确保标准分辨率
        '-vf', 'scale=1920:1080:flags=lanczos,format=yuv420p',

        # VP8 编码基础参数 - 最大兼容性
        '-c:v', 'libvpx',
        '-b:v', '1M',  # 保守码率
        '-minrate', '500k',
        '-maxrate', '1.5M',
        '-bufsize', '2M',

        # 关键帧设置 - QSP4 播放关键
        '-g', '30',  # 每1秒一个关键帧
        '-keyint_min', '15',  # 最小关键帧间隔

        # 编码质量设置
        '-quality', 'best',  # 最佳质量
        '-cpu-used', '0',  # 最慢但质量最好
        '-qmin', '4',
        '-qmax', '40',
        '-threads', '2',  # 减少线程避免问题

        # 移除可能引起兼容性问题的参数
        # 不使用 -auto-alt-ref, -row-mt 等高级特性

        # 音频设置 - 最兼容配置
        '-c:a', 'libvorbis',
        '-b:a', '64k',  # 更低比特率
        '-ac', '1',  # 单声道
        '-ar', '22050',  # 标准采样率

        # 输出格式设置
        '-f', 'webm',
        '-r', '30',  # 保持原帧率或使用30fps

        # 确保输出文件规范
        '-avoid_negative_ts', 'make_zero',
        '-fflags', '+genpts',

        '-y', str(dst)
    ]


def get_qsp4_minimal_webm_cmd(src: Path, dst: Path):
    """QSP4 最小化WebM编码 - 最大兼容性"""
    return [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', str(src),

        # 最简视频处理
        '-vf', 'scale=640:360:flags=lanczos,format=yuv420p',

        # 最简编码参数
        '-c:v', 'libvpx',
        '-b:v', '500k',
        '-g', '30',

        # 最简音频
        '-c:a', 'libvorbis',
        '-b:a', '64k',
        '-ac', '1',

        # 基础输出
        '-f', 'webm',
        '-r', '30',

        '-y', str(dst)
    ]


def transcode_comprehensive(args):
    """综合转码 - 尝试多种方案"""
    idx, total, video_path = args

    # 方案1: 标准QSP4兼容
    webm_path1 = OUTPUT_DIR / video_path.with_suffix('.qsp4.webm').name
    # 方案2: 最小化兼容
    webm_path2 = OUTPUT_DIR / video_path.with_suffix('.min.webm').name

    # 尝试方案1
    if not webm_path1.exists():
        try:
            subprocess.run(
                get_qsp4_compatible_webm_cmd(video_path, webm_path1),
                check=True,
                capture_output=True,
                timeout=300
            )
            return idx, "success", video_path.name, "标准WebM"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            # 方案1失败，尝试方案2
            try:
                subprocess.run(
                    get_qsp4_minimal_webm_cmd(video_path, webm_path2),
                    check=True,
                    capture_output=True,
                    timeout=300
                )
                return idx, "success", video_path.name, "最小WebM"
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e2:
                return idx, "fail", video_path.name, f"全部失败: {str(e2)[:100]}"
    else:
        return idx, "skip", video_path.name, "已存在"


def check_webm_file(webm_path):
    """检查WebM文件是否有效"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,width,height,r_frame_rate',
            '-of', 'csv=p=0',
            str(webm_path)
        ], capture_output=True, text=True, check=True)

        info = result.stdout.strip().split(',')
        if len(info) >= 4 and info[0] == 'vp8':
            return True, f"VP8 {info[1]}x{info[2]} {info[3]}"
        else:
            return False, "非VP8编码"
    except:
        return False, "检查失败"


def main():
    if not shutil.which('ffmpeg'):
        sys.exit('错误: FFmpeg 未安装或未加入 PATH')

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 查找视频文件
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.flv']
    video_list = []
    for ext in video_extensions:
        video_list.extend(INPUT_DIR.glob(ext))

    if not video_list:
        sys.exit(f'{INPUT_DIR} 下未找到视频文件')

    total = len(video_list)
    print(f"发现 {total} 个视频文件")
    print("QSP4 WebM 转码选项:")
    print("1. 标准兼容模式 (1920x1080, 1M码率)")
    print("2. 最小兼容模式 (640x360, 500k码率)")
    print("3. 智能模式 (先尝试标准，失败则用最小)")

    choice = input("请选择 [1-3]: ").strip()

    start_t = time.time()
    success_count = 0
    fail_count = 0

    with multiprocessing.Pool(2) as pool, \
            tqdm(total=total, unit='file', desc='转码进度') as pbar:

        if choice == "1":
            # 标准模式
            for idx, video_path in enumerate(video_list):
                webm_path = OUTPUT_DIR / video_path.with_suffix('.webm').name
                pbar.set_description(f"处理: {video_path.name}")

                if webm_path.exists():
                    pbar.write(f'[跳过] {video_path.name}')
                    pbar.update(1)
                    continue

                try:
                    subprocess.run(
                        get_qsp4_compatible_webm_cmd(video_path, webm_path),
                        check=True,
                        capture_output=True,
                        timeout=300
                    )
                    success_count += 1
                    # 验证文件
                    valid, info = check_webm_file(webm_path)
                    status = GREEN + f'[成功] {video_path.name}' + RESET
                    if valid:
                        status += f" ({info})"
                    else:
                        status += RED + f" (警告: {info})" + RESET
                    pbar.write(status)
                except Exception as e:
                    fail_count += 1
                    pbar.write(RED + f'[失败] {video_path.name}' + RESET)
                    pbar.write(RED + f'     错误: {str(e)[:100]}' + RESET)

                pbar.update(1)

        elif choice == "2":
            # 最小模式
            for idx, video_path in enumerate(video_list):
                webm_path = OUTPUT_DIR / video_path.with_suffix('.webm').name
                pbar.set_description(f"处理: {video_path.name}")

                if webm_path.exists():
                    pbar.write(f'[跳过] {video_path.name}')
                    pbar.update(1)
                    continue

                try:
                    subprocess.run(
                        get_qsp4_minimal_webm_cmd(video_path, webm_path),
                        check=True,
                        capture_output=True,
                        timeout=300
                    )
                    success_count += 1
                    valid, info = check_webm_file(webm_path)
                    status = GREEN + f'[成功] {video_path.name}' + RESET
                    if valid:
                        status += f" ({info})"
                    pbar.write(status)
                except Exception as e:
                    fail_count += 1
                    pbar.write(RED + f'[失败] {video_path.name}' + RESET)
                    pbar.write(RED + f'     错误: {str(e)[:100]}' + RESET)

                pbar.update(1)

        else:
            # 智能模式
            results = pool.imap_unordered(transcode_comprehensive,
                                          [(i, total, f) for i, f in enumerate(video_list)])

            for idx, status, name, msg in results:
                pbar.update(1)
                if status == "success":
                    success_count += 1
                    pbar.write(GREEN + f'[成功] {name} ({msg})' + RESET)
                elif status == "skip":
                    pbar.write(f'[跳过] {name}')
                else:
                    fail_count += 1
                    pbar.write(RED + f'[失败] {name}' + RESET)
                    if msg:
                        pbar.write(RED + f'     错误: {msg}' + RESET)

    elapsed = datetime.timedelta(seconds=int(time.time() - start_t))
    print(f'\n转码完成!')
    print(f'成功: {success_count}, 失败: {fail_count}, 总耗时: {elapsed}')

    # 最终建议
    if success_count > 0:
        print(f"\n下一步:")
        print(f"1. 在QSP4中测试生成的WebM文件")
        print(f"2. 如果仍有问题，尝试不同的编码选项")
        print(f"3. 检查QSP4游戏代码确保正确引用WebM文件")


if __name__ == '__main__':
    main()