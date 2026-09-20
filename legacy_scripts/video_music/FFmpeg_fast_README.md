# 视频压缩工具 - 优化版

## 简介

FFmpeg_fast.py 是一个优化版的视频压缩工具，专为快速处理大文件(3GB以上)而设计。相比原始版本，它提供了多种速度模式选择、硬件加速检测和智能大文件处理功能，可以显著提高压缩速度。

## 主要功能

### 1. 速度模式选择
- **平衡模式(balanced)**: 默认模式，在速度和质量之间取得平衡
- **快速模式(fast)**: 优先考虑速度，质量略有降低
- **超快模式(ultrafast)**: 最大编码速度，适合快速处理大文件

### 2. 硬件加速检测与利用
- 自动检测NVIDIA GPU硬件加速
- 支持HEVC_NVENC和H264_NVENC硬件编码器
- 如果没有检测到硬件加速，自动回退到软件编码

### 3. 大文件智能处理
- 自动检测大文件(>3GB)
- 对大文件自动使用更快的压缩模式
- 显示文件大小和压缩率信息

### 4. 性能监控
- 详细的执行时间统计
- 计算并显示平均每GB处理时间
- 与原始slow模式比较，显示提速百分比

## 使用方法

### 批量压缩文件夹中的视频
```python
from video_music.FFmpeg_fast import compress_all_mp4

# 平衡模式（默认）
compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'balanced')

# 快速模式
compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'fast')

# 超快模式
compress_all_mp4(r'H:/NudeFileZilla/ff/tvshow', 'ultrafast')
```

### 压缩单个视频文件
```python
from video_music.FFmpeg_fast import compress_video

# 压缩单个文件，使用快速模式
compress_video(r'H:/NudeFileZilla/ff/tvshow/video.mp4', r'H:/NudeFileZilla/ff/tvshow/video_reb', 'fast')
```

### 直接运行脚本
```bash
python d:\Code\pythonProject\video_music\FFmpeg_fast.py
```

## 预期提速效果

根据优化内容，预期可以获得以下提速效果：
- **平衡模式**: 比原始slow模式快约2-3倍
- **快速模式**: 比原始slow模式快约3-5倍
- **超快模式**: 比原始slow模式快约5-8倍
- **硬件加速**: 如果有NVIDIA GPU，可额外提速2-4倍

## 注意事项

1. 确保已安装FFmpeg并添加到系统PATH
2. 确保已安装Python依赖库：prettytable
3. 如果使用硬件加速，确保已安装NVIDIA显卡驱动
4. 压缩后的文件会添加"_reb"后缀，不会覆盖原始文件

## 与原版对比

| 特性 | 原版(FFmpeg.py) | 优化版(FFmpeg_fast.py) |
|------|----------------|----------------------|
| 编码预设 | slow | medium/fast/ultrafast |
| 硬件加速检测 | 无 | 自动检测 |
| 速度模式选择 | 无 | 三种模式可选 |
| 大文件处理 | 无 | 智能优化 |
| 性能统计 | 基础 | 详细 |
| 压缩速度 | 基准 | 2-8倍提升 |

通过使用优化版工具，3GB以上大文件的压缩时间可以从原来的半小时以上缩短到几分钟到十几分钟不等，具体取决于文件大小、硬件配置和选择的压缩模式。