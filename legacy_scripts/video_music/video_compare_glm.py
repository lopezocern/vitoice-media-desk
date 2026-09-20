#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频对比与压缩工具 - 保留中文，修复对齐
"""

import subprocess
import json
import os
import re
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from prettytable import PrettyTable


# 中文字符宽度计算
def get_display_width(text: str) -> int:
    """计算字符串显示宽度（中文算2，英文算1）"""
    width = 0
    for char in str(text):
        if ord(char) > 127:  # 中文字符
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text: str, target_width: int, align: str = 'left') -> str:
    """填充字符串到指定显示宽度"""
    current_width = get_display_width(text)
    padding = target_width - current_width

    if padding <= 0:
        # 超长则截断
        if get_display_width(text) > target_width:
            result = ''
            w = 0
            for char in text:
                cw = 2 if ord(char) > 127 else 1
                if w + cw > target_width - 1:
                    break
                result += char
                w += cw
            return result + ' '  # 补一个空格
        return text

    spaces = ' ' * padding
    if align == 'left':
        return text + spaces
    elif align == 'right':
        return spaces + text
    else:  # center
        left = padding // 2
        right = padding - left
        return ' ' * left + text + ' ' * right


@dataclass
class VideoInfo:
    """视频信息数据类"""
    file_path: str
    file_name: str
    file_size: int
    duration: float
    video_codec: str
    width: int
    height: int
    fps: float
    video_bitrate: int
    pixel_format: str
    profile: str
    audio_codec: str
    sample_rate: int
    channels: int
    audio_bitrate: int
    bpp: float = 0.0
    estimated_crf: float = 0.0
    efficiency_score: float = 0.0


class VideoAnalyzer:
    """视频分析器"""

    @staticmethod
    def run_ffprobe(file_path: str, args: List[str]) -> Optional[dict]:
        try:
            cmd = ['ffprobe', '-v', 'error'] + args + ['-of', 'json', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(f"FFprobe错误: {result.stderr}")
                return None
            return json.loads(result.stdout)
        except Exception as e:
            print(f"FFprobe执行失败: {e}")
            return None

    @staticmethod
    def parse_fps(fps_str: str) -> float:
        try:
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                return num / den if den != 0 else 0
            return float(fps_str)
        except:
            return 0

    @classmethod
    def analyze(cls, file_path: str) -> Optional[VideoInfo]:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None

        streams_data = cls.run_ffprobe(file_path, ['-show_streams'])
        if not streams_data:
            return None

        format_data = cls.run_ffprobe(file_path, ['-show_format'])
        if not format_data:
            return None

        streams = streams_data.get('streams', [])
        fmt = format_data.get('format', {})

        video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
        audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})

        video_bitrate = video_stream.get('bit_rate')
        if not video_bitrate:
            total_br = fmt.get('bit_rate')
            audio_br = audio_stream.get('bit_rate')
            if total_br and audio_br:
                video_bitrate = int(total_br) - int(audio_br)
            elif total_br:
                video_bitrate = int(int(total_br) * 0.9)
            else:
                video_bitrate = 0

        fps = cls.parse_fps(video_stream.get('r_frame_rate', '0/1'))

        info = VideoInfo(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size=int(fmt.get('size', 0)),
            duration=float(fmt.get('duration', 0)),
            video_codec=video_stream.get('codec_name', 'unknown'),
            width=video_stream.get('width', 0),
            height=video_stream.get('height', 0),
            fps=fps,
            video_bitrate=int(video_bitrate) if video_bitrate else 0,
            pixel_format=video_stream.get('pix_fmt', 'unknown'),
            profile=video_stream.get('profile', 'unknown'),
            audio_codec=audio_stream.get('codec_name', 'unknown'),
            sample_rate=audio_stream.get('sample_rate', 0),
            channels=audio_stream.get('channels', 0),
            audio_bitrate=int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else 0
        )

        info.bpp = cls.calculate_bpp(info)
        info.estimated_crf = cls.estimate_crf(info)
        info.efficiency_score = cls.calculate_efficiency(info)

        return info

    @staticmethod
    def calculate_bpp(info: VideoInfo) -> float:
        if info.width and info.height and info.fps and info.video_bitrate:
            return round(info.video_bitrate / (info.width * info.height * info.fps), 4)
        return 0.0

    @staticmethod
    def estimate_crf(info: VideoInfo) -> float:
        bpp = info.bpp
        if 'hevc' in info.video_codec or '265' in info.video_codec:
            crf = 17 + (bpp * 100)
        else:
            crf = 15 + (bpp * 80)
        return round(max(0, min(51, crf)), 1)

    @staticmethod
    def calculate_efficiency(info: VideoInfo) -> float:
        bpp = info.bpp
        resolution = info.width * info.height

        if resolution >= 3840 * 2160:
            target_bpp = 0.15
        elif resolution >= 1920 * 1080:
            target_bpp = 0.12
        elif resolution >= 1280 * 720:
            target_bpp = 0.10
        else:
            target_bpp = 0.08

        efficiency = 100 - abs(bpp / target_bpp - 1) * 50
        return round(max(0, min(100, efficiency)), 1)


class VideoComparator:
    """视频对比器 - 保留中文，强制对齐"""

    # 列宽配置
    COL_WIDTHS = {
        '参数': 22,  # 中文占2字符宽度
        '视频A': 16,
        '视频B': 16,
        '对比': 10,
        '评价': 12
    }

    @staticmethod
    def format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.2f} MB"
        else:
            return f"{size / (1024 ** 3):.2f} GB"

    @staticmethod
    def format_bitrate(bitrate: int) -> str:
        if bitrate < 1000:
            return f"{bitrate} bit/s"
        elif bitrate < 1_000_000:
            return f"{bitrate / 1000:.2f} Kbps"
        else:
            return f"{bitrate / 1_000_000:.2f} Mbps"

    @staticmethod
    def format_duration(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @classmethod
    def compare(cls, info1: VideoInfo, info2: VideoInfo) -> str:
        """返回字符串表格，确保中文对齐"""
        w = cls.COL_WIDTHS

        # 构建表头
        lines = []
        lines.append("=" * (w['参数'] + w['视频A'] + w['视频B'] + w['对比'] + w['评价'] + 8))
        header = f"| {pad_to_width('参数', w['参数'])} | {pad_to_width('视频 A', w['视频A'], 'center')} | {pad_to_width('视频 B', w['视频B'], 'center')} | {pad_to_width('对比', w['对比'], 'center')} | {pad_to_width('评价', w['评价'])} |"
        lines.append(header)
        lines.append("-" * (w['参数'] + w['视频A'] + w['视频B'] + w['对比'] + w['评价'] + 8))

        # 数据行
        rows = [
            ('文件名',
             info1.file_name[:14] + '..' if len(info1.file_name) > 14 else info1.file_name,
             info2.file_name[:14] + '..' if len(info2.file_name) > 14 else info2.file_name,
             '-', '参考'),

            ('文件大小',
             cls.format_size(info1.file_size),
             cls.format_size(info2.file_size),
             f"{info1.file_size / info2.file_size:.1f}x" if info2.file_size else 'N/A',
             cls._eval_ratio(info1.file_size / info2.file_size if info2.file_size else 0)),

            ('视频编码', info1.video_codec, info2.video_codec,
             '相同' if info1.video_codec == info2.video_codec else '不同',
             '参考'),

            ('分辨率',
             f"{info1.width}x{info1.height}",
             f"{info2.width}x{info2.height}",
             '相同' if (info1.width, info1.height) == (info2.width, info2.height) else '不同',
             '✓ 正常' if (info1.width, info1.height) == (info2.width, info2.height) else '⚠ 变化'),

            ('帧率(FPS)',
             f"{info1.fps:.2f}", f"{info2.fps:.2f}",
             '相同' if abs(info1.fps - info2.fps) < 0.1 else '不同',
             '✓ 正常' if abs(info1.fps - info2.fps) < 0.1 else '⚠ 变化'),

            ('视频码率',
             cls.format_bitrate(info1.video_bitrate),
             cls.format_bitrate(info2.video_bitrate),
             f"{info1.video_bitrate / info2.video_bitrate:.1f}x" if info2.video_bitrate else 'N/A',
             cls._eval_br_ratio(info1.video_bitrate / info2.video_bitrate if info2.video_bitrate else 0)),

            ('每像素比特(BPP)',
             f"{info1.bpp:.4f}", f"{info2.bpp:.4f}",
             f"{info1.bpp / info2.bpp:.1f}x" if info2.bpp else 'N/A',
             cls._eval_bpp(info2.bpp)),

            ('等效CRF值',
             f"{info1.estimated_crf}", f"{info2.estimated_crf}",
             f"{info2.estimated_crf - info1.estimated_crf:+.1f}",
             cls._eval_crf_diff(info2.estimated_crf - info1.estimated_crf)),

            ('编码效率分',
             f"{info1.efficiency_score}", f"{info2.efficiency_score}",
             f"{info2.efficiency_score - info1.efficiency_score:+.1f}",
             cls._eval_eff(info2.efficiency_score)),

            ('像素格式',
             info1.pixel_format, info2.pixel_format,
             '相同' if info1.pixel_format == info2.pixel_format else '不同',
             '参考'),

            ('音频编码',
             info1.audio_codec, info2.audio_codec,
             '相同' if info1.audio_codec == info2.audio_codec else '不同',
             '参考'),

            ('音频采样率',
             f"{info1.sample_rate}Hz", f"{info2.sample_rate}Hz",
             '相同' if info1.sample_rate == info2.sample_rate else '不同',
             '参考'),

            ('音频声道',
             f"{info1.channels}", f"{info2.channels}",
             '相同' if info1.channels == info2.channels else '不同',
             '参考'),

            ('时长',
             cls.format_duration(info1.duration),
             cls.format_duration(info2.duration),
             '相同' if abs(info1.duration - info2.duration) < 1 else '不同',
             '✓ 正常' if abs(info1.duration - info2.duration) < 1 else '⚠ 变化'),
        ]

        for param, val1, val2, change, eval_str in rows:
            line = f"| {pad_to_width(param, w['参数'])} | {pad_to_width(str(val1), w['视频A'], 'right')} | {pad_to_width(str(val2), w['视频B'], 'right')} | {pad_to_width(str(change), w['对比'], 'center')} | {pad_to_width(eval_str, w['评价'])} |"
            lines.append(line)

        lines.append("=" * (w['参数'] + w['视频A'] + w['视频B'] + w['对比'] + w['评价'] + 8))

        return '\n'.join(lines)

    @staticmethod
    def _eval_ratio(ratio: float) -> str:
        if ratio == 0:
            return 'N/A'
        elif ratio > 5:
            return '⚠ 激进'
        elif ratio > 2:
            return '✓ 优秀'
        elif ratio > 1.5:
            return '○ 一般'
        else:
            return '✗ 不足'

    @staticmethod
    def _eval_br_ratio(ratio: float) -> str:
        if ratio == 0:
            return 'N/A'
        elif ratio > 5:
            return '⚠ 骤降'
        elif ratio > 2:
            return '✓ 理想'
        elif ratio > 1.2:
            return '○ 保守'
        else:
            return '✗ 未压'

    @staticmethod
    def _eval_bpp(bpp: float) -> str:
        if bpp == 0:
            return 'N/A'
        elif bpp < 0.05:
            return '⚠ 过低'
        elif bpp <= 0.15:
            return '✓ 黄金'
        elif bpp <= 0.3:
            return '○ 可优'
        else:
            return '✗ 浪费'

    @staticmethod
    def _eval_crf_diff(diff: float) -> str:
        if abs(diff) < 2:
            return '✓ 相当'
        elif diff < 5:
            return '○ 轻微'
        else:
            return '⚠ 下降'

    @staticmethod
    def _eval_eff(score: float) -> str:
        if score >= 80:
            return '✓ 高效'
        elif score >= 60:
            return '○ 中等'
        else:
            return '⚠ 低效'


class FFmpegCommandBuilder:
    """FFmpeg命令生成器"""

    NVENC_PRESETS = {
        'p1': {'speed': 10, 'quality': 4, 'desc': '最快'},
        'p2': {'speed': 8, 'quality': 5, 'desc': '较快'},
        'p3': {'speed': 7, 'quality': 6, 'desc': '快速'},
        'p4': {'speed': 6, 'quality': 7, 'desc': '平衡'},
        'p5': {'speed': 5, 'quality': 8, 'desc': '慢速'},
        'p6': {'speed': 3, 'quality': 9, 'desc': '较慢'},
        'p7': {'speed': 1, 'quality': 10, 'desc': '最佳'}
    }

    def __init__(self, source_info: VideoInfo):
        self.source = source_info
        self.target_quality = 'balanced'

    def set_target(self, target: str):
        self.target_quality = target
        return self

    def generate(self, output_path: Optional[str] = None) -> Dict:
        if not output_path:
            base, ext = os.path.splitext(self.source.file_path)
            output_path = f"{base}_compressed.mp4"

        params = self._calculate_params()
        cmd = self._build_command(output_path, params)

        return {
            'command': cmd,
            'output_path': output_path,
            'params': params,
            'estimated_size': self._estimate_size(params),
            'recommendations': self._get_recommendations(params)
        }

    def _calculate_params(self) -> Dict:
        resolution = self.source.width * self.source.height
        current_bpp = self.source.bpp

        if self.target_quality == 'quality':
            target_bpp = 0.12 if resolution >= 1920 * 1080 else 0.08
            cq = 20
        elif self.target_quality == 'size':
            target_bpp = 0.06 if resolution >= 1920 * 1080 else 0.04
            cq = 28
        else:
            target_bpp = 0.09 if resolution >= 1920 * 1080 else 0.06
            cq = 24

        target_bitrate = int(target_bpp * self.source.width * self.source.height * self.source.fps)

        if self.target_quality == 'quality':
            preset = 'p7'
        elif self.target_quality == 'size':
            preset = 'p4'
        else:
            preset = 'p5'

        if resolution >= 1920 * 1080:
            profile = 'main10'
            pix_fmt = 'p010le'
        else:
            profile = 'main'
            pix_fmt = 'yuv420p'

        if self.source.audio_codec == 'aac' and self.source.audio_bitrate <= 128000:
            audio_mode = 'copy'
        else:
            audio_mode = 'aac'

        return {
            'encoder': 'hevc_nvenc',
            'preset': preset,
            'tune': 'hq',
            'profile': profile,
            'pix_fmt': pix_fmt,
            'rc': 'vbr',
            'cq': cq,
            'qmin': max(16, cq - 4),
            'qmax': min(32, cq + 4),
            'target_bitrate': target_bitrate,
            'gop': int(self.source.fps * 4),
            'bf': 4,
            'b_ref_mode': 'middle',
            'audio_mode': audio_mode,
            'audio_bitrate': 128000 if audio_mode != 'copy' else None
        }

    def _build_command(self, output: str, p: Dict) -> str:
        cmd_parts = ['ffmpeg', '-i', f'"{self.source.file_path}"']

        cmd_parts.extend([
            '-c:v', 'hevc_nvenc',
            '-preset', p['preset'],
            '-tune', p['tune'],
            '-profile:v', p['profile'],
            '-pix_fmt', p['pix_fmt'],
            '-rc', p['rc'],
            '-cq', str(p['cq']),
            '-qmin', str(p['qmin']),
            '-qmax', str(p['qmax']),
            '-g', str(p['gop']),
            '-bf', str(p['bf']),
            '-b_ref_mode', p['b_ref_mode']
        ])

        if p['audio_mode'] == 'copy':
            cmd_parts.extend(['-c:a', 'copy'])
        else:
            cmd_parts.extend([
                '-c:a', 'aac',
                '-b:a', f"{p['audio_bitrate'] // 1000}k"
            ])

        cmd_parts.extend(['-movflags', '+faststart'])
        cmd_parts.append(f'"{output}"')

        return ' '.join(cmd_parts)

    def _estimate_size(self, p: Dict) -> str:
        video_bits = p['target_bitrate'] * self.source.duration
        audio_bits = (p['audio_bitrate'] or self.source.audio_bitrate) * self.source.duration
        total_bytes = (video_bits + audio_bits) / 8
        total_bytes *= 1.1
        return VideoComparator.format_size(int(total_bytes))

    def _get_recommendations(self, p: Dict) -> List[str]:
        recs = []

        if p['cq'] <= 20:
            recs.append("高质量模式：视觉无损，适合存档收藏")
        elif p['cq'] >= 28:
            recs.append("高压缩模式：文件极小，适合网络传输")
        else:
            recs.append("平衡模式：质量与大小兼顾，推荐日常使用")

        preset_info = self.NVENC_PRESETS.get(p['preset'], {})
        recs.append(f"使用 {p['encoder']} 预设 {p['preset']} (质量等级: {preset_info.get('quality', 'N/A')}/10)")

        if p['profile'] == 'main10':
            recs.append("10bit编码：减少色带，提升压缩效率约10%")

        if p['audio_mode'] == 'copy':
            recs.append("音频直接复制：保留原音质，编码速度提升30%")

        est_size = self._estimate_size(p)
        orig_size = VideoComparator.format_size(self.source.file_size)
        reduction = (1 - (int(self._estimate_size_raw(p)) / self.source.file_size)) * 100
        recs.append(f"预估大小: {est_size} (原文件: {orig_size}, 预计减小{reduction:.0f}%)")

        return recs

    def _estimate_size_raw(self, p: Dict) -> int:
        video_bits = p['target_bitrate'] * self.source.duration
        audio_bits = (p['audio_bitrate'] or self.source.audio_bitrate) * self.source.duration
        total_bytes = (video_bits + audio_bits) / 8
        return int(total_bytes * 1.1)

    def print_command_details(self, result: Dict):
        """打印命令详情 - 使用自定义对齐"""
        w = {'参数': 14, '值': 12, '说明': 40}

        print("\n" + "=" * 75)
        print("FFMPEG 压缩命令")
        print("=" * 75)
        print(f"\n{result['command']}\n")

        print("-" * 75)
        print("参数详解")
        print("-" * 75)

        p = result['params']

        # 手动构建表格
        lines = []
        lines.append(
            f"| {pad_to_width('参数', w['参数'])} | {pad_to_width('值', w['值'])} | {pad_to_width('说明', w['说明'])} |")
        lines.append("-" * 75)

        rows = [
            ('-c:v', p['encoder'], 'NVIDIA HEVC硬件编码器'),
            ('-preset', p['preset'], f'编码速度/质量平衡 (p1最快-p7最佳)'),
            ('-tune', p['tune'], '高质量调优模式'),
            ('-profile:v', p['profile'], '编码档次 (main10=10bit色深)'),
            ('-pix_fmt', p['pix_fmt'], '像素格式 (p010le=10bit)'),
            ('-rc', p['rc'], '码率控制 (vbr=可变码率)'),
            ('-cq', str(p['cq']), f'质量因子 (18-28, 越小质量越好)'),
            ('-qmin/qmax', f"{p['qmin']}/{p['qmax']}", '质量波动范围限制'),
            ('-g', str(p['gop']), f'GOP大小 ({p["gop"] / self.source.fps:.1f}秒一个关键帧)'),
            ('-bf', str(p['bf']), 'B帧数量 (双向预测帧，提高压缩率)'),
            ('-b_ref_mode', p['b_ref_mode'], 'B帧参考模式 (middle=中间参考)'),
            ('-c:a', p['audio_mode'], '音频处理 (copy=不重新编码，保留原质)'),
            ('-movflags', '+faststart', 'MP4容器优化 (moov前置，支持网络播放)'),
        ]

        for param, val, desc in rows:
            lines.append(
                f"| {pad_to_width(param, w['参数'])} | {pad_to_width(val, w['值'])} | {pad_to_width(desc, w['说明'])} |")

        lines.append("=" * 75)
        print('\n'.join(lines))

        print("-" * 75)
        print("智能建议")
        print("-" * 75)
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"{i}. {rec}")

        print("=" * 75)


def main(file_path1, file_path2):
    print("视频对比与压缩工具")
    print("=" * 75)

    if len(sys.argv) >= 3:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
    else:
        file1 = file_path1.strip().strip('"')
        file2 = file_path2.strip().strip('"') or None

    print(f"\n[1/3] 正在分析: {os.path.basename(file1)}")
    info1 = VideoAnalyzer.analyze(file1)
    if not info1:
        print("分析失败，请检查文件路径")
        return

    if file2 and os.path.exists(file2):
        print(f"[2/3] 正在分析: {os.path.basename(file2)}")
        info2 = VideoAnalyzer.analyze(file2)

        if info2:
            print("\n[3/3] 生成对比报告...")
            comparison_table = VideoComparator.compare(info1, info2)
            print(comparison_table)

            if input("\n是否为视频A生成压缩命令? (y/n): ").lower() == 'y':
                builder = FFmpegCommandBuilder(info1)
            else:
                return
        else:
            builder = FFmpegCommandBuilder(info1)
    else:
        print("[2/3] 无对比视频，跳过对比")
        print("[3/3] 生成压缩建议...")
        builder = FFmpegCommandBuilder(info1)

    print("\n选择压缩模式:")
    print("1. quality - 质量优先 (CQ20, 适合存档)")
    print("2. balanced - 平衡模式 (CQ24, 推荐)")
    print("3. size - 体积优先 (CQ28, 适合网络)")

    choice = input("请输入选项 (1-3, 默认2): ").strip() or "2"
    mode_map = {"1": "quality", "2": "balanced", "3": "size"}
    mode = mode_map.get(choice, "balanced")

    builder.set_target(mode)

    output = input(f"输出路径 (直接回车使用默认): ").strip().strip('"')
    result = builder.generate(output if output else None)

    builder.print_command_details(result)

    if input("\n是否立即执行压缩? (y/n): ").lower() == 'y':
        print("\n正在执行...")
        try:
            subprocess.run(result['command'], shell=True, check=True)
            print("✓ 压缩完成!")
        except subprocess.CalledProcessError as e:
            print(f"✗ 执行失败: {e}")


if __name__ == "__main__":
    file_path2 = r"H:\NudeFileZilla\J-AV\SONE-187-C 黑岛玲衣.mp4"
    file_path1 = r"H:\NudeFileZilla\J-AV\# 单体\259Luxu\259LUXU-751.ts"
    main(file_path1, file_path2)
